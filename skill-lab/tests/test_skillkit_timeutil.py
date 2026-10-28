"""Tests for _skillkit.timeutil: strict RFC 3339, relaxed --now parsing, canonical output."""

from __future__ import annotations

import datetime as dt
import unittest

from tests import skillkit_support  # noqa: F401
from _skillkit import timeutil

UTC = dt.timezone.utc


class TestIsRfc3339(unittest.TestCase):
    def test_rejects_non_strings(self):
        for value in (None, 20261022, dt.datetime(2026, 10, 22, tzinfo=UTC)):
            self.assertFalse(timeutil.is_rfc3339(value))

    def test_leap_years(self):
        self.assertTrue(timeutil.is_rfc3339("2000-02-29T00:00:00Z"))
        self.assertFalse(timeutil.is_rfc3339("1900-02-29T00:00:00Z"))
        self.assertTrue(timeutil.is_rfc3339("2024-02-29T00:00:00Z"))

    def test_leap_second_only_at_utc_end_of_day(self):
        self.assertTrue(timeutil.is_rfc3339("1998-12-31T23:59:60Z"))
        self.assertTrue(timeutil.is_rfc3339("1999-01-01T05:29:60+05:30"))
        self.assertFalse(timeutil.is_rfc3339("1998-12-31T23:59:60+01:00"))


class TestParse(unittest.TestCase):
    def test_parse_rfc3339_converts_to_utc(self):
        value = timeutil.parse_rfc3339("2026-10-22T10:30:00+02:30")
        self.assertEqual(value, dt.datetime(2026, 10, 22, 8, 0, 0, tzinfo=UTC))
        self.assertEqual(value.utcoffset(), dt.timedelta(0))

    def test_parse_rfc3339_fraction(self):
        value = timeutil.parse_rfc3339("2026-10-22T08:00:00.1234567Z")
        self.assertEqual(value.microsecond, 123456)

    def test_parse_rfc3339_rejects_naive_and_leap_seconds(self):
        for text in ("2026-10-22T08:00:00", "1998-12-31T23:59:60Z", "garbage"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                timeutil.parse_rfc3339(text)

    def test_parse_iso8601_relaxations(self):
        expected = dt.datetime(2026, 10, 22, 8, 0, tzinfo=UTC)
        for text in (
            "2026-10-22T08:00:00Z",
            "2026-10-22T08:00Z",
            "2026-10-22 08:00:00",
            "2026-10-22T08:00:00",
            "2026-10-22T09:00:00+0100",
            "  2026-10-22T08:00:00z  ",
        ):
            with self.subTest(text=text):
                self.assertEqual(timeutil.parse_iso8601(text), expected)
        self.assertEqual(timeutil.parse_iso8601("2026-10-22"), dt.datetime(2026, 10, 22, tzinfo=UTC))

    def test_parse_iso8601_rejects(self):
        for text in ("22/10/2026", "2026-10-32", "2026-10-22T25:00", "2026-10-22T08:00:00+99:00", "", "now"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                timeutil.parse_iso8601(text)
        with self.assertRaises(ValueError):
            timeutil.parse_iso8601(None)


class TestFormat(unittest.TestCase):
    def test_to_iso_is_canonical_utc_seconds(self):
        aware = dt.datetime(2026, 10, 22, 10, 0, 0, 999999, tzinfo=dt.timezone(dt.timedelta(hours=2)))
        self.assertEqual(timeutil.to_iso(aware), "2026-10-22T08:00:00Z")

    def test_to_iso_treats_naive_as_utc(self):
        self.assertEqual(timeutil.to_iso(dt.datetime(2026, 1, 2, 3, 4, 5)), "2026-01-02T03:04:05Z")

    def test_round_trip_is_valid_rfc3339(self):
        now = timeutil.utc_now()
        self.assertEqual(now.microsecond, 0)
        self.assertIsNotNone(now.tzinfo)
        self.assertTrue(timeutil.is_rfc3339(timeutil.to_iso(now)))


if __name__ == "__main__":
    unittest.main()
