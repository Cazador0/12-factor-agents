"""Tests for _skillkit.cli: common flags, strict input reading, --now."""

from __future__ import annotations

import datetime as dt
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from tests import skillkit_support
from _skillkit import EXIT_USAGE, cli
from _skillkit.envelope import ScriptError


class TestParser(unittest.TestCase):
    def test_common_flags_and_defaults(self):
        args = cli.base_parser("demo").parse_args([])
        self.assertEqual((args.pretty, args.now, args.state_dir), (False, None, os.path.join(".", ".skill-state")))
        args = cli.base_parser("demo").parse_args(
            ["--pretty", "--now", "2026-10-22T08:00:00Z", "--state-dir", "/tmp/s"]
        )
        self.assertEqual((args.pretty, args.now, args.state_dir), (True, "2026-10-22T08:00:00Z", "/tmp/s"))

    def test_usage_errors_raise_script_error(self):
        parser = cli.base_parser("demo")
        parser.add_argument("--input", required=True)
        with skillkit_support.captured_stderr() as err:
            with self.assertRaises(ScriptError) as ctx:
                parser.parse_args([])
        self.assertEqual((ctx.exception.code, ctx.exception.exit_code), ("USAGE", EXIT_USAGE))
        self.assertIn("--input", ctx.exception.message)
        self.assertIn("usage:", err.getvalue())

    def test_subparsers_inherit_behaviour_and_can_take_common_flags(self):
        parser = cli.base_parser("demo", common=False)
        sub = parser.add_subparsers(dest="command", required=True)
        validate = cli.add_common_arguments(sub.add_parser("validate"))
        cli.add_input_argument(validate)
        args = parser.parse_args(["validate", "--input", "x.json", "--pretty"])
        self.assertEqual((args.command, args.input, args.pretty), ("validate", "x.json", True))
        with skillkit_support.captured_stderr(), self.assertRaises(ScriptError):
            parser.parse_args(["validate"])
        with skillkit_support.captured_stderr(), self.assertRaises(ScriptError):
            parser.parse_args(["bogus"])

    def test_help_exits_zero(self):
        with mock.patch("sys.stdout", new=io.StringIO()) as out, self.assertRaises(SystemExit) as ctx:
            cli.base_parser("demo tool").parse_args(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("demo tool", out.getvalue())

    def test_optional_input_argument(self):
        parser = cli.add_input_argument(cli.base_parser("demo"), required=False)
        self.assertIsNone(parser.parse_args([]).input)


class TestReadJson(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, data):
        path = os.path.join(self.dir, name)
        with open(path, "wb") as handle:
            handle.write(data if isinstance(data, bytes) else data.encode("utf-8"))
        return path

    def assert_code(self, path, code):
        with self.assertRaises(ScriptError) as ctx:
            cli.read_json(path)
        self.assertEqual(ctx.exception.code, code)
        self.assertEqual(ctx.exception.exit_code, EXIT_USAGE)
        return ctx.exception

    def test_reads_a_file(self):
        self.assertEqual(cli.read_json(self.write("a.json", '{"a": [1, "é"]}')), {"a": [1, "é"]})

    def test_tolerates_a_bom(self):
        self.assertEqual(cli.read_json(self.write("a.json", b'\xef\xbb\xbf{"a": 1}')), {"a": 1})

    def test_reads_stdin(self):
        with mock.patch("sys.stdin", new=io.StringIO("[1, 2]")):
            self.assertEqual(cli.read_json("-"), [1, 2])

    def test_missing_file(self):
        error = self.assert_code(os.path.join(self.dir, "nope.json"), "INPUT_NOT_FOUND")
        self.assertTrue(error.path.endswith("nope.json"))

    def test_directory(self):
        self.assert_code(self.dir, "INPUT_UNREADABLE")

    def test_bad_json_reports_line_and_column(self):
        error = self.assert_code(self.write("bad.json", '{\n  "a": 1\n  "b": 2\n}'), "INPUT_NOT_JSON")
        self.assertTrue(error.path.endswith("bad.json:3:3"), error.path)
        self.assertIn("delimiter", error.message)

    def test_bad_json_on_stdin(self):
        with mock.patch("sys.stdin", new=io.StringIO("{oops")):
            with self.assertRaises(ScriptError) as ctx:
                cli.read_json("-")
        self.assertEqual(ctx.exception.code, "INPUT_NOT_JSON")
        self.assertTrue(ctx.exception.path.startswith("<stdin>:1:"))

    def test_nan_and_infinity_are_rejected(self):
        for text in ('{"a": NaN}', "[Infinity]", "[-Infinity]"):
            with self.subTest(text=text):
                self.assert_code(self.write("n.json", text), "INPUT_NOT_JSON")

    def test_overflowing_numbers_are_rejected(self):
        error = self.assert_code(self.write("big.json", '{"x": 1e400}'), "INPUT_NOT_JSON")
        self.assertIn("out of range", error.message)
        self.assertEqual(cli.read_json(self.write("ok.json", "[1.5e300, -2.0, 10]")), [1.5e300, -2.0, 10])

    def test_pathological_nesting_is_rejected(self):
        error = self.assert_code(self.write("deep.json", "[" * 200000 + "]" * 200000), "INPUT_NOT_JSON")
        self.assertIn("nested", error.message)

    def test_duplicate_keys_are_rejected(self):
        error = self.assert_code(self.write("d.json", '{"ok": true, "nested": {"x": 1, "x": 2}}'), "INPUT_NOT_JSON")
        self.assertIn("duplicate", error.message)

    def test_non_utf8_is_not_json(self):
        self.assert_code(self.write("l1.json", b'{"a": "\xff"}'), "INPUT_NOT_JSON")

    def test_read_text(self):
        self.assertEqual(cli.read_text(self.write("t.md", "- [ ] T001\n")), "- [ ] T001\n")
        with self.assertRaises(ScriptError) as ctx:
            cli.read_text(self.write("bin", b"\xff\xfe\x00"))
        self.assertEqual(ctx.exception.code, "INPUT_NOT_TEXT")

    @unittest.skipUnless(
        os.name == "posix" and hasattr(os, "geteuid") and os.geteuid() != 0, "needs a non-root POSIX user"
    )
    def test_unreadable_file(self):
        path = self.write("secret.json", "{}")
        os.chmod(path, 0)
        self.assert_code(path, "INPUT_UNREADABLE")


class TestLoadsStrict(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(cli.loads_strict('{"level": "shadow", "deny": []}'), {"level": "shadow", "deny": []})

    def test_rejections_are_value_errors(self):
        for text in ('{"a": 1, "a": 2}', "[NaN]", "[1e999]", "[" * 100000 + "]" * 100000, "{oops"):
            with self.subTest(text=text[:20]), self.assertRaises(ValueError):
                cli.loads_strict(text)

    def test_syntax_errors_keep_their_position(self):
        with self.assertRaises(json.JSONDecodeError) as ctx:
            cli.loads_strict('{\n  "a" 1\n}')
        self.assertEqual((ctx.exception.lineno, ctx.exception.colno), (2, 7))


class TestNow(unittest.TestCase):
    def test_parse_now_given(self):
        self.assertEqual(
            cli.parse_now("2026-10-22T10:00:00+02:00"), dt.datetime(2026, 10, 22, 8, tzinfo=dt.timezone.utc)
        )

    def test_parse_now_defaults_to_aware_utc_clock(self):
        for value in (None, ""):
            now = cli.parse_now(value)
            self.assertEqual(now.utcoffset(), dt.timedelta(0))
            self.assertLess(abs((dt.datetime.now(dt.timezone.utc) - now).total_seconds()), 5)

    def test_parse_now_invalid(self):
        with self.assertRaises(ScriptError) as ctx:
            cli.parse_now("tomorrow")
        self.assertEqual(
            (ctx.exception.code, ctx.exception.path, ctx.exception.exit_code), ("INVALID_NOW", "--now", EXIT_USAGE)
        )

    def test_to_iso(self):
        self.assertEqual(cli.to_iso(cli.parse_now("2026-10-22T08:00:00.9Z")), "2026-10-22T08:00:00Z")


class TestLog(unittest.TestCase):
    def test_log_goes_to_stderr_redacted(self):
        with skillkit_support.env(GITEA_TOKEN="gitea-token-123456"):
            with skillkit_support.captured_stderr() as err, mock.patch("sys.stdout", new=io.StringIO()) as out:
                cli.log("calling gitea with gitea-token-123456\n")
        self.assertEqual(err.getvalue(), "calling gitea with ***\n")
        self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
