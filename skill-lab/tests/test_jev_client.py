"""SPEC-103 Jev (TypeSafe System One) client against a fake TypeSafe API on 127.0.0.1."""

from __future__ import annotations

import socket
import unittest

from tests.test_bench_fakes import FakeServer, Reply, jev_answers, jev_models
from lab import jev
from lab.runtimes.transport import RetryPolicy

KEY = "ts-canary-key-5f2c9a7e1b"
NOUL = {
    "type": "noul",
    "instructions": "The verdict cites evidence for every blocker.",
    "criteria": {"true": "cites", "false": "does not"},
}
CHOICE = {"type": "choice", "instructions": "Which tone?", "criteria": {"calm": "neutral", "angry": "hostile"}}
SCORE = {"type": "score", "instructions": "How complete?", "criteria": ["missing", "partial", "complete"]}


def client(server, **kwargs):
    kwargs.setdefault("sleep", lambda seconds: None)
    kwargs.setdefault("log", None)
    return jev.JevClient(KEY, base_url=server.url, **kwargs)


class TestConfiguration(unittest.TestCase):
    def test_key_precedence_and_defaults(self):
        self.assertEqual(jev.resolve_api_key({"TYPESAFE_API_KEY": " a ", "JEV_API_KEY": "b"}), "a")
        self.assertEqual(jev.resolve_api_key({"JEV_API_KEY": "b"}), "b")
        self.assertIsNone(jev.resolve_api_key({"TYPESAFE_API_KEY": "  "}))
        made = jev.JevClient.from_env({"JEV_API_KEY": "b"})
        self.assertEqual((made.base_url, made.model, made.timeout), ("https://api.typesafe.ai", "jev-latest", 30.0))
        custom = jev.JevClient.from_env(
            {"TYPESAFE_API_KEY": "a", "TYPESAFE_BASE_URL": "http://x/", "TYPESAFE_DEFAULT_MODEL": "jev-2026-09-15"}
        )
        self.assertEqual((custom.base_url, custom.model), ("http://x", "jev-2026-09-15"))

    def test_missing_or_malformed_key(self):
        with self.assertRaises(jev.JevConfigError):
            jev.JevClient.from_env({})
        with self.assertRaises(jev.JevConfigError):
            jev.JevClient("has space")

    def test_question_checks_happen_before_any_request(self):
        with FakeServer() as server:
            for questions in (
                {},
                {"q": {"type": "box"}},
                {"q": {"type": "choice", "criteria": {}}},
                {"q": {"type": "score", "criteria": []}},
            ):
                with self.subTest(questions=questions), self.assertRaises(jev.JevConfigError):
                    client(server).ask("state", questions)
        self.assertEqual(server.requests, [])


class TestSystemOne(unittest.TestCase):
    def test_request_shape_and_typed_answers(self):
        answers = {
            "cites": {"type": "noul", "noul": 0.93},
            "tone": {
                "type": "choice",
                "choice": "calm",
                "confidence": 0.8,
                "probabilities": {"calm": 0.8, "angry": 0.2},
            },
            "done": {
                "type": "score",
                "score": 1.7,
                "confidence": 0.6,
                "legend": {"0": "missing", "1": "partial", "2": "complete"},
                "probabilities": {"0": 0.1, "1": 0.1, "2": 0.8},
            },
        }
        with FakeServer() as server:
            server.route("POST", "/v1/systemone", jev_answers(answers, "req-42"))
            result = client(server).ask({"output": {"a": 1}}, {"cites": NOUL, "tone": CHOICE, "done": SCORE})
        sent = server.requests[0]
        self.assertEqual(sent.path, "/v1/systemone")
        self.assertEqual(sent.headers["authorization"], "Bearer " + KEY)
        self.assertEqual(sent.headers["content-type"], "application/json")
        self.assertEqual(sent.headers["accept"], "application/json")
        self.assertTrue(sent.headers["user-agent"].startswith("skill-lab/"))
        self.assertEqual(
            sent.json(),
            {
                "model": "jev-latest",
                "state": {"output": {"a": 1}},
                "questions": {"cites": NOUL, "tone": CHOICE, "done": SCORE},
            },
        )
        self.assertEqual(result.request_id, "req-42")
        self.assertEqual(result.model, "jev-2026-09-15")
        self.assertEqual(result.usage, jev.Usage(120, 12))
        self.assertEqual(result.answers["cites"], jev.NoulAnswer(0.93))
        self.assertEqual(result.answers["tone"].choice, "calm")
        self.assertIsInstance(result.answers["done"], jev.ScoreAnswer)
        self.assertEqual(result.answers["done"].score, 1.7)

    def test_429_with_retry_after_is_retried(self):
        sleeps = []
        with FakeServer() as server:
            server.route(
                "POST",
                "/v1/systemone",
                Reply(429, {"error": "slow down"}, {"retry-after": "2"}),
                Reply(503, {"error": "busy"}, {"retry-after-ms": "250"}),
                jev_answers({"q": {"type": "noul", "noul": 0.5}}),
            )
            result = client(server, sleep=sleeps.append).ask("s", {"q": NOUL})
        self.assertEqual(sleeps, [2.0, 0.25])
        self.assertEqual(result.answers["q"].noul, 0.5)
        retries = [request.headers.get("x-typesafe-retry-count") for request in server.requests]
        self.assertEqual(retries, [None, "1", "2"])

    def test_retries_are_bounded_then_http_error(self):
        with FakeServer() as server:
            server.route("POST", "/v1/systemone", Reply(500, {"error": "oops"}, {"x-typesafe-request-id": "r9"}))
            with self.assertRaises(jev.JevHTTPError) as caught:
                client(server, retry=RetryPolicy(max_retries=3)).ask("s", {"q": NOUL})
        self.assertEqual(len(server.requests), 4)
        self.assertEqual((caught.exception.status, caught.exception.request_id), (500, "r9"))

    def test_422_carries_the_detail_list(self):
        detail = [{"loc": ["body", "questions", "q", "criteria"], "msg": "Field required", "type": "missing"}]
        with FakeServer() as server:
            server.route("POST", "/v1/systemone", Reply(422, {"detail": detail}))
            with self.assertRaises(jev.JevValidationError) as caught:
                client(server).ask("s", {"q": NOUL})
        self.assertEqual(caught.exception.detail, detail)
        self.assertIn("questions.q.criteria: Field required", caught.exception.message)
        self.assertEqual(len(server.requests), 1)

    def test_401_and_403_are_auth_errors_without_the_key(self):
        for status in (401, 403):
            with self.subTest(status=status), FakeServer() as server:
                server.route("POST", "/v1/systemone", Reply(status, {"error": "bad key %s" % KEY}))
                with self.assertRaises(jev.JevAuthError) as caught:
                    client(server).ask("s", {"q": NOUL})
                self.assertEqual(caught.exception.code, "JEV_AUTH")
                self.assertNotIn(KEY, str(caught.exception))

    def test_retry_log_never_contains_the_key(self):
        lines = []
        with FakeServer() as server:
            server.route("POST", "/v1/systemone", Reply(502, {}), jev_answers({"q": {"type": "noul", "noul": 0.9}}))
            client(server, log=lines.append).ask("s", {"q": NOUL})
        self.assertEqual(len(lines), 1)
        self.assertIn("HTTP 502", lines[0])
        self.assertNotIn(KEY, lines[0])

    def test_connection_failure(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        dead = jev.JevClient(
            KEY, base_url="http://127.0.0.1:%d" % port, sleep=lambda s: None, log=None, retry=RetryPolicy(max_retries=1)
        )
        with self.assertRaises(jev.JevConnectionError):
            dead.ask("s", {"q": NOUL})

    def test_list_models(self):
        with FakeServer() as server:
            server.route("GET", "/v1/models", jev_models())
            models = client(server).list_models()
        self.assertEqual(models, [jev.ModelInfo("jev-latest", "General-purpose system one model.", "2026-09-15")])
        self.assertEqual(server.requests[0].body, b"")


class TestStrictResponses(unittest.TestCase):
    QUESTIONS = {"q": NOUL, "tone": CHOICE, "done": SCORE}
    GOOD = {
        "q": {"type": "noul", "noul": 0.2},
        "tone": {"type": "choice", "choice": "angry", "confidence": 0.7, "probabilities": {"calm": 0.3, "angry": 0.7}},
        "done": {"type": "score", "score": 2.0, "confidence": 0.9, "legend": {}, "probabilities": {"2": 1.0}},
    }

    def parse(self, answers=None, **body):
        document = {
            "model": "m",
            "answers": self.GOOD if answers is None else answers,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        document.update(body)
        return jev.parse_system_one(document, self.QUESTIONS, "rid")

    def broken(self, name, **changes):
        answers = {key: dict(value) for key, value in self.GOOD.items()}
        answers[name].update(changes)
        return answers

    def test_good_response_parses(self):
        self.assertEqual(set(self.parse().answers), {"q", "tone", "done"})

    def test_protocol_violations(self):
        cases = {
            "unknown answer type": self.broken("q", type="box"),
            "type mismatch": self.broken("q", type="choice"),
            "probability above 1": self.broken("q", noul=1.2),
            "boolean is not a number": self.broken("q", noul=True),
            "choice not a label": self.broken("tone", choice="sad"),
            "confidence missing": {**self.GOOD, "tone": {"type": "choice", "choice": "calm", "probabilities": {}}},
            "score above top level": self.broken("done", score=2.5),
            "missing answer": {"q": self.GOOD["q"], "tone": self.GOOD["tone"]},
            "extra answer": {**self.GOOD, "other": {"type": "noul", "noul": 0.1}},
        }
        for label, answers in cases.items():
            with self.subTest(label), self.assertRaises(jev.JevProtocolError) as caught:
                self.parse(answers)
            self.assertEqual(caught.exception.request_id, "rid")
        for body in ({"usage": {"input_tokens": 1}}, {"model": 7}, {"usage": {"input_tokens": -1, "output_tokens": 0}}):
            with self.subTest(body=body), self.assertRaises(jev.JevProtocolError):
                self.parse(**body)

    def test_non_json_200_is_a_protocol_error(self):
        with FakeServer() as server:
            server.route("POST", "/v1/systemone", Reply(200, b"<html>"))
            with self.assertRaises(jev.JevProtocolError):
                client(server).ask("s", {"q": NOUL})


class TestBuilders(unittest.TestCase):
    JUDGMENTS = [
        {
            "id": "a",
            "type": "noul",
            "instructions": "A?",
            "criteria": {"true": "y", "false": "n"},
            "state_from": ["output", "prompt"],
            "pass_if": {"gte": 0.8},
        },
        {
            "id": "b",
            "type": "score",
            "instructions": "B?",
            "criteria": ["0", "1"],
            "state_from": ["prompt", "output"],
            "pass_if": {"gte": 1},
        },
        {
            "id": "c",
            "type": "choice",
            "instructions": "C?",
            "criteria": {"x": None},
            "state_from": ["skill"],
            "pass_if": {"eq": "x"},
        },
    ]

    def test_question_for_drops_runner_fields(self):
        self.assertEqual(
            jev.question_for(self.JUDGMENTS[0]),
            {"type": "noul", "instructions": "A?", "criteria": {"true": "y", "false": "n"}},
        )

    def test_batches_group_by_state_from_set(self):
        batches = jev.judgment_batches(self.JUDGMENTS)
        self.assertEqual(
            [(key, [j["id"] for j in group]) for key, group in batches],
            [(("output", "prompt"), ["a", "b"]), (("skill",), ["c"])],
        )

    def test_build_state_only_includes_declared_parts(self):
        state = jev.build_state(
            ["output", "skill"], skill={"name": "s"}, prompt="p", fixtures={"f": 1}, output={"o": 1}
        )
        self.assertEqual(state, {"skill": {"name": "s"}, "output": {"o": 1}})
        self.assertEqual(
            list(
                jev.build_state(
                    ["output", "prompt", "fixtures", "skill"], skill={}, prompt="p", fixtures={}, output=None
                )
            ),
            ["skill", "prompt", "fixtures", "output"],
        )

    def test_routing_question(self):
        question = jev.routing_question([("review-verifier", "Verify a PR."), ("work-lease", "Lease work.")])
        self.assertEqual(question["type"], "choice")
        self.assertEqual(
            question["criteria"],
            {
                "review-verifier": "Verify a PR.",
                "work-lease": "Lease work.",
                "none": "No installed skill fits this request",
            },
        )
        self.assertIn("Choose 'none'", question["instructions"])
        with self.assertRaises(jev.JevConfigError):
            jev.routing_question([("none", "collides")])


if __name__ == "__main__":
    unittest.main()
