"""Crash-safe writes, inter-process locks, and path containment checks.

- ``atomic_write_json`` / ``atomic_write_text``: write a temporary file in the
  destination directory, fsync it, then ``os.replace`` it over the target, so
  readers see either the old or the new content, never a torn file.
- ``file_lock``: an exclusive lock held for a ``with`` block. It uses
  ``fcntl.flock`` on POSIX and ``msvcrt.locking`` on Windows, and otherwise
  falls back to an ``O_EXCL`` lock file. A timeout raises ``LOCK_TIMEOUT``
  (exit 3).
- ``safe_join``: join untrusted path parts under a root and refuse anything
  that escapes it, symlinks included (``PATH_TRAVERSAL``, exit 4).
- ``ensure_not_inside``: refuse writes inside a forbidden tree, such as the
  skill's own folder (``PATH_FORBIDDEN``, exit 4).
"""

from __future__ import annotations

import contextlib
import itertools
import json
import os
import time
from typing import Callable, Iterator, Tuple

from . import EXIT_EXTERNAL, EXIT_REFUSED
from .envelope import ScriptError

try:  # POSIX
    import fcntl as _fcntl
except ImportError:  # not POSIX
    _fcntl = None

try:  # Windows
    import msvcrt as _msvcrt
except ImportError:
    _msvcrt = None

_TMP_COUNTER = itertools.count()


def atomic_write_text(path: str, text: str) -> None:
    """Atomically replace ``path`` with ``text`` (UTF-8), creating parent dirs."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    tmp_path, fd = _create_temp(directory, os.path.basename(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
    _fsync_directory(directory)


def atomic_write_json(path: str, obj: object) -> None:
    """Atomically write ``obj`` as stable JSON: sorted keys, 2-space indent, final newline."""
    text = json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    atomic_write_text(path, text)


def _create_temp(directory: str, base: str) -> Tuple[str, int]:
    """Create a unique temp file beside the target; mode honours the umask."""
    while True:
        candidate = os.path.join(directory, ".%s.%d.%d.tmp" % (base, os.getpid(), next(_TMP_COUNTER)))
        try:
            return candidate, os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        except FileExistsError:
            continue


def _fsync_directory(directory: str) -> None:
    """Persist the rename itself; a no-op where directories cannot be opened."""
    flags = getattr(os, "O_DIRECTORY", None)
    if flags is None:
        return
    try:
        fd = os.open(directory, os.O_RDONLY | flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


@contextlib.contextmanager
def file_lock(path: str, timeout: float = 10.0, poll_interval: float = 0.05) -> Iterator[str]:
    """Hold an exclusive lock on the lock file ``path`` for the ``with`` block.

    Raises ``ScriptError(LOCK_TIMEOUT)`` with exit code 3 when the lock is not
    acquired within ``timeout`` seconds. With ``flock`` and ``msvcrt`` the lock
    file is left in place (deleting it would race with waiting processes); the
    ``O_EXCL`` fallback removes it on release.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if _fcntl is not None or _msvcrt is not None:
        with _descriptor_lock(path, timeout, poll_interval):
            yield path
    else:  # neither fcntl nor msvcrt is available
        with _exclusive_file_lock(path, timeout, poll_interval):
            yield path


@contextlib.contextmanager
def _descriptor_lock(path: str, timeout: float, poll_interval: float) -> Iterator[None]:
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
    try:
        _wait_for(lambda: _try_lock(fd), path, timeout, poll_interval)
        try:
            yield
        finally:
            _unlock(fd)
    finally:
        os.close(fd)


@contextlib.contextmanager
def _exclusive_file_lock(path: str, timeout: float, poll_interval: float) -> Iterator[None]:
    def attempt() -> bool:
        try:
            os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666))
        except FileExistsError:
            return False
        return True

    _wait_for(attempt, path, timeout, poll_interval)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            os.unlink(path)


def _try_lock(fd: int) -> bool:
    try:
        if _fcntl is not None:
            _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        else:  # Windows
            os.lseek(fd, 0, os.SEEK_SET)
            _msvcrt.locking(fd, _msvcrt.LK_NBLCK, 1)
    except OSError:
        return False
    return True


def _unlock(fd: int) -> None:
    if _fcntl is not None:
        _fcntl.flock(fd, _fcntl.LOCK_UN)
    else:  # Windows
        os.lseek(fd, 0, os.SEEK_SET)
        _msvcrt.locking(fd, _msvcrt.LK_UNLCK, 1)


def _wait_for(attempt: Callable[[], bool], path: str, timeout: float, poll_interval: float) -> None:
    deadline = time.monotonic() + max(0.0, timeout)
    while not attempt():
        if time.monotonic() >= deadline:
            raise ScriptError(
                "LOCK_TIMEOUT",
                "could not acquire lock within %.1fs" % timeout,
                path=path,
                exit_code=EXIT_EXTERNAL,
            )
        time.sleep(poll_interval)


def safe_join(root: str, *parts: str) -> str:
    """Join ``parts`` under ``root`` and return the resolved absolute path.

    Raises ``ScriptError(PATH_TRAVERSAL)`` (exit 4) when the result, after
    resolving ``..`` and symlinks, is not ``root`` or inside it. Absolute parts
    and NUL bytes are refused the same way.
    """
    for part in parts:
        if not isinstance(part, str) or "\x00" in part:
            raise ScriptError("PATH_TRAVERSAL", "path part is not a valid string", exit_code=EXIT_REFUSED)
    real_root = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(real_root, *parts))
    if not _is_within(candidate, real_root):
        raise ScriptError(
            "PATH_TRAVERSAL",
            "path escapes its allowed root",
            path="/".join(parts),
            exit_code=EXIT_REFUSED,
        )
    return candidate


def ensure_not_inside(path: str, forbidden_root: str) -> str:
    """Refuse ``path`` when it is ``forbidden_root`` or inside it; return its real path.

    Use it before every write so a script never writes into its own skill
    folder: ``ensure_not_inside(out_path, schemas.skill_root())``.
    """
    real_path = os.path.realpath(path)
    if _is_within(real_path, os.path.realpath(forbidden_root)):
        raise ScriptError(
            "PATH_FORBIDDEN",
            "refusing to write inside a protected folder",
            path=path,
            exit_code=EXIT_REFUSED,
        )
    return real_path


def is_within(path: str, root: str) -> bool:
    """True when ``path`` resolves to ``root`` or somewhere beneath it."""
    return _is_within(os.path.realpath(path), os.path.realpath(root))


def _is_within(real_path: str, real_root: str) -> bool:
    path_norm, root_norm = os.path.normcase(real_path), os.path.normcase(real_root)
    try:
        return os.path.commonpath([path_norm, root_norm]) == root_norm
    except ValueError:  # different drives on Windows
        return False
