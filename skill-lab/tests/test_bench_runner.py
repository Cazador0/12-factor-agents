"""SPEC-102 end to end: ``lab.bench`` on a scratch repository with fake Ollama and fake Jev servers."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from tests import skillkit_support as support
from tests.test_bench_fakes import (
    NOW,
    FakeServer,
    ScratchRepo,
    captured_stdout,
    jev_answers,
    jev_models,
    ollama_reply,
    ollama_tags,
)
from _skillkit import EXIT_FAIL, EXIT_OK, EXIT_REFUSED, schemas
from _skillkit.envelope import ScriptError
from lab import bench

KEY = "ts-bench-canary-0a1b2c3d4e"
DECISION = support.load_example("transition-decision")
DESCRIPTION = (
    "Echo a fixture as an envelope payload. Use when testing the bench, checking envelopes, or replaying fixtures."
)
JUDGMENTS = [
    {
        "id": "grounded",
        "type": "noul",
        "instructions": "The output restates the decision in the fixture without inventing facts.",
        "criteria": {"true": "Every field comes from the fixture.", "false": "Some field is invented."},
        "state_from": ["output", "fixtures"],
        "pass_if": {"gte": 0.8},
    },
    {
        "id": "complete",
        "type": "score",
        "instructions": "How complete is the restated decision?",
        "criteria": ["missing fields", "partial", "complete"],
        "state_from": ["fixtures", "output"],
        "pass_if": {"gte": 1.5},
    },
]


def build_repo():
    repo = ScratchRepo()
    repo.add_skill("demo-skill", DESCRIPTION)
    repo.add_skill(
        "lease-skill", "Claim and release work leases. Use when a session must own an issue, renew, or release it."
    )
    repo.add_echo_script("demo-skill")
    repo.write("skills/demo-skill/evals/fixtures/decision.json", DECISION)
    fixture = ["--input", "evals/fixtures/decision.json"]
    repo.add_case(
        "demo-skill",
        {
            "id": "det-pass",
            "tier": "deterministic",
            "description": "Echo succeeds.",
            "tags": ["smoke"],
            "run": {"script": "scripts/echo.py", "args": fixture},
            "expect": {
                "exit_code": 0,
                "schema_valid": True,
                "assertions": [{"path": "/payload/allowed", "op": "eq", "value": DECISION["allowed"]}],
            },
        },
    )
    repo.add_case(
        "demo-skill",
        {
            "id": "det-fail",
            "tier": "deterministic",
            "description": "Expects a refusal that never comes.",
            "run": {"script": "scripts/echo.py", "args": fixture},
            "expect": {"exit_code": 1, "schema_valid": True, "assertions": []},
        },
    )
    repo.add_case(
        "demo-skill",
        {
            "id": "det-stdin-tmp",
            "tier": "deterministic",
            "description": "Reads stdin and writes only to {tmp}.",
            "tags": ["smoke"],
            "run": {
                "script": "scripts/echo.py",
                "args": ["--input", "-", "--touch", "{tmp}/marker"],
                "stdin_file": "evals/fixtures/decision.json",
            },
            "expect": {
                "exit_code": 0,
                "schema_valid": True,
                "assertions": [{"path": "/kind", "op": "eq", "value": "transition-decision"}],
            },
        },
    )
    repo.add_case(
        "demo-skill",
        {
            "id": "agentic-restate",
            "tier": "agentic",
            "description": "Restate the fixture decision.",
            "prompt": "Restate the decision in the fixture as a transition-decision document.",
            "fixtures": ["evals/fixtures/decision.json"],
            "output_schema": "urn:skill-lab:schema:transition-decision:v1",
            "expect": {
                "schema_valid": True,
                "assertions": [{"path": "/allowed", "op": "eq", "value": DECISION["allowed"]}],
            },
            "judgments": JUDGMENTS,
        },
    )
    repo.add_case(
        "demo-skill",
        {
            "id": "route-positive",
            "tier": "trigger",
            "description": "Routes here.",
            "query": "echo this fixture as an envelope",
            "expect_skill": "demo-skill",
        },
    )
    repo.add_case(
        "demo-skill",
        {
            "id": "route-negative",
            "tier": "trigger",
            "description": "Routes nowhere.",
            "query": "what is the weather in Paris",
            "expect_skill": None,
        },
    )
    return repo


class FakeServices:
    """Fake Ollama and Jev whose replies depend on the request, so routing can be right or wrong."""

    def __init__(self, noul=0.93):
        self.noul = noul
        self.ollama = (
            FakeServer().route("GET", "/api/tags", ollama_tags("qwen3:14b")).route("POST", "/api/chat", self.chat)
        )
        self.jev = FakeServer().route("GET", "/v1/models", jev_models()).route("POST", "/v1/systemone", self.systemone)

    def __enter__(self):
        self.ollama.__enter__()
        self.jev.__enter__()
        return self

    def __exit__(self, *exc):
        self.ollama.__exit__(*exc)
        self.jev.__exit__(*exc)

    def environ(self):
        return {"OLLAMA_HOST": self.ollama.url, "TYPESAFE_API_KEY": KEY, "TYPESAFE_BASE_URL": self.jev.url}

    def chat(self, request):
        body = request.json()
        user = body["messages"][-1]["content"]
        if '"skill"' in json.dumps(body.get("format", {})):
            return ollama_reply('{"skill": "%s"}' % ("none" if "weather" in user else "demo-skill"))
        return ollama_reply("```json\n%s\n```" % json.dumps(DECISION))

    def systemone(self, request):
        body = request.json()
        if "routing" in body["questions"]:
            choice = "none" if "weather" in body["state"] else "demo-skill"
            probabilities = (
                {"demo-skill": 0.1, "lease-skill": 0.05, "none": 0.85}
                if choice == "none"
                else {"demo-skill": 0.9, "lease-skill": 0.05, "none": 0.05}
            )
            return jev_answers(
                {"routing": {"type": "choice", "choice": choice, "confidence": 0.9, "probabilities": probabilities}},
                "req-route",
            )
        answers = {}
        for name, question in body["questions"].items():
            if question["type"] == "noul":
                answers[name] = {"type": "noul", "noul": self.noul}
            else:
                answers[name] = {
                    "type": "score",
                    "score": 1.8,
                    "confidence": 0.7,
                    "legend": {"0": "missing fields", "1": "partial", "2": "complete"},
                    "probabilities": {"0": 0.0, "1": 0.2, "2": 0.8},
                }
        return jev_answers(answers, "req-judge")


class BenchCase(unittest.TestCase):
    def setUp(self):
        self.repo = build_repo()
        self.addCleanup(self.repo.close)
        self._out = tempfile.TemporaryDirectory()
        self.addCleanup(self._out.cleanup)
        self.out = self._out.name

    def run_bench(self, *args, environ=None):
        argv = ["--repo", self.repo.root, "--now", NOW, "--out", self.out] + list(args)
        return bench.run(argv, environ=environ or {})

    def by_id(self, result):
        return {item["case_id"]: item for item in result.payload["results"]}


class TestDeterministicTier(BenchCase):
    def test_offline_run_grades_writes_and_validates(self):
        result = self.run_bench()
        cases = self.by_id(result)
        self.assertEqual(
            {k: v["status"] for k, v in cases.items()},
            {"det-pass": "pass", "det-fail": "fail", "det-stdin-tmp": "pass"},
        )
        self.assertEqual(result.exit_code, EXIT_FAIL)
        self.assertEqual(cases["det-pass"]["runtime"], "script")
        self.assertEqual(cases["det-fail"]["exit_code"], 0)
        self.assertIn("exit code 0, expected 1", cases["det-fail"]["notes"])
        self.assertEqual(result.payload["summary"]["deterministic"]["pass_rate"], 2 / 3)
        self.assertEqual(result.payload["jev_mode"], "off")
        self.assertFalse(any(note.startswith("jev:") for note in result.payload["notes"]))
        self.assertTrue(result.payload["notes"][0].startswith("suite_digest=sha256:"))
        self.assertFalse(os.path.exists(self.repo.path("skills", "demo-skill", "marker")))
        with open(os.path.join(self.out, "benchmark-run.json"), encoding="utf-8") as handle:
            written = json.load(handle)
        self.assertEqual(schemas.validate_payload("benchmark-run", written, [support.SCHEMA_DIR]), [])
        with open(os.path.join(self.out, "results", "demo-skill", "det-pass.json"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), cases["det-pass"])

    def test_run_id_is_deterministic_with_now(self):
        first, second = self.run_bench(), self.run_bench()
        self.assertEqual(first.payload["run_id"], second.payload["run_id"])
        self.assertRegex(first.payload["run_id"], r"^run-20261022T080000Z-[0-9a-f]{8}$")
        self.assertNotEqual(first.payload["run_id"], self.run_bench("--tag", "smoke").payload["run_id"])

    def test_tag_filter_and_filters_record(self):
        result = self.run_bench("--tag", "smoke", "--skill", "demo-skill")
        self.assertEqual(sorted(self.by_id(result)), ["det-pass", "det-stdin-tmp"])
        self.assertEqual(result.exit_code, EXIT_OK)
        self.assertEqual(result.payload["filters"], {"skill": "demo-skill", "tier": "deterministic"})

    def test_main_prints_one_valid_envelope(self):
        with captured_stdout() as raw:
            code = bench.main(["--repo", self.repo.root, "--now", NOW, "--out", self.out, "--tag", "smoke"])
        document = json.loads(raw.getvalue().decode("utf-8"))
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(schemas.validate_envelope(document, exit_code=code, search_dirs=[support.SCHEMA_DIR]), [])
        self.assertEqual(document["producer"]["skill"], "skill-lab")

    def test_invalid_case_file_is_reported(self):
        self.repo.write(
            "skills/demo-skill/evals/cases/wrong-name.json",
            {
                "schema": "urn:skill-lab:schema:benchmark-case:v1",
                "id": "other",
                "skill": "demo-skill",
                "tier": "trigger",
                "description": "x",
                "query": "q",
                "expect_skill": None,
            },
        )
        self.repo.write("skills/demo-skill/evals/cases/not-json.json", "{oops")
        result = self.run_bench("--tag", "smoke")
        self.assertEqual(result.exit_code, EXIT_FAIL)
        self.assertEqual([error["code"] for error in result.errors], ["CASE_INVALID", "CASE_INVALID"])
        self.assertTrue(all(error["path"].startswith("skills/demo-skill/evals/cases/") for error in result.errors))

    def test_output_inside_skills_is_refused(self):
        with captured_stdout():
            code = bench.main(
                ["--repo", self.repo.root, "--now", NOW, "--out", self.repo.path("skills", "demo-skill", "out")]
            )
        self.assertEqual(code, EXIT_REFUSED)

    def test_unknown_skill_and_tier(self):
        with self.assertRaises(ScriptError) as caught:
            self.run_bench("--skill", "nope")
        self.assertEqual(caught.exception.code, "SKILL_NOT_FOUND")
        self.assertEqual(bench.parse_tiers(["agentic,trigger"]), ["agentic", "trigger"])
        self.assertEqual(bench.parse_tiers(["all"]), ["deterministic", "agentic", "trigger"])
        self.assertEqual(bench.parse_tiers(None), ["deterministic"])
        with self.assertRaises(ScriptError):
            bench.parse_tiers(["fast"])


class TestModelTiers(BenchCase):
    def test_agentic_and_trigger_with_live_fakes(self):
        with FakeServices() as services:
            result = self.run_bench(
                "--tier",
                "agentic,trigger",
                "--runtime",
                "ollama-local",
                "--model",
                "qwen3:14b",
                environ=services.environ(),
            )
        cases = self.by_id(result)
        self.assertEqual(result.exit_code, EXIT_OK, result.payload)
        agentic = cases["agentic-restate"]
        self.assertEqual(
            (agentic["status"], agentic["runtime"], agentic["jev_mode"]), ("pass", "ollama-local-zed-emulation", "live")
        )
        self.assertEqual([j["id"] for j in agentic["judgments"]], ["grounded", "complete"])
        self.assertEqual({j["request_id"] for j in agentic["judgments"]}, {"req-judge"})
        self.assertIn("json_extraction=fenced", " ".join(agentic["notes"]))

        judge_requests = [
            r.json() for r in services.jev.requests_to("/v1/systemone") if "routing" not in r.json()["questions"]
        ]
        self.assertEqual(len(judge_requests), 1, "all judgments of a case go in one request")
        self.assertEqual(set(judge_requests[0]["questions"]), {"grounded", "complete"})
        self.assertEqual(list(judge_requests[0]["state"]), ["fixtures", "output"])
        self.assertEqual(judge_requests[0]["state"]["fixtures"]["evals/fixtures/decision.json"], DECISION)
        self.assertEqual(judge_requests[0]["questions"]["grounded"]["instructions"], JUDGMENTS[0]["instructions"])

        chat = services.ollama.requests_to("/api/chat")[0].json()
        self.assertIn("<available_skills>", chat["messages"][0]["content"])
        self.assertIn("<name>lease-skill</name>", chat["messages"][0]["content"])
        self.assertTrue(chat["messages"][1]["content"].startswith('<skill_content name="demo-skill">'))
        self.assertIn('<file path="evals/fixtures/decision.json">', chat["messages"][1]["content"])
        self.assertEqual(chat["options"]["num_ctx"], 32768)

        for case_id in ("route-positive", "route-negative"):
            routed = cases[case_id]
            self.assertEqual((routed["status"], routed["runtime"], routed["jev_mode"]), ("pass", "jev-choice", "live"))
            self.assertIn("routing_method=jev-choice", routed["notes"])
        self.assertEqual(cases["route-positive"]["routed_skill"], "demo-skill")
        self.assertIsNone(cases["route-negative"]["routed_skill"])
        self.assertEqual(cases["route-negative"]["judgments"][0]["value"], "none")
        self.assertIn("num_ctx=32768", result.payload["notes"])
        self.assertEqual(result.payload["jev_mode"], "live")
        for item in result.payload["results"]:
            self.assertEqual(schemas.validate_payload("benchmark-result", item, [support.SCHEMA_DIR]), [])

    def test_runtime_router(self):
        with FakeServices() as services:
            result = self.run_bench(
                "--tier",
                "trigger",
                "--runtime",
                "ollama-local",
                "--model",
                "qwen3:14b",
                "--router",
                "runtime",
                environ=services.environ(),
            )
            routing = [r.json() for r in services.ollama.requests_to("/api/chat")]
        cases = self.by_id(result)
        self.assertEqual({c["status"] for c in cases.values()}, {"pass"})
        self.assertEqual(cases["route-positive"]["runtime"], "ollama-local-zed-emulation")
        self.assertIn("routing_method=runtime", cases["route-positive"]["notes"])
        self.assertEqual(cases["route-positive"]["jev_mode"], "off")
        self.assertEqual(routing[0]["format"]["properties"]["skill"]["enum"], ["demo-skill", "lease-skill", "none"])
        self.assertEqual(services.jev.requests_to("/v1/systemone"), [])

    def test_unavailable_services_are_skipped_never_passed(self):
        result = self.run_bench("--tier", "agentic,trigger", environ={})
        cases = self.by_id(result)
        self.assertEqual({c["status"] for c in cases.values()}, {"skipped"})
        self.assertTrue(all(c["skip_reason"].startswith("LIVE_PREREQ_MISSING") for c in cases.values()))
        self.assertIsNone(result.payload["summary"]["agentic"]["pass_rate"])
        self.assertEqual(result.exit_code, EXIT_OK)
        self.assertEqual({w["code"] for w in result.warnings}, {"CASES_SKIPPED"})

    def test_jev_off_leaves_judged_cases_ungraded(self):
        with FakeServices() as services:
            result = self.run_bench(
                "--tier",
                "agentic",
                "--runtime",
                "ollama-local",
                "--model",
                "qwen3:14b",
                "--jev",
                "off",
                environ=services.environ(),
            )
        agentic = self.by_id(result)["agentic-restate"]
        self.assertEqual((agentic["status"], agentic["schema_valid"], agentic["judgments"]), ("skipped", True, []))
        self.assertIn("2 judgments not graded", agentic["skip_reason"])

    def test_missing_jev_key_means_off_without_network(self):
        with FakeServices() as services:
            environ = {"OLLAMA_HOST": services.ollama.url, "TYPESAFE_BASE_URL": services.jev.url}
            result = self.run_bench(
                "--tier", "agentic", "--runtime", "ollama-local", "--model", "qwen3:14b", environ=environ
            )
            self.assertEqual(services.jev.requests, [])
        agentic = self.by_id(result)["agentic-restate"]
        self.assertEqual(agentic["status"], "skipped")
        self.assertIn("JEV_NOT_CONFIGURED", agentic["skip_reason"])

    def test_uncertain_judgment_fails_and_flags_a_human(self):
        with FakeServices(noul=0.5) as services:
            result = self.run_bench(
                "--tier", "agentic", "--runtime", "ollama-local", "--model", "qwen3:14b", environ=services.environ()
            )
        agentic = self.by_id(result)["agentic-restate"]
        self.assertEqual(agentic["status"], "fail")
        grounded = agentic["judgments"][0]
        self.assertEqual((grounded["band"], grounded["pass"], grounded["needs_human"]), ("uncertain", False, True))
        self.assertIn("needs human review (uncertain): grounded", agentic["notes"])

    def test_record_then_replay_without_services(self):
        cassettes = os.path.join(self.out, "cassettes")
        with support.env(TYPESAFE_API_KEY=KEY), FakeServices() as services:
            live = self.run_bench(
                "--tier",
                "agentic,trigger",
                "--runtime",
                "ollama-local",
                "--model",
                "qwen3:14b",
                "--record",
                cassettes,
                environ=services.environ(),
            )
        for directory, _, files in os.walk(cassettes):
            for name in files:
                with open(os.path.join(directory, name), encoding="utf-8") as handle:
                    text = handle.read()
                self.assertNotIn(KEY, text)
                self.assertNotIn(self.repo.root, text)
        replayed = self.run_bench(
            "--tier",
            "agentic,trigger",
            "--runtime",
            "replay",
            "--model",
            "qwen3:14b",
            "--jev",
            "replay",
            "--cassettes",
            cassettes,
            environ={},
        )
        live_cases, replay_cases = self.by_id(live), self.by_id(replayed)
        self.assertEqual(
            {k: v["status"] for k, v in replay_cases.items()}, {k: v["status"] for k, v in live_cases.items()}
        )
        self.assertEqual(replay_cases["agentic-restate"]["jev_mode"], "replay")
        self.assertEqual(replay_cases["agentic-restate"]["runtime"], "replay-zed-emulation")
        self.assertEqual(replay_cases["agentic-restate"]["judgments"], live_cases["agentic-restate"]["judgments"])
        self.assertEqual(replayed.payload["jev_mode"], "replay")

    def test_replay_miss_is_skipped(self):
        cassettes = os.path.join(self.out, "empty-cassette")
        os.makedirs(os.path.join(cassettes, "runtime"))
        with open(os.path.join(cassettes, "runtime", "0" * 64 + ".json"), "w", encoding="utf-8") as handle:
            handle.write("{}")
        result = self.run_bench(
            "--tier", "agentic", "--runtime", "replay", "--jev", "replay", "--cassettes", cassettes, environ={}
        )
        agentic = self.by_id(result)["agentic-restate"]
        self.assertEqual(agentic["status"], "skipped")
        self.assertTrue(agentic["skip_reason"].startswith("CASSETTE_MISS"))

    def test_replay_needs_a_cassette(self):
        with self.assertRaises(ScriptError) as caught:
            self.run_bench("--tier", "agentic", "--runtime", "replay")
        self.assertEqual(caught.exception.code, "USAGE")

    def test_unreachable_runtime_is_skipped_with_reason(self):
        result = self.run_bench(
            "--tier",
            "agentic",
            "--runtime",
            "ollama-local",
            "--model",
            "qwen3:14b",
            environ={"OLLAMA_HOST": "127.0.0.1:9"},
        )
        agentic = self.by_id(result)["agentic-restate"]
        self.assertEqual((agentic["status"], agentic["runtime"]), ("skipped", "ollama-local"))
        self.assertIn("not reachable", agentic["skip_reason"])
        self.assertTrue(
            any(note.startswith("runtime unavailable: LIVE_PREREQ_MISSING") for note in result.payload["notes"])
        )


if __name__ == "__main__":
    unittest.main()
