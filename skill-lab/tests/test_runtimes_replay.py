"""SPEC-102 runtime recording and replay: turns recorded live replay without the runtime; misses never invent."""

from __future__ import annotations

import os
import tempfile
import unittest

from lab.cassette import RUNTIME_KIND, Cassette, CassetteMiss
from lab.runtimes import Runtime, RuntimeResult, create_runtime
from lab.runtimes.replay import RecordingRuntime, ReplayRuntime


class StubRuntime(Runtime):
    name = "ollama-cloud"
    model = "gpt-oss:120b"

    def __init__(self):
        self.calls = 0

    def available(self):
        return True, "ok"

    def run(self, system_prompt, user_prompt, output_schema, *, timeout):
        self.calls += 1
        return RuntimeResult('{"ok": true}', {"ok": True}, {"input_tokens": 3, "output_tokens": 2}, {"repairs": 0})


class TestRecordAndReplay(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = os.path.join(self._tmp.name, "repo")
        self.cassette = Cassette(os.path.join(self._tmp.name, "cassette"), aliases={self.repo: "<repo>"})

    def test_recorded_turn_replays_identically(self):
        stub = StubRuntime()
        recorder = RecordingRuntime(stub, self.cassette, recorded_at="2026-10-22T08:00:00Z")
        system = "catalog at %s/skills/x/SKILL.md" % self.repo
        live = recorder.run(system, "user", {"type": "object"}, timeout=5)
        self.assertEqual((recorder.name, recorder.model, stub.calls), ("ollama-cloud", "gpt-oss:120b", 1))
        self.assertEqual(self.cassette.count(RUNTIME_KIND), 1)

        # Another machine: different absolute repository path, same relative layout.
        other_repo = os.path.join(self._tmp.name, "elsewhere")
        replay_cassette = Cassette(self.cassette.root, aliases={other_repo: "<repo>"})
        replay = ReplayRuntime(replay_cassette, model="gpt-oss:120b")
        self.assertEqual(replay.available(), (True, "ok"))
        replayed = replay.run("catalog at %s/skills/x/SKILL.md" % other_repo, "user", {"type": "object"}, timeout=5)
        self.assertEqual(
            (replayed.text, replayed.json_or_none, replayed.usage), (live.text, live.json_or_none, live.usage)
        )
        self.assertTrue(replayed.raw_meta["replayed"])
        self.assertEqual(replayed.raw_meta["recorded_runtime"], "ollama-cloud")
        self.assertEqual(replayed.raw_meta["repairs"], 0)

    def test_unrecorded_turn_is_a_miss(self):
        RecordingRuntime(StubRuntime(), self.cassette, recorded_at="t").run("s", "u", None, timeout=5)
        replay = ReplayRuntime(self.cassette, model="gpt-oss:120b")
        with self.assertRaises(CassetteMiss):
            replay.run("s", "a different prompt", None, timeout=5)
        with self.assertRaises(CassetteMiss):
            ReplayRuntime(self.cassette, model="another-model").run("s", "u", None, timeout=5)

    def test_empty_cassette_is_unavailable(self):
        ok, reason = create_runtime("replay", cassette=self.cassette).available()
        self.assertFalse(ok)
        self.assertIn("LIVE_PREREQ_MISSING", reason)
        with self.assertRaises(ValueError):
            create_runtime("replay")


if __name__ == "__main__":
    unittest.main()
