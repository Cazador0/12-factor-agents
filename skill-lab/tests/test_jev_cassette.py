"""SPEC-102/103 cassettes: keyed by request content (not headers), replay never invents, no secrets on disk."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from tests import skillkit_support as support
from tests.test_bench_fakes import FakeServer, jev_answers
from lab import jev
from lab.cassette import HTTP_KIND, Cassette, CassetteError, CassetteMiss, CassetteTransport, http_key_request
from lab.runtimes.transport import HttpRequest, urllib_transport

CANARY = "ts-canary-secret-9d8c7b6a5f"
NOUL = {"type": "noul", "instructions": "Is it grounded?", "criteria": {"true": "yes", "false": "no"}}


def read_all(root):
    texts = []
    for directory, _, files in os.walk(root):
        for name in files:
            with open(os.path.join(directory, name), encoding="utf-8") as handle:
                texts.append(handle.read())
    return texts


class TestCassette(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = os.path.join(self._tmp.name, "cassette")

    def test_key_ignores_headers_and_host(self):
        body = b'{"a": 1}'
        one = HttpRequest("POST", "http://127.0.0.1:1/v1/systemone", {"Authorization": "Bearer one"}, body)
        two = HttpRequest(
            "POST", "https://api.typesafe.ai/v1/systemone", {"Authorization": "Bearer two", "X": "y"}, body
        )
        cassette = Cassette(self.root)
        self.assertEqual(cassette.key(HTTP_KIND, http_key_request(one)), cassette.key(HTTP_KIND, http_key_request(two)))
        three = HttpRequest("POST", "https://api.typesafe.ai/v1/systemone", {}, b'{"a": 2}')
        self.assertNotEqual(
            cassette.key(HTTP_KIND, http_key_request(one)), cassette.key(HTTP_KIND, http_key_request(three))
        )

    def test_record_then_replay_through_the_jev_client(self):
        with support.env(TYPESAFE_API_KEY=CANARY), FakeServer() as server:
            server.route("POST", "/v1/systemone", jev_answers({"q": {"type": "noul", "noul": 0.91}}, "req-rec"))
            recorder = CassetteTransport(
                Cassette(self.root), mode="record", inner=urllib_transport, recorded_at="2026-10-22T08:00:00Z"
            )
            live = jev.JevClient.from_env(transport=recorder, base_url=server.url, log=None).ask(
                {"output": "x"}, {"q": NOUL}
            )
            files = read_all(self.root)
        self.assertEqual(len(files), 1)
        self.assertNotIn(CANARY, files[0])
        self.assertNotIn("authorization", files[0].lower())
        entry = json.loads(files[0])
        self.assertEqual(entry["request"]["path"], "/v1/systemone")
        self.assertEqual(entry["response"]["headers"]["x-typesafe-request-id"], "req-rec")

        # The server is gone and no key is set: replay alone answers, with the recorded request id.
        replayer = CassetteTransport(Cassette(self.root), mode="replay")
        replayed = jev.JevClient(None, transport=replayer, log=None).ask({"output": "x"}, {"q": NOUL})
        self.assertEqual(replayed.answers, live.answers)
        self.assertEqual(replayed.request_id, "req-rec")

    def test_replay_miss_is_never_answered(self):
        replayer = CassetteTransport(Cassette(self.root), mode="replay")
        with self.assertRaises(CassetteMiss):
            jev.JevClient(None, transport=replayer, log=None).ask("never recorded", {"q": NOUL})

    def test_secret_values_and_credential_keys_are_redacted(self):
        cassette = Cassette(self.root)
        with support.env(OLLAMA_API_KEY=CANARY):
            path = cassette.save(
                "runtime", {"user": "uses " + CANARY}, {"text": "ok", "api_key": "abc"}, recorded_at="t"
            )
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn(CANARY, text)
        self.assertNotIn('"abc"', text)

    def test_aliases_hide_local_paths(self):
        cassette = Cassette(self.root, aliases={"/home/alice/repo": "<repo>"})
        path = cassette.save(
            "runtime", {"system": "/home/alice/repo/skills/x/SKILL.md"}, {"text": "t"}, recorded_at="t"
        )
        with open(path, encoding="utf-8") as handle:
            self.assertNotIn("/home/alice", handle.read())
        self.assertEqual(
            cassette.load("runtime", {"system": "/home/alice/repo/skills/x/SKILL.md"})["response"], {"text": "t"}
        )

    def test_corrupt_entry_is_an_error_not_a_miss(self):
        cassette = Cassette(self.root)
        request = {"user": "u"}
        path = cassette.save("runtime", request, {"text": "t"}, recorded_at="t")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('{"cassette_format": 99}')
        with self.assertRaises(CassetteError):
            cassette.load("runtime", request)

    def test_modes_are_checked(self):
        with self.assertRaises(ValueError):
            CassetteTransport(Cassette(self.root), mode="record")
        with self.assertRaises(ValueError):
            CassetteTransport(Cassette(self.root), mode="live")


if __name__ == "__main__":
    unittest.main()
