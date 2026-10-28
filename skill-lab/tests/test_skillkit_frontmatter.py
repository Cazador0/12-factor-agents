"""Tests for _skillkit.frontmatter: the strict portable subset and the §2 field rules."""

from __future__ import annotations

import unittest

from tests import skillkit_support  # noqa: F401
from _skillkit import frontmatter as fm

GOOD = (
    "---\n"
    "name: review-verifier\n"
    'description: "Independently verify a pull request against its spec. Use when a PR needs a \\"verdict\\"."\n'
    "license: Apache-2.0\n"
    'compatibility: "Zed Agent (Ollama local or cloud), Claude Code, Codex. Scripts need python3 >= 3.9."\n'
    "metadata:\n"
    '  version: "0.1.0"\n'
    "  family: roles\n"
    "  spec: SPEC-003\n"
    "  author: Cazador0\n"
    "---\n"
    "# Review verifier\n"
    "\n"
    "## When to use\n"
)


GOOD_DESCRIPTION = GOOD.splitlines()[2]


def body_lines(text):
    """Frontmatter lines between the delimiters of GOOD, replaced by ``text``."""
    return "---\n" + text + "---\nbody\n"


def issue_keywords(text):
    return [issue.keyword for issue in fm.parse(text).issues]


class TestAccept(unittest.TestCase):
    def test_canonical_example(self):
        result = fm.parse(GOOD)
        self.assertEqual(result.issues, [])
        self.assertTrue(result.ok)
        self.assertEqual(result.data["name"], "review-verifier")
        self.assertEqual(
            result.data["description"],
            'Independently verify a pull request against its spec. Use when a PR needs a "verdict".',
        )
        self.assertEqual(
            result.data["metadata"], {"version": "0.1.0", "family": "roles", "spec": "SPEC-003", "author": "Cazador0"}
        )
        self.assertEqual(list(result.data), ["name", "description", "license", "compatibility", "metadata"])
        self.assertEqual(result.body, "# Review verifier\n\n## When to use\n")
        self.assertEqual(result.body_start_line, 12)
        self.assertEqual(result.styles["description"], "double")
        self.assertEqual(result.styles["metadata.family"], "plain")
        self.assertEqual(result.lines["metadata.spec"], 9)
        self.assertFalse(result.bom)
        self.assertEqual(fm.lint(result, folder_name="review-verifier"), [])

    def test_crlf_line_endings(self):
        text = GOOD.replace("\n", "\r\n")
        result = fm.parse(text)
        self.assertEqual(result.issues, [])
        self.assertEqual(result.data["metadata"]["author"], "Cazador0")
        self.assertEqual(result.body, "# Review verifier\r\n\r\n## When to use\r\n")
        self.assertEqual(fm.lint(result), [])

    def test_leading_bom_and_whitespace_like_zed_trim_start(self):
        result = fm.parse("\ufeff\n\n  \n" + GOOD)
        self.assertEqual(result.issues, [])
        self.assertTrue(result.bom)
        self.assertEqual(result.body_start_line, 15)
        self.assertEqual(result.lines["name"], 5)

    def test_closing_delimiter_at_end_of_file(self):
        result = fm.parse("---\nname: x\n---")
        self.assertEqual((result.issues, result.data, result.body), ([], {"name": "x"}, ""))

    def test_booleans_blank_lines_and_escapes(self):
        result = fm.parse(body_lines('name: x\n\ndisable-model-invocation: true\nd: "a \\\\ b"\ne: false\n'))
        self.assertEqual(result.issues, [])
        self.assertEqual(result.data, {"name": "x", "disable-model-invocation": True, "d": "a \\ b", "e": False})

    def test_unicode_and_inner_punctuation(self):
        result = fm.parse(
            body_lines('name: x\nauthor: José Ñ\nnote: "50% faster: really"\nurl: https://example.com/a?b=c\n')
        )
        self.assertEqual(result.issues, [])
        self.assertEqual(result.data["author"], "José Ñ")
        self.assertEqual(result.data["url"], "https://example.com/a?b=c")

    def test_only_first_closing_delimiter_counts(self):
        result = fm.parse("---\nname: x\n---\nbody\n---\nmore\n")
        self.assertEqual(result.body, "body\n---\nmore\n")

    def test_trailing_spaces_after_values_are_ignored(self):
        result = fm.parse(body_lines('name: x   \nd: "q"   \n'))
        self.assertEqual((result.issues, result.data), ([], {"name": "x", "d": "q"}))


class TestReject(unittest.TestCase):
    MATRIX = {
        "missing_open_delimiter": ["# Title\n", "", "name: x\n---\n"],
        "missing_close_delimiter": ["---\nname: x\n", "---\nname: x\n--- \n", "---\nname: x\n----\n"],
    }

    def test_delimiters(self):
        for keyword, texts in self.MATRIX.items():
            for text in texts:
                with self.subTest(text=text):
                    self.assertEqual(issue_keywords(text), [keyword])
        self.assertEqual(issue_keywords("---x\nname: x\n---\n"), ["missing_open_delimiter"])

    def test_line_constructs(self):
        cases = {
            "tab": "name:\tx\n",
            "comment": "# a comment\n",
            "list": "- item\n",
            "bad_line": "name:x\n",
            "duplicate_key": "name: x\nname: y\n",
            "empty_value": "name:\n",
            "bad_metadata": "metadata: flat\n",
            "bad_indent": "name: x\n   indented: 1\n",
            "control_character": "name: a\x07b\n",
        }
        for keyword, text in cases.items():
            with self.subTest(keyword=keyword):
                self.assertIn(keyword, issue_keywords(body_lines(text)))

    def test_multiline_plain_scalar_is_rejected(self):
        self.assertEqual(issue_keywords(body_lines("description: first\n  second\n")), ["bad_indent"])

    def test_quoted_keys_are_rejected(self):
        self.assertEqual(issue_keywords(body_lines('"name": x\n')), ["bad_line"])

    def test_scalar_constructs(self):
        cases = {
            "block_scalar": ["description: |\n  text\n", "description: >-\n"],
            "flow_collection": ["tags: [a, b]\n", "metadata: {a: 1}\n"],
            "anchor": ["name: &a x\n", "name: *a\n"],
            "tag": ["name: !!str x\n"],
            "single_quoted": ["name: 'x'\n"],
            "comment": ["name: x # trailing\n", 'name: "x" # trailing\n'],
            "trailing_content": ['name: "x" y\n'],
            "bad_escape": ['name: "a\\nb"\n', 'name: "a\\tb"\n', 'name: "\\u0041"\n'],
            "unterminated_string": ['name: "abc\n', 'name: "abc\\"\n'],
            "bad_plain_scalar": [
                "name: a: b\n",
                "name: x:\n",
                "name: @x\n",
                "name: `x`\n",
                "name: %x\n",
                "name: ?x\n",
                "name: -x\n",
            ],
            "list": ["name: - x\n"],
        }
        for keyword, texts in cases.items():
            for text in texts:
                with self.subTest(text=text):
                    self.assertEqual(issue_keywords(body_lines(text))[:1], [keyword])

    def test_block_scalar_continuation_is_also_reported(self):
        self.assertEqual(issue_keywords(body_lines("description: |\n  text\n")), ["block_scalar", "bad_indent"])

    def test_ambiguous_plain_scalars_must_be_quoted(self):
        for value in (
            "yes",
            "No",
            "on",
            "OFF",
            "y",
            "True",
            "FALSE",
            "null",
            "~",
            "1",
            "1.0",
            "-3",
            "1e5",
            ".5",
            "0x1F",
            "0o17",
            ".inf",
            ".NaN",
            "1_000",
            "12:30:00",
            "2026-10-22",
            "2026-10-22T08:00:00Z",
        ):
            with self.subTest(value=value):
                self.assertEqual(issue_keywords(body_lines("version: %s\n" % value)), ["ambiguous_scalar"])
        for value in ("0.1.0", "v1", "SPEC-003", "1.2.3-rc.1", "roles", "Apache-2.0"):
            with self.subTest(value=value):
                self.assertEqual(issue_keywords(body_lines("version: %s\n" % value)), [])

    def test_metadata_map_rules(self):
        self.assertEqual(issue_keywords(body_lines("metadata:\n    version: x\n")), ["bad_indent", "empty_map"])
        self.assertEqual(
            issue_keywords(body_lines("metadata:\n  nested:\n    a: b\n")), ["nested_map", "bad_indent", "empty_map"]
        )
        self.assertEqual(issue_keywords(body_lines("metadata:\n  a: x\n  a: y\n")), ["duplicate_key"])
        self.assertEqual(issue_keywords(body_lines("metadata:\nname: x\n")), ["empty_map"])
        self.assertEqual(issue_keywords(body_lines("name: x\n  family: roles\n")), ["bad_indent"])

    def test_yaml11_line_separators_are_rejected(self):
        for separator in ("\x85", "\u2028", "\u2029"):
            with self.subTest(separator=repr(separator)):
                self.assertEqual(issue_keywords(body_lines('d: "a%sb"\n' % separator)), ["control_character"])

    def test_issue_paths_name_source_and_line(self):
        result = fm.parse("\n---\nname: x\nname: y\n---\n", source="skills/x/SKILL.md")
        self.assertEqual(result.issues[0].path, "skills/x/SKILL.md:4")

    def test_never_raises_on_garbage(self):
        for text in ("---\n\x00\n---\n", "---\n" + ":" * 50 + "\n---\n", '---\n"\n---\n', "\ufeff"):
            fm.parse(text)


class TestLint(unittest.TestCase):
    def lint(self, text, folder_name=None):
        result = fm.parse(text)
        self.assertEqual(result.issues, [], "fixture must parse")
        return [issue.keyword for issue in fm.lint(result, folder_name=folder_name)]

    def test_unknown_and_missing_keys(self):
        text = GOOD.replace("license: Apache-2.0\n", "license: Apache-2.0\nallowed-tools: Bash\n")
        self.assertEqual(self.lint(text), ["unknown_key"])
        self.assertEqual(self.lint("---\nlicense: MIT\n---\n"), ["missing_key", "missing_key", "missing_key"])

    def test_name_rules(self):
        for name, keyword in (
            ("Review", "name_pattern"),
            ("a--b", "name_pattern"),
            ('"-a"', "name_pattern"),
            ("a" * 65, "name_pattern"),
            ("create-skill", "name_reserved"),
        ):
            with self.subTest(name=name):
                self.assertEqual(self.lint(GOOD.replace("name: review-verifier", "name: " + name)), [keyword])
        self.assertEqual(self.lint(GOOD, folder_name="other"), ["name_folder_mismatch"])
        self.assertEqual(
            self.lint(GOOD.replace("name: review-verifier", "name: " + "a" * 64), folder_name="a" * 64), []
        )

    def test_description_must_be_double_quoted_and_bounded(self):
        plain = GOOD.replace('description: "Independently', "description: Independently").replace(
            '\\"verdict\\"."', "verdict."
        )
        self.assertEqual(self.lint(plain), ["not_double_quoted"])
        self.assertEqual(
            self.lint(
                GOOD.replace(
                    GOOD_DESCRIPTION,
                    'description: "%s"' % ("x" * 1025),
                )
            ),
            ["too_long"],
        )
        self.assertEqual(
            self.lint(
                GOOD.replace(
                    GOOD_DESCRIPTION,
                    'description: "  "',
                )
            ),
            ["empty_value"],
        )

    def test_compatibility_rules(self):
        self.assertEqual(self.lint(GOOD.replace('compatibility: "Zed', 'compatibility: "' + "z" * 500)), ["too_long"])
        unquoted = GOOD.replace(
            'compatibility: "Zed Agent (Ollama local or cloud), Claude Code, Codex. Scripts need python3 >= 3.9."',
            "compatibility: Zed",
        )
        self.assertEqual(self.lint(unquoted), ["not_double_quoted"])

    def test_metadata_rules(self):
        self.assertEqual(self.lint(GOOD.replace("  family: roles\n", "  family: other\n")), ["bad_metadata_value"])
        self.assertEqual(self.lint(GOOD.replace('  version: "0.1.0"\n', '  version: "1.0"\n')), ["bad_metadata_value"])
        self.assertEqual(self.lint(GOOD.replace("  spec: SPEC-003\n", "  spec: SPEC-3\n")), ["bad_metadata_value"])
        self.assertEqual(self.lint(GOOD.replace("  author: Cazador0\n", '  author: " "\n')), ["bad_metadata_value"])
        self.assertEqual(self.lint(GOOD.replace("  author: Cazador0\n", "")), ["missing_metadata_key"])
        self.assertEqual(self.lint(GOOD.replace("  author: Cazador0\n", "  author: true\n")), ["not_string"])

    def test_disable_model_invocation(self):
        self.assertEqual(self.lint(GOOD.replace("license:", "disable-model-invocation: true\nlicense:")), [])
        self.assertEqual(
            self.lint(GOOD.replace("license:", 'disable-model-invocation: "true"\nlicense:')), ["not_boolean"]
        )

    def test_license_must_be_a_string(self):
        self.assertEqual(self.lint(GOOD.replace("license: Apache-2.0", "license: false")), ["not_string"])

    def test_lint_paths_point_at_lines(self):
        result = fm.parse(GOOD.replace("  family: roles\n", "  family: other\n"))
        self.assertEqual(
            fm.lint(result, source="skills/review-verifier/SKILL.md")[0].path, "skills/review-verifier/SKILL.md:8"
        )


if __name__ == "__main__":
    unittest.main()
