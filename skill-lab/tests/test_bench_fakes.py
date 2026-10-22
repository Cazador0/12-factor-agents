"""Test doubles for the SPEC-102/103/104 tests, plus tests of the doubles themselves.

* ``FakeServer``: a scripted HTTP server on 127.0.0.1 (ephemeral port) in a
  background thread that records every request. It stands in for Ollama and
  for the TypeSafe API; no test talks to a real service.
* ``fake_executable``: a small Python program installed under a given name
  (``claude``, ``codex``) that records its argv and stdin and prints a canned
  reply, so CLI runtimes are exercised through a real subprocess.
* ``ScratchRepo``: a throwaway repository with ``skills/`` and
  ``skill-lab/`` folders, for end-to-end bench and score runs.
"""

from __future__ import annotations

import contextlib
import http.server
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Iterator, List, NamedTuple, Optional, Tuple

from tests import skillkit_support as support

if support.LAB_ROOT not in sys.path:
    sys.path.insert(0, support.LAB_ROOT)

NOW = "2026-10-22T08:00:00Z"


class Recorded(NamedTuple):
    method: str
    path: str
    headers: Dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class Reply(NamedTuple):
    status: int
    body: Any = None
    headers: Optional[Dict[str, str]] = None


Responder = Callable[[Recorded], Reply]


class FakeServer:
    """Scripted HTTP server. ``route(method, path, *replies)`` queues replies; the last one repeats.

    A route may instead be a callable ``(Recorded) -> Reply``.
    """

    def __init__(self) -> None:
        self.requests: List[Recorded] = []
        self._routes: Dict[Tuple[str, str], Any] = {}
        self._lock = threading.Lock()
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - http.server API
                server._handle(self)

            def do_POST(self) -> None:  # noqa: N802 - http.server API
                server._handle(self)

            def log_message(self, *args: Any) -> None:
                return None

        self._httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)

    @property
    def url(self) -> str:
        return "http://127.0.0.1:%d" % self._httpd.server_address[1]

    def route(self, method: str, path: str, *replies: Any) -> "FakeServer":
        if len(replies) == 1 and callable(replies[0]):
            self._routes[(method, path)] = replies[0]
        else:
            self._routes[(method, path)] = list(replies)
        return self

    def requests_to(self, path: str) -> List[Recorded]:
        return [request for request in self.requests if request.path == path]

    def __enter__(self) -> "FakeServer":
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)

    def _handle(self, handler: http.server.BaseHTTPRequestHandler) -> None:
        length = int(handler.headers.get("Content-Length") or 0)
        body = handler.rfile.read(length) if length else b""
        recorded = Recorded(handler.command, handler.path, {k.lower(): v for k, v in handler.headers.items()}, body)
        with self._lock:
            self.requests.append(recorded)
            route = self._routes.get((handler.command, handler.path))
            if route is None:
                reply = Reply(404, {"error": "no route"})
            elif callable(route):
                reply = route(recorded)
            else:
                reply = route.pop(0) if len(route) > 1 else route[0]
        payload = reply.body if isinstance(reply.body, bytes) else json.dumps(reply.body).encode("utf-8")
        handler.send_response(reply.status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(payload)))
        for name, value in (reply.headers or {}).items():
            handler.send_header(name, value)
        handler.end_headers()
        handler.wfile.write(payload)


def ollama_reply(content: str, prompt_tokens: int = 11, output_tokens: int = 7) -> Reply:
    return Reply(
        200,
        {
            "model": "qwen3:14b",
            "message": {"role": "assistant", "content": content},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": prompt_tokens,
            "eval_count": output_tokens,
        },
    )


def ollama_tags(*names: str) -> Reply:
    return Reply(200, {"models": [{"name": name, "model": name} for name in names]})


def jev_models() -> Reply:
    return Reply(
        200,
        {
            "models": [
                {"name": "jev-latest", "description": "General-purpose system one model.", "release_date": "2026-09-15"}
            ]
        },
    )


def jev_answers(answers: Dict[str, Any], request_id: str = "req-1") -> Reply:
    return Reply(
        200,
        {"model": "jev-2026-09-15", "answers": answers, "usage": {"input_tokens": 120, "output_tokens": 12}},
        {"x-typesafe-request-id": request_id},
    )


def fake_executable(directory: str, name: str, *, stdout: str, exit_code: int = 0, stderr: str = "") -> str:
    """Install ``directory/name``: records argv and stdin in ``name.calls.json``, prints ``stdout``."""
    path = os.path.join(directory, name)
    log = os.path.join(directory, name + ".calls.json")
    source = (
        "#!%s\n"
        "import json, sys\n"
        "data = sys.stdin.read()\n"
        "with open(%r, 'w', encoding='utf-8') as handle:\n"
        "    json.dump({'argv': sys.argv[1:], 'stdin': data}, handle)\n"
        "sys.stdout.write(%r)\n"
        "sys.stderr.write(%r)\n"
        "sys.exit(%d)\n" % (sys.executable, log, stdout, stderr, exit_code)
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(source)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return log


ECHO_SCRIPT = '''#!/usr/bin/env python3
"""Echo a fixture as the payload of an envelope (bench test double)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _skillkit import cli, envelope  # noqa: E402
from _skillkit.envelope import ScriptResult  # noqa: E402


def main():
    parser = cli.base_parser("echo a fixture")
    parser.add_argument("--input", required=True)
    parser.add_argument("--kind", default="transition-decision")
    parser.add_argument("--exit", type=int, default=0)
    parser.add_argument("--touch", help="write a marker file here")
    args = parser.parse_args()
    payload = cli.read_json(args.input)
    if args.touch:
        with open(args.touch, "w", encoding="utf-8") as handle:
            handle.write("touched")
    errors = [] if args.exit == 0 else [{"code": "DENIED", "message": "denied by fixture"}]
    return ScriptResult(args.exit, payload, errors, [], kind=args.kind)


if __name__ == "__main__":
    sys.exit(
        envelope.run_script(main, skill="demo-skill", script="echo.py", version="0.1.0", kind="transition-decision")
    )
'''


class ScratchRepo:
    """A temporary repository: ``skills/<name>/`` folders plus an empty ``skill-lab/``."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="skill-lab-test-")
        self.root = os.path.realpath(self._tmp.name)
        os.makedirs(os.path.join(self.root, "skills"))
        os.makedirs(os.path.join(self.root, "skill-lab", "benchmarks", "criteria"))

    def close(self) -> None:
        self._tmp.cleanup()

    def path(self, *parts: str) -> str:
        return os.path.join(self.root, *parts)

    def write(self, relative: str, content: Any) -> str:
        path = self.path(*relative.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = content if isinstance(content, str) else json.dumps(content, indent=2, sort_keys=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def add_skill(
        self, name: str, description: str, *, body: str = "# Title\n\nDo the thing.\n", extra: str = ""
    ) -> str:
        self.write(
            "skills/%s/SKILL.md" % name,
            '---\nname: %s\ndescription: "%s"\n%smetadata:\n  version: "0.1.0"\n  family: meta\n'
            "  spec: SPEC-012\n  author: tests\n---\n%s" % (name, description, extra, body),
        )
        return self.path("skills", name)

    def add_echo_script(self, skill: str) -> None:
        shutil.copytree(support.SKILLKIT_DIR, self.path("skills", skill, "scripts", "_skillkit"))
        self.write("skills/%s/scripts/echo.py" % skill, ECHO_SCRIPT)

    def add_case(self, skill: str, case: Dict[str, Any]) -> str:
        document = {"schema": "urn:skill-lab:schema:benchmark-case:v1", "skill": skill}
        document.update(case)
        return self.write("skills/%s/evals/cases/%s.json" % (skill, case["id"]), document)


@contextlib.contextmanager
def captured_stdout() -> Iterator[io.BytesIO]:
    """Capture what an envelope writer puts on stdout (it writes UTF-8 bytes to ``sys.stdout.buffer``)."""
    raw = io.BytesIO()
    wrapper = io.TextIOWrapper(raw, encoding="utf-8", write_through=True)
    try:
        with contextlib.redirect_stdout(wrapper):
            yield raw
    finally:
        wrapper.flush()
        wrapper.detach()  # keep ``raw`` open after the wrapper is garbage-collected


class TestFakeServer(unittest.TestCase):
    def test_records_requests_and_repeats_last_reply(self):
        with FakeServer() as server:
            server.route("POST", "/x", Reply(500, {"n": 1}), Reply(200, {"n": 2}))
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            statuses = []
            for _ in range(3):
                request = urllib.request.Request(server.url + "/x", data=b'{"a": 1}', method="POST")
                try:
                    with opener.open(request, timeout=5) as response:
                        statuses.append(response.status)
                except urllib.error.HTTPError as exc:
                    statuses.append(exc.code)
        self.assertEqual(statuses, [500, 200, 200])
        self.assertEqual(server.requests[0].json(), {"a": 1})

    def test_fake_executable_records_argv_and_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            log = fake_executable(directory, "tool", stdout="out", exit_code=3)
            completed = subprocess.run(
                [os.path.join(directory, "tool"), "a", "b"], input="in", capture_output=True, text=True
            )
            with open(log, encoding="utf-8") as handle:
                calls = json.load(handle)
        self.assertEqual((completed.returncode, completed.stdout), (3, "out"))
        self.assertEqual(calls, {"argv": ["a", "b"], "stdin": "in"})


if __name__ == "__main__":
    unittest.main()
