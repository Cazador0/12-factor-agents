"""Tests for _skillkit.ids: canonical JSON, digests, idempotency keys."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import unittest

from tests import skillkit_support  # noqa: F401
from _skillkit import ids


class TestCanonicalJson(unittest.TestCase):
    def test_sorted_compact_utf8(self):
        self.assertEqual(ids.canonical_json({"b": 1, "a": [True, None, "é"]}), '{"a":[true,null,"é"],"b":1}')

    def test_key_order_does_not_matter(self):
        self.assertEqual(ids.canonical_json({"x": {"b": 2, "a": 1}}), ids.canonical_json({"x": {"a": 1, "b": 2}}))

    def test_nan_is_refused(self):
        with self.assertRaises(ValueError):
            ids.canonical_json(float("nan"))


class TestDigest(unittest.TestCase):
    def test_digest_format_and_value(self):
        value = ids.digest({"a": 1})
        self.assertRegex(value, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(value, "sha256:" + hashlib.sha256(b'{"a":1}').hexdigest())

    def test_digest_is_stable_across_key_order(self):
        self.assertEqual(ids.digest({"a": 1, "b": 2}), ids.digest({"b": 2, "a": 1}))
        self.assertNotEqual(ids.digest({"a": 1}), ids.digest({"a": 2}))

    def test_digest_bytes_and_file_agree(self):
        data = b"log line 1\nlog line 2\n" * 5000
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "log.txt")
            with open(path, "wb") as handle:
                handle.write(data)
            self.assertEqual(ids.digest_file(path, chunk_size=1024), ids.digest_bytes(data))
        self.assertEqual(ids.digest_bytes(b""), "sha256:" + hashlib.sha256(b"").hexdigest())


class TestIdempotencyKey(unittest.TestCase):
    def test_format(self):
        key = ids.idempotency_key("create_issue", "acme/factory", "T001")
        self.assertTrue(re.match(r"^idem-[0-9a-f]{32}$", key), key)

    def test_deterministic_and_sensitive_to_parts(self):
        first = ids.idempotency_key("create_issue", "acme/factory", "T001")
        self.assertEqual(first, ids.idempotency_key("create_issue", "acme/factory", "T001"))
        self.assertNotEqual(first, ids.idempotency_key("create_issue", "acme/factory", "T002"))
        self.assertNotEqual(
            ids.idempotency_key("ab", "c"), ids.idempotency_key("a", "bc"), "parts are not concatenated"
        )

    def test_matches_documented_derivation(self):
        expected = "idem-" + hashlib.sha256(b'["op",{"a":1},2]').hexdigest()[:32]
        self.assertEqual(ids.idempotency_key("op", {"a": 1}, 2), expected)


if __name__ == "__main__":
    unittest.main()
