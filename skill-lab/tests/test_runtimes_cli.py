"""SPEC-102 agent-CLI runtimes, exercised through real subprocesses of fake ``claude``/``codex`` programs."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from tests.test_bench_fakes import fake_executable
from lab.runtimes import RuntimeCallError, create_runtime
from lab.runtimes.codex_cli import CodexCliRuntime

SCHEMA = {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}


def claude_result(text, **extra):
    document = {"type": "result", "subtype": "success", "is_error": False, "result": text, "num_turns": 1}
    document["usage"] = {"input_tokens": 40, "output_tokens": 9}
    document.update(extra)
    return json.dumps(document)


class CliCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bin = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def environ(self):
        return {"PATH": self.bin}

    def calls(self, log):
        with open(log, encoding="utf-8") as handle:
            return json.load(handle)


class TestClaudeCli(CliCase):
    def test_unavailable_when_not_on_path(self):
        ok, reason = create_runtime("claude-cli", environ=self.environ()).available()
        self.assertFalse(ok)
        self.assertIn("LIVE_PREREQ_MISSING", reason)

    def test_argv_stdin_and_parse(self):
        log = fake_executable(self.bin, "claude", stdout=claude_result('{"ok": true}'))
        runtime = create_runtime("claude", model="sonnet", environ=self.environ())
        self.assertEqual(runtime.name, "claude-cli")
        self.assertEqual(runtime.available(), (True, "ok"))
        result = runtime.run("SYSTEM PROMPT", "USER PROMPT", SCHEMA, timeout=30)
        call = self.calls(log)
        self.assertEqual(
            call["argv"],
            [
                "-p",
                "--output-format",
                "json",
                "--no-session-persistence",
                "--tools",
                "",
                "--system-prompt",
                "SYSTEM PROMPT",
                "--model",
                "sonnet",
            ],
        )
        self.assertTrue(call["stdin"].startswith("USER PROMPT\n\nReply with exactly one JSON document"))
        self.assertEqual(result.json_or_none, {"ok": True})
        self.assertEqual(result.usage, {"input_tokens": 40, "output_tokens": 9})
        self.assertEqual(result.raw_meta["structured_output"], "prompt")

    def test_reported_error_and_bad_exit(self):
        fake_executable(
            self.bin, "claude", stdout=claude_result("quota", is_error=True, subtype="error_during_execution")
        )
        with self.assertRaises(RuntimeCallError) as caught:
            create_runtime("claude-cli", environ=self.environ()).run("S", "U", None, timeout=30)
        self.assertEqual(caught.exception.code, "RUNTIME_FAILED")
        fake_executable(self.bin, "claude", stdout="", stderr="not logged in", exit_code=1)
        with self.assertRaises(RuntimeCallError) as caught:
            create_runtime("claude-cli", environ=self.environ()).run("S", "U", None, timeout=30)
        self.assertIn("not logged in", caught.exception.message)

    def test_non_json_output_is_a_protocol_error(self):
        fake_executable(self.bin, "claude", stdout="hello")
        with self.assertRaises(RuntimeCallError) as caught:
            create_runtime("claude-cli", environ=self.environ()).run("S", "U", None, timeout=30)
        self.assertEqual(caught.exception.code, "RUNTIME_PROTOCOL")


class TestCodexCli(CliCase):
    def test_argv_stdin_and_current_event_shape(self):
        events = [
            {"type": "thread.started", "thread_id": "t"},
            {"type": "item.completed", "item": {"id": "1", "type": "reasoning", "text": "thinking"}},
            {"type": "item.completed", "item": {"id": "2", "type": "agent_message", "text": '{"ok": false}'}},
            {"type": "turn.completed", "usage": {"input_tokens": 50, "cached_input_tokens": 0, "output_tokens": 4}},
        ]
        log = fake_executable(self.bin, "codex", stdout="\n".join(json.dumps(e) for e in events) + "\n")
        result = create_runtime("codex", model="gpt-5-codex", environ=self.environ()).run(
            "SYS", "USR", SCHEMA, timeout=30
        )
        call = self.calls(log)
        self.assertEqual(
            call["argv"],
            ["exec", "--json", "--sandbox", "read-only", "--skip-git-repo-check", "--model", "gpt-5-codex", "-"],
        )
        self.assertTrue(call["stdin"].startswith("SYS\n\nUSR\n\nReply with exactly one JSON document"))
        self.assertEqual(result.json_or_none, {"ok": False})
        self.assertEqual(result.usage, {"input_tokens": 50, "output_tokens": 4})

    def test_legacy_event_shape(self):
        events = [{"id": "0", "msg": {"type": "agent_message", "message": '{"ok": true}'}}]
        fake_executable(self.bin, "codex", stdout=json.dumps(events[0]) + "\n")
        result = create_runtime("codex-cli", environ=self.environ()).run("S", "U", SCHEMA, timeout=30)
        self.assertEqual(result.json_or_none, {"ok": True})

    def test_failures(self):
        fake_executable(self.bin, "codex", stdout=json.dumps({"type": "turn.failed", "error": {"message": "boom"}}))
        with self.assertRaises(RuntimeCallError) as caught:
            create_runtime("codex-cli", environ=self.environ()).run("S", "U", None, timeout=30)
        self.assertIn("boom", caught.exception.message)
        fake_executable(self.bin, "codex", stdout=json.dumps({"type": "turn.completed", "usage": {}}))
        with self.assertRaises(RuntimeCallError) as caught:
            create_runtime("codex-cli", environ=self.environ()).run("S", "U", None, timeout=30)
        self.assertEqual(caught.exception.code, "RUNTIME_PROTOCOL")

    def test_runs_in_an_empty_temporary_directory(self):
        fake_executable(self.bin, "codex", stdout=json.dumps({"msg": {"type": "agent_message", "message": "x"}}))
        seen = {}

        def runner(argv, stdin_text, timeout, env, cwd):
            seen.update(cwd=cwd, listing=os.listdir(cwd), env=env)
            return 0, json.dumps({"msg": {"type": "agent_message", "message": "hi"}}), ""

        result = CodexCliRuntime(None, environ=self.environ(), runner=runner).run("S", "U", None, timeout=5)
        self.assertEqual(result.text, "hi")
        self.assertEqual(seen["listing"], [])
        self.assertFalse(os.path.exists(seen["cwd"]))


if __name__ == "__main__":
    unittest.main()
