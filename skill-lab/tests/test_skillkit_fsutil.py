"""Tests for _skillkit.fsutil: atomic writes, locks, and path containment."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from unittest import mock

from tests import skillkit_support  # noqa: F401
from _skillkit import EXIT_EXTERNAL, EXIT_REFUSED, fsutil
from _skillkit.envelope import ScriptError


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def leftovers(self, directory):
        return [name for name in os.listdir(directory) if name.endswith(".tmp")]


class TestAtomicWrite(TempDirTest):
    def test_writes_stable_json(self):
        path = os.path.join(self.root, "state", "lease.json")
        fsutil.atomic_write_json(path, {"b": 1, "a": "é"})
        with open(path, "r", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), '{\n  "a": "é",\n  "b": 1\n}\n')
        self.assertEqual(self.leftovers(os.path.dirname(path)), [])

    def test_replaces_existing_file(self):
        path = os.path.join(self.root, "x.json")
        fsutil.atomic_write_json(path, {"v": 1})
        fsutil.atomic_write_json(path, {"v": 2})
        self.assertEqual(skillkit_support.load_json(path), {"v": 2})

    def test_failed_replace_keeps_old_content_and_cleans_up(self):
        path = os.path.join(self.root, "x.json")
        fsutil.atomic_write_json(path, {"v": 1})
        with mock.patch.object(fsutil.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                fsutil.atomic_write_json(path, {"v": 2})
        self.assertEqual(skillkit_support.load_json(path), {"v": 1})
        self.assertEqual(self.leftovers(self.root), [])

    def test_unserialisable_data_writes_nothing(self):
        path = os.path.join(self.root, "x.json")
        with self.assertRaises(ValueError):
            fsutil.atomic_write_json(path, {"v": float("nan")})
        self.assertFalse(os.path.exists(path))

    def test_fsyncs_file_before_replace(self):
        path = os.path.join(self.root, "x.txt")
        calls = []
        real_fsync, real_replace = os.fsync, os.replace
        with (
            mock.patch.object(fsutil.os, "fsync", side_effect=lambda fd: (calls.append("fsync"), real_fsync(fd))),
            mock.patch.object(
                fsutil.os, "replace", side_effect=lambda a, b: (calls.append("replace"), real_replace(a, b))
            ),
        ):
            fsutil.atomic_write_text(path, "hello\n")
        self.assertEqual(calls[:2], ["fsync", "replace"])

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
    def test_mode_honours_umask(self):
        path = os.path.join(self.root, "x.txt")
        old = os.umask(0o027)
        try:
            fsutil.atomic_write_text(path, "x")
        finally:
            os.umask(old)
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o640)

    def test_concurrent_writers_never_tear_the_file(self):
        path = os.path.join(self.root, "x.json")
        payloads = [{"writer": n, "blob": "x" * 20000} for n in range(8)]
        threads = [threading.Thread(target=fsutil.atomic_write_json, args=(path, p)) for p in payloads]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertIn(skillkit_support.load_json(path), payloads)
        self.assertEqual(self.leftovers(self.root), [])


class TestFileLock(TempDirTest):
    def test_lock_and_release(self):
        lock_path = os.path.join(self.root, "locks", "issue-184.lock")
        with fsutil.file_lock(lock_path, timeout=1) as held:
            self.assertEqual(held, lock_path)
        with fsutil.file_lock(lock_path, timeout=1):
            pass

    def test_second_holder_times_out_with_lock_timeout(self):
        lock_path = os.path.join(self.root, "x.lock")
        with fsutil.file_lock(lock_path, timeout=1):
            started = time.monotonic()
            with self.assertRaises(ScriptError) as ctx:
                with fsutil.file_lock(lock_path, timeout=0.2, poll_interval=0.02):
                    self.fail("lock acquired twice")
            self.assertGreaterEqual(time.monotonic() - started, 0.15)
        self.assertEqual(ctx.exception.code, "LOCK_TIMEOUT")
        self.assertEqual(ctx.exception.exit_code, EXIT_EXTERNAL)
        self.assertEqual(ctx.exception.path, lock_path)

    def test_lock_is_released_when_the_block_raises(self):
        lock_path = os.path.join(self.root, "x.lock")
        with self.assertRaises(RuntimeError):
            with fsutil.file_lock(lock_path, timeout=1):
                raise RuntimeError("boom")
        with fsutil.file_lock(lock_path, timeout=0.2):
            pass

    def test_waiter_gets_the_lock_after_release(self):
        lock_path = os.path.join(self.root, "x.lock")
        order = []
        acquired = threading.Event()

        def holder():
            with fsutil.file_lock(lock_path, timeout=1):
                acquired.set()
                time.sleep(0.2)
                order.append("holder-done")

        thread = threading.Thread(target=holder)
        thread.start()
        acquired.wait(2)
        with fsutil.file_lock(lock_path, timeout=3, poll_interval=0.02):
            order.append("waiter")
        thread.join()
        self.assertEqual(order, ["holder-done", "waiter"])

    def test_exclusive_file_fallback(self):
        lock_path = os.path.join(self.root, "fallback.lock")
        with fsutil._exclusive_file_lock(lock_path, timeout=1, poll_interval=0.01):
            self.assertTrue(os.path.exists(lock_path))
            with self.assertRaises(ScriptError) as ctx:
                with fsutil._exclusive_file_lock(lock_path, timeout=0.05, poll_interval=0.01):
                    pass
            self.assertEqual(ctx.exception.code, "LOCK_TIMEOUT")
        self.assertFalse(os.path.exists(lock_path), "fallback lock file is removed on release")

    def test_without_fcntl_or_msvcrt_the_fallback_is_used(self):
        lock_path = os.path.join(self.root, "nofcntl.lock")
        with mock.patch.object(fsutil, "_fcntl", None), mock.patch.object(fsutil, "_msvcrt", None):
            with fsutil.file_lock(lock_path, timeout=1):
                self.assertTrue(os.path.exists(lock_path))
        self.assertFalse(os.path.exists(lock_path))


class TestSafeJoin(TempDirTest):
    def test_inside_root(self):
        self.assertEqual(fsutil.safe_join(self.root, "a", "b.json"), os.path.join(self.root, "a", "b.json"))
        self.assertEqual(fsutil.safe_join(self.root, "a/../b"), os.path.join(self.root, "b"))
        self.assertEqual(fsutil.safe_join(self.root), self.root)
        self.assertEqual(fsutil.safe_join(self.root, "."), self.root)

    def test_traversal_is_refused(self):
        for parts in (("..",), ("a", "..", ".."), ("../etc/passwd",), ("/etc/passwd",), ("a", "/abs")):
            with self.subTest(parts=parts), self.assertRaises(ScriptError) as ctx:
                fsutil.safe_join(self.root, *parts)
            self.assertEqual(ctx.exception.code, "PATH_TRAVERSAL")
            self.assertEqual(ctx.exception.exit_code, EXIT_REFUSED)

    def test_sibling_with_common_prefix_is_outside(self):
        sibling = self.root + "-evil"
        with self.assertRaises(ScriptError):
            fsutil.safe_join(self.root, "..", os.path.basename(sibling))

    def test_nul_byte_and_non_string_are_refused(self):
        for part in ("a\x00b", 5):
            with self.subTest(part=part), self.assertRaises(ScriptError):
                fsutil.safe_join(self.root, part)

    @unittest.skipUnless(hasattr(os, "symlink"), "needs symlinks")
    def test_symlink_escape_is_refused(self):
        outside = tempfile.mkdtemp()
        try:
            os.symlink(outside, os.path.join(self.root, "link"))
            with self.assertRaises(ScriptError):
                fsutil.safe_join(self.root, "link", "x.json")
        finally:
            os.rmdir(outside)


class TestEnsureNotInside(TempDirTest):
    def test_refuses_paths_inside_and_the_root_itself(self):
        skill = os.path.join(self.root, "skills", "review-verifier")
        os.makedirs(skill)
        for target in (skill, os.path.join(skill, "out.json"), os.path.join(skill, "a", "..", "b.json")):
            with self.subTest(target=target), self.assertRaises(ScriptError) as ctx:
                fsutil.ensure_not_inside(target, skill)
            self.assertEqual(ctx.exception.code, "PATH_FORBIDDEN")
            self.assertEqual(ctx.exception.exit_code, EXIT_REFUSED)

    def test_allows_paths_outside(self):
        skill = os.path.join(self.root, "skills", "review-verifier")
        os.makedirs(skill)
        out = os.path.join(self.root, ".skill-state", "x.json")
        self.assertEqual(fsutil.ensure_not_inside(out, skill), out)
        self.assertEqual(fsutil.ensure_not_inside(skill + "-other/x", skill), skill + "-other/x")

    def test_is_within(self):
        self.assertTrue(fsutil.is_within(os.path.join(self.root, "a"), self.root))
        self.assertTrue(fsutil.is_within(self.root, self.root))
        self.assertFalse(fsutil.is_within(os.path.dirname(self.root), self.root))


class TestJsonRoundTrip(TempDirTest):
    def test_atomic_json_is_readable_by_json_module(self):
        path = os.path.join(self.root, "x.json")
        doc = {"tasks": {"T001": {"gitea_issue": 184}}, "unicode": "ü"}
        fsutil.atomic_write_json(path, doc)
        with open(path, "rb") as handle:
            self.assertEqual(json.loads(handle.read().decode("utf-8")), doc)


if __name__ == "__main__":
    unittest.main()
