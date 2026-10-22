"""Tests for _skillkit.redact: nothing secret reaches stdout, stderr or state files."""

from __future__ import annotations

import copy
import unittest

from tests import skillkit_support
from _skillkit import redact as rd

GITEA = "gt_0123456789abcdef"
JEV = "jev-key-ABCDEFGHIJ"


class TestEnvironmentSecrets(unittest.TestCase):
    def test_masks_values_of_every_listed_variable(self):
        values = {name: "secret-value-for-%s" % name.lower() for name in rd.SECRET_ENV_VARS}
        with skillkit_support.env(**values):
            for name, value in values.items():
                with self.subTest(name=name):
                    self.assertEqual(rd.redact("prefix %s suffix" % value), "prefix *** suffix")

    def test_lists_the_documented_variables(self):
        self.assertEqual(
            set(rd.SECRET_ENV_VARS),
            {
                "GITEA_TOKEN",
                "GITEA_WEBHOOK_SECRET",
                "TYPESAFE_API_KEY",
                "JEV_API_KEY",
                "OLLAMA_API_KEY",
                "GITHUB_TOKEN",
                "GH_TOKEN",
                "ANTHROPIC_API_KEY",
                "OPENAI_API_KEY",
            },
        )

    def test_short_values_are_not_masked(self):
        with skillkit_support.env(GITEA_TOKEN="abc"):
            self.assertEqual(rd.redact("abc def"), "abc def")

    def test_unset_variables_do_nothing(self):
        with skillkit_support.env(GITEA_TOKEN=None, TYPESAFE_API_KEY=None):
            self.assertEqual(rd.redact("plain text"), "plain text")

    def test_nested_structures_and_keys(self):
        with skillkit_support.env(GITEA_TOKEN=GITEA, JEV_API_KEY=JEV):
            doc = {"errors": [{"message": "401 with %s" % GITEA}], GITEA: [JEV, ("t", JEV)], "n": 5}
            self.assertEqual(
                rd.redact(doc), {"errors": [{"message": "401 with ***"}], "***": ["***", ["t", "***"]], "n": 5}
            )


class TestPatterns(unittest.TestCase):
    def test_bearer_tokens(self):
        self.assertEqual(rd.redact("Authorization: Bearer abc.def-ghi_jkl=="), "Authorization: Bearer ***")
        self.assertEqual(rd.redact("got bearer XYZ123 back"), "got bearer *** back")

    def test_authorization_header_schemes(self):
        self.assertEqual(rd.redact("Authorization: token 0123456789abcdef"), "Authorization: token ***")
        self.assertEqual(rd.redact("authorization=Basic dXNlcjpwYXNz"), "authorization=Basic ***")
        self.assertEqual(rd.redact("Authorization: opaque-cred"), "Authorization: ***")

    def test_url_credentials(self):
        self.assertEqual(
            rd.redact("clone https://bot:hunter2@gitea.local/acme/x.git"), "clone https://***@gitea.local/acme/x.git"
        )
        self.assertEqual(rd.redact("https://ghp_tok@github.com/x"), "https://***@github.com/x")
        self.assertEqual(rd.redact("https://gitea.local/user@example"), "https://gitea.local/user@example")

    def test_known_token_formats(self):
        for token in ("ghp_" + "a" * 36, "github_pat_" + "B" * 30, "sk-ant-" + "c" * 30, "sk-" + "d" * 40):
            with self.subTest(token=token[:12]):
                self.assertEqual(rd.redact("key=%s end" % token), "key=*** end")

    def test_ordinary_text_is_untouched(self):
        text = "The token budget is 32k; authorization rules live in policy.md; see https://ollama.com/api"
        self.assertEqual(rd.redact(text), text)


class TestSensitiveKeys(unittest.TestCase):
    def test_sensitive_key_names(self):
        for key in (
            "token",
            "access_token",
            "GITEA_TOKEN",
            "api_key",
            "apiKey",
            "x-api-key",
            "Authorization",
            "password",
            "client_secret",
            "secret",
            "private_key",
            "auth",
            "x-auth-token",
            "cookie",
            "credentials",
        ):
            with self.subTest(key=key):
                self.assertTrue(rd.is_sensitive_key(key))

    def test_non_sensitive_key_names(self):
        for key in (
            "input_tokens",
            "output_tokens",
            "max_tokens",
            "idempotency_key",
            "author",
            "key",
            "keys",
            "signature_verified",
            "session_id",
            "tokens",
            "secrets_count",
        ):
            with self.subTest(key=key):
                self.assertFalse(rd.is_sensitive_key(key))

    def test_values_under_sensitive_keys(self):
        doc = {
            "token": "abc",
            "api_key": {"nested": "x"},
            "password": ["a"],
            "secret": "",
            "auth": None,
            "token_present": True,
            "usage": {"input_tokens": 120, "output_tokens": 12},
            "token_count": 4,
        }
        self.assertEqual(
            rd.redact(doc),
            {
                "token": "***",
                "api_key": "***",
                "password": "***",
                "secret": "",
                "auth": None,
                "token_present": True,
                "usage": {"input_tokens": 120, "output_tokens": 12},
                "token_count": 4,
            },
        )


class TestPurity(unittest.TestCase):
    def test_input_is_not_modified(self):
        doc = {"token": "abc", "items": [{"password": "p"}], "t": ("Bearer x",)}
        before = copy.deepcopy(doc)
        result = rd.redact(doc)
        self.assertEqual(doc, before)
        self.assertIsNot(result, doc)
        self.assertEqual(result["t"], ["Bearer ***"], "tuples become lists, like JSON arrays")

    def test_non_json_scalars_pass_through(self):
        for value in (None, True, 3, 2.5):
            self.assertEqual(rd.redact(value), value)

    def test_redact_text(self):
        with skillkit_support.env(OLLAMA_API_KEY="ollama-secret-123"):
            self.assertEqual(rd.redact_text("calling with ollama-secret-123"), "calling with ***")


if __name__ == "__main__":
    unittest.main()
