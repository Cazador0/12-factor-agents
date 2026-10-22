"""Tests for _skillkit.envelope: construction, emission and the run_script contract."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import json
import unittest

from tests import skillkit_support
from tests.skillkit_support import Captured
from _skillkit import EXIT_EXTERNAL, EXIT_FAIL, EXIT_OK, EXIT_REFUSED, EXIT_USAGE, cli, envelope, schemas
from _skillkit.envelope import ScriptError, ScriptResult

PRODUCER = {"skill": "review-verifier", "script": "review_verdict.py", "version": "0.1.0"}
NOW = "2026-10-22T08:00:00Z"


def payload(**extra):
    doc = skillkit_support.load_example("review-verdict")
    doc.update(extra)
    return doc


class TestErrorHelpers(unittest.TestCase):
    def test_error_shape(self):
        self.assertEqual(
            envelope.error("CHECK_NOT_EXECUTED", "unit has no command", "/checks/0"),
            {"code": "CHECK_NOT_EXECUTED", "message": "unit has no command", "path": "/checks/0"},
        )
        self.assertEqual(envelope.error("X", "m")["path"], None)

    def test_error_message_is_compacted(self):
        message = envelope.error("X", "line one\n  line two\t" + "y" * 400)["message"]
        self.assertNotIn("\n", message)
        self.assertTrue(message.startswith("line one line two y"))
        self.assertEqual(len(message), envelope.MAX_MESSAGE_LENGTH)
        self.assertTrue(message.endswith("..."))

    def test_error_code_must_be_upper_snake(self):
        for code in ("bad-code", "lower", "", "9X", None):
            with self.subTest(code=code), self.assertRaises(ValueError):
                envelope.error(code, "m")

    def test_script_error(self):
        exc = ScriptError("LOCK_TIMEOUT", "busy", path="x.lock", exit_code=EXIT_EXTERNAL)
        self.assertEqual((exc.code, exc.message, exc.path, exc.exit_code), ("LOCK_TIMEOUT", "busy", "x.lock", 3))
        self.assertEqual(exc.to_dict(), {"code": "LOCK_TIMEOUT", "message": "busy", "path": "x.lock"})
        self.assertEqual(ScriptError("USAGE", "x").exit_code, EXIT_USAGE)
        for bad in (0, 5, -1):
            with self.subTest(exit_code=bad), self.assertRaises(ValueError):
                ScriptError("X", "m", exit_code=bad)


class TestMakeEnvelope(unittest.TestCase):
    def test_fields_and_schema_validity(self):
        env = envelope.make_envelope("review-verdict", payload(), ok=True, now=NOW, **PRODUCER)
        self.assertEqual(env["schema"], "urn:skill-lab:schema:envelope:v1")
        self.assertEqual(env["kind_schema"], "urn:skill-lab:schema:review-verdict:v1")
        self.assertEqual(env["producer"], PRODUCER)
        self.assertEqual(env["created_at"], NOW)
        self.assertEqual((env["errors"], env["warnings"], env["idempotency_key"]), ([], [], None))
        self.assertEqual(schemas.validate_envelope(env, exit_code=EXIT_OK), [])

    def test_now_accepts_datetime_string_or_clock(self):
        aware = dt.datetime(2026, 10, 22, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=2)))
        self.assertEqual(envelope.make_envelope("lease", {}, ok=False, now=aware, **PRODUCER)["created_at"], NOW)
        self.assertEqual(
            envelope.make_envelope("lease", {}, ok=False, now="2026-10-22 08:00", **PRODUCER)["created_at"], NOW
        )
        clock = envelope.make_envelope("lease", {}, ok=False, **PRODUCER)["created_at"]
        self.assertRegex(clock, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_string_messages_are_wrapped(self):
        env = envelope.make_envelope(
            "lease", None, ok=False, errors=["boom"], warnings=["careful", {"code": "W1", "message": "x"}], **PRODUCER
        )
        self.assertEqual(env["errors"], [{"code": "ERROR", "message": "boom", "path": None}])
        self.assertEqual(env["warnings"][0]["code"], "WARNING")
        self.assertEqual(env["warnings"][1], {"code": "W1", "message": "x", "path": None})

    def test_kind_must_be_a_contract_name(self):
        with self.assertRaises(ValueError):
            envelope.make_envelope("Review Verdict", {}, ok=True, **PRODUCER)

    def test_schema_urn(self):
        self.assertEqual(envelope.schema_urn("lease"), "urn:skill-lab:schema:lease:v1")
        self.assertEqual(envelope.schema_urn("lease", 2), "urn:skill-lab:schema:lease:v2")


class TestEmit(unittest.TestCase):
    def test_one_sorted_document_with_trailing_newline(self):
        out = Captured()
        envelope.emit({"b": 1, "a": "é"}, stream=out.stream)
        self.assertEqual(out.text(), '{"a":"é","b":1}\n')

    def test_pretty(self):
        out = Captured()
        envelope.emit({"b": 1, "a": 2}, pretty=True, stream=out.stream)
        self.assertEqual(out.text(), '{\n  "a": 2,\n  "b": 1\n}\n')

    def test_emit_redacts(self):
        out = Captured()
        with skillkit_support.env(GITEA_TOKEN="gitea-secret-0001"):
            envelope.emit({"message": "used gitea-secret-0001", "token": "x"}, stream=out.stream)
        self.assertNotIn("gitea-secret-0001", out.text())
        self.assertEqual(json.loads(out.text()), {"message": "used ***", "token": "***"})

    def test_text_stream_without_buffer(self):
        stream = io.StringIO()
        envelope.emit({"a": 1}, stream=stream)
        self.assertEqual(stream.getvalue(), '{"a":1}\n')

    def test_dumps_rejects_nan(self):
        with self.assertRaises(ValueError):
            envelope.dumps({"x": float("nan")})


class RunScriptTest(unittest.TestCase):
    def run_main(self, main, argv=(), kind="review-verdict"):
        out = Captured()
        with skillkit_support.captured_stderr() as err:
            code = envelope.run_script(main, kind=kind, argv=list(argv), stream=out.stream, **PRODUCER)
        text = out.text()
        self.assertEqual(text.count("\n"), 1 if text else 0, "exactly one JSON line on stdout")
        doc = json.loads(text) if text else None
        return code, doc, err.getvalue()


class TestRunScript(RunScriptTest):
    def test_success(self):
        code, doc, _ = self.run_main(lambda: (EXIT_OK, payload(), [], []), ["--now", NOW])
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["created_at"], NOW)
        self.assertEqual(schemas.validate_envelope(doc, exit_code=code), [])

    def test_completed_but_failing(self):
        failing = payload()
        code, doc, _ = self.run_main(
            lambda: (EXIT_FAIL, failing, [envelope.error("CHANGES_REQUESTED", "1 blocker")], [])
        )
        self.assertEqual(code, EXIT_FAIL)
        self.assertFalse(doc["ok"])
        self.assertEqual(doc["errors"][0]["code"], "CHANGES_REQUESTED")
        self.assertEqual(schemas.validate_envelope(doc, exit_code=code), [])

    def test_ok_is_exactly_exit_zero(self):
        for exit_code in (EXIT_OK, EXIT_FAIL, EXIT_EXTERNAL, EXIT_REFUSED):
            with self.subTest(exit_code=exit_code):
                errors = [] if exit_code == EXIT_OK else ["x"]
                code, doc, _ = self.run_main(lambda code=exit_code, errs=errors: (code, payload(), errs, []))
                self.assertEqual(code, exit_code)
                self.assertEqual(doc["ok"], exit_code == EXIT_OK)

    def test_script_error(self):
        def main():
            raise ScriptError("APPLY_REQUIRED", "mutation needs --apply", exit_code=EXIT_REFUSED)

        code, doc, _ = self.run_main(main)
        self.assertEqual(code, EXIT_REFUSED)
        self.assertEqual(doc["errors"], [{"code": "APPLY_REQUIRED", "message": "mutation needs --apply", "path": None}])
        self.assertIsNone(doc["payload"])
        self.assertEqual(schemas.validate_envelope(doc, exit_code=code), [])

    def test_unexpected_exception_is_internal_without_traceback(self):
        def main():
            raise KeyError("missing-thing")

        with skillkit_support.env(SKILLKIT_DEBUG=None):
            code, doc, stderr = self.run_main(main)
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(doc["errors"][0]["code"], "INTERNAL")
        self.assertEqual(doc["errors"][0]["message"], "KeyError: 'missing-thing'")
        self.assertNotIn("Traceback", json.dumps(doc))
        self.assertNotIn("Traceback", stderr)

    def test_debug_prints_traceback_to_stderr_only(self):
        def main():
            raise RuntimeError("boom")

        with skillkit_support.env(SKILLKIT_DEBUG="1"):
            code, doc, stderr = self.run_main(main)
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("Traceback", stderr)
        self.assertNotIn("Traceback", json.dumps(doc))

    def test_secrets_are_redacted_everywhere(self):
        def main():
            raise RuntimeError("401 for token typesafe-secret-xyz at https://u:p@host/x")

        with skillkit_support.env(TYPESAFE_API_KEY="typesafe-secret-xyz"):
            _, doc, _ = self.run_main(main)
        message = doc["errors"][0]["message"]
        self.assertNotIn("typesafe-secret-xyz", message)
        self.assertNotIn("u:p@", message)

    def test_usage_error_from_base_parser(self):
        def main():
            cli.base_parser("demo").parse_args(["--bogus"])
            return EXIT_OK, {}, [], []

        code, doc, stderr = self.run_main(main, ["--bogus"])
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(doc["errors"][0]["code"], "USAGE")
        self.assertIn("--bogus", doc["errors"][0]["message"])
        self.assertIn("usage:", stderr)

    def test_help_exits_zero_without_envelope(self):
        def main():
            argparse.ArgumentParser(prog="demo").parse_args(["--help"])

        out = Captured()
        with contextlib.redirect_stdout(io.StringIO()):
            code = envelope.run_script(main, kind="lease", argv=["--help"], stream=out.stream, **PRODUCER)
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.text(), "")

    def test_plain_argparse_failure_becomes_usage(self):
        def main():
            argparse.ArgumentParser(prog="demo").parse_args(["--nope"])

        code, doc, _ = self.run_main(main)
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(doc["errors"][0]["code"], "USAGE")

    def test_pretty_and_now_are_honoured_on_failure(self):
        def main():
            raise ScriptError("INPUT_NOT_FOUND", "file not found", path="x.json")

        out = Captured()
        code = envelope.run_script(
            main, kind="lease", argv=["--pretty", "--now=2026-10-22T08:00:00Z"], stream=out.stream, **PRODUCER
        )
        self.assertEqual(code, EXIT_USAGE)
        self.assertTrue(out.text().startswith("{\n  "))
        self.assertEqual(json.loads(out.text())["created_at"], NOW)

    def test_bad_now_falls_back_to_clock(self):
        code, doc, _ = self.run_main(lambda: (EXIT_OK, payload(), [], []), ["--now", "yesterday"])
        self.assertEqual(code, EXIT_OK)
        self.assertRegex(doc["created_at"], r"Z$")

    def test_script_result_idempotency_key_and_kind(self):
        lease = skillkit_support.load_example("lease")
        code, doc, _ = self.run_main(lambda: ScriptResult(EXIT_OK, lease, idempotency_key="idem-abc", kind="lease"))
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(
            (doc["kind"], doc["kind_schema"], doc["idempotency_key"]),
            ("lease", "urn:skill-lab:schema:lease:v1", "idem-abc"),
        )
        self.assertEqual(schemas.validate_envelope(doc, exit_code=code), [])

    def test_contract_violations_by_main_are_internal(self):
        cases = {
            "wrong shape": lambda: (0, {}),
            "bad exit code": lambda: (7, {}, [], []),
            "bool exit code": lambda: (True, {}, [], []),
            "non-dict payload": lambda: (0, [1], [], []),
            "exit 0 without payload": lambda: (0, None, [], []),
            "exit 1 without payload": lambda: (1, None, ["x"], []),
            "exit 0 with errors": lambda: (0, {}, ["x"], []),
            "bad error code": lambda: (1, {}, [{"code": "bad", "message": "m"}], []),
            "bad kind override": lambda: ScriptResult(0, {}, kind="Bad Kind"),
        }
        for label, main in cases.items():
            with self.subTest(label):
                code, doc, _ = self.run_main(main)
                self.assertEqual(code, EXIT_USAGE)
                self.assertEqual(doc["errors"][0]["code"], "INTERNAL")
                self.assertIsNone(doc["payload"])

    def test_non_json_payload_is_internal(self):
        code, doc, _ = self.run_main(lambda: (EXIT_OK, {"x": float("nan")}, [], []))
        self.assertEqual(code, EXIT_USAGE)
        self.assertEqual(doc["errors"][0]["code"], "INTERNAL")
        self.assertIn("not JSON", doc["errors"][0]["message"])
        code, doc, _ = self.run_main(lambda: (EXIT_OK, {"x": object()}, [], []))
        self.assertEqual(doc["errors"][0]["code"], "INTERNAL")

    def test_invalid_kind_is_a_programming_error(self):
        with self.assertRaises(ValueError):
            envelope.run_script(lambda: None, kind="Not A Kind", argv=[], **PRODUCER)


if __name__ == "__main__":
    unittest.main()
