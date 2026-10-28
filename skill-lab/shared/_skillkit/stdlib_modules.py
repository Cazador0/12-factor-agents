"""Is a module part of the Python standard library?

``is_stdlib`` uses ``sys.stdlib_module_names`` (Python 3.10+) and otherwise an
embedded list of every top-level standard-library module of Python 3.9, built
the same way CPython builds that attribute: all platforms, pure-Python,
built-in, frozen and extension modules, excluding the ``test`` suite and
``__main__``.

Provenance of ``PY39_STDLIB_MODULES``: Python 3.11's ``sys.stdlib_module_names``
minus modules added in 3.10/3.11 (``tomllib``, ``_tokenize``, ``_typing``) plus
modules removed by 3.11 (``_bootlocale``, ``_peg_parser``, ``binhex``,
``formatter``, ``parser``, ``symbol``), cross-checked against the
``stdlib-list`` 0.11.1 inventory for 3.9.

``is_portable_stdlib`` is the stricter check the skill contract needs
("Python >= 3.9, stdlib only"): the module must exist in 3.9 *and* in the
running interpreter, so ``tomllib`` (3.11+) and ``distutils`` (gone in 3.12)
are both rejected on a modern Python.

``POST_PY39_STDLIB_MODULES`` lists the top-level modules Python 3.10-3.14
added, measured as ``sys.stdlib_module_names`` of CPython 3.10.20, 3.11,
3.12, 3.13 and 3.14.6 minus ``PY39_STDLIB_MODULES``. With it,
``is_known_stdlib`` gives the same answer on every interpreter, so a
validator running on 3.9 still recognises ``tomllib`` as standard library
(just not portable) instead of mistaking it for a third-party package.
"""

from __future__ import annotations

import sys

# fmt: off
PY39_STDLIB_MODULES = frozenset(
    {
        "__future__", "_abc", "_aix_support", "_ast", "_asyncio", "_bisect", "_blake2",
        "_bootlocale", "_bootsubprocess", "_bz2", "_codecs", "_codecs_cn", "_codecs_hk",
        "_codecs_iso2022", "_codecs_jp", "_codecs_kr", "_codecs_tw", "_collections",
        "_collections_abc", "_compat_pickle", "_compression", "_contextvars", "_crypt", "_csv",
        "_ctypes", "_curses", "_curses_panel", "_datetime", "_dbm", "_decimal", "_elementtree",
        "_frozen_importlib", "_frozen_importlib_external", "_functools", "_gdbm", "_hashlib",
        "_heapq", "_imp", "_io", "_json", "_locale", "_lsprof", "_lzma", "_markupbase", "_md5",
        "_msi", "_multibytecodec", "_multiprocessing", "_opcode", "_operator", "_osx_support",
        "_overlapped", "_peg_parser", "_pickle", "_posixshmem", "_posixsubprocess", "_py_abc",
        "_pydecimal", "_pyio", "_queue", "_random", "_scproxy", "_sha1", "_sha256", "_sha3",
        "_sha512", "_signal", "_sitebuiltins", "_socket", "_sqlite3", "_sre", "_ssl", "_stat",
        "_statistics", "_string", "_strptime", "_struct", "_symtable", "_thread",
        "_threading_local", "_tkinter", "_tracemalloc", "_uuid", "_warnings", "_weakref",
        "_weakrefset", "_winapi", "_zoneinfo", "abc", "aifc", "antigravity", "argparse",
        "array", "ast", "asynchat", "asyncio", "asyncore", "atexit", "audioop", "base64", "bdb",
        "binascii", "binhex", "bisect", "builtins", "bz2", "cProfile", "calendar", "cgi",
        "cgitb", "chunk", "cmath", "cmd", "code", "codecs", "codeop", "collections", "colorsys",
        "compileall", "concurrent", "configparser", "contextlib", "contextvars", "copy",
        "copyreg", "crypt", "csv", "ctypes", "curses", "dataclasses", "datetime", "dbm",
        "decimal", "difflib", "dis", "distutils", "doctest", "email", "encodings", "ensurepip",
        "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
        "formatter", "fractions", "ftplib", "functools", "gc", "genericpath", "getopt",
        "getpass", "gettext", "glob", "graphlib", "grp", "gzip", "hashlib", "heapq", "hmac",
        "html", "http", "idlelib", "imaplib", "imghdr", "imp", "importlib", "inspect", "io",
        "ipaddress", "itertools", "json", "keyword", "lib2to3", "linecache", "locale",
        "logging", "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
        "modulefinder", "msilib", "msvcrt", "multiprocessing", "netrc", "nis", "nntplib", "nt",
        "ntpath", "nturl2path", "numbers", "opcode", "operator", "optparse", "os",
        "ossaudiodev", "parser", "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil",
        "platform", "plistlib", "poplib", "posix", "posixpath", "pprint", "profile", "pstats",
        "pty", "pwd", "py_compile", "pyclbr", "pydoc", "pydoc_data", "pyexpat", "queue",
        "quopri", "random", "re", "readline", "reprlib", "resource", "rlcompleter", "runpy",
        "sched", "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal",
        "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd", "sqlite3",
        "sre_compile", "sre_constants", "sre_parse", "ssl", "stat", "statistics", "string",
        "stringprep", "struct", "subprocess", "sunau", "symbol", "symtable", "sys", "sysconfig",
        "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "textwrap", "this",
        "threading", "time", "timeit", "tkinter", "token", "tokenize", "trace", "traceback",
        "tracemalloc", "tty", "turtle", "turtledemo", "types", "typing", "unicodedata",
        "unittest", "urllib", "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
        "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile",
        "zipimport", "zlib", "zoneinfo"
    }
)

POST_PY39_STDLIB_MODULES = frozenset(
    {
        # 3.11
        "_tokenize", "_typing", "tomllib",
        # 3.12
        "_pydatetime", "_pylong", "_sha2",
        # 3.13
        "_android_support", "_apple_support", "_colorize", "_interpchannels", "_interpqueues",
        "_interpreters", "_ios_support", "_opcode_metadata", "_pyrepl", "_suggestions", "_sysconfig",
        "_wmi",
        # 3.14
        "_ast_unparse", "_hmac", "_py_warnings", "_remote_debugging", "_types", "_zstd",
        "annotationlib", "compression",
    }
)
# fmt: on


def top_level(module_name: str) -> str:
    """Return the top-level package of a dotted name (``os.path`` -> ``os``)."""
    return module_name.split(".", 1)[0]


def current_stdlib_modules() -> frozenset:
    """Top-level stdlib names for the running interpreter."""
    names = getattr(sys, "stdlib_module_names", None)
    if names is None:
        names = PY39_STDLIB_MODULES
    return frozenset(names) | frozenset(sys.builtin_module_names)


def is_stdlib(module_name: str) -> bool:
    """True when ``module_name`` (dotted or not) is in the running stdlib."""
    if not module_name or module_name.startswith("."):
        return False
    return top_level(module_name) in current_stdlib_modules()


def is_portable_stdlib(module_name: str) -> bool:
    """True when the module is stdlib on Python 3.9 and on the running Python."""
    return is_stdlib(module_name) and top_level(module_name) in PY39_STDLIB_MODULES


def is_known_stdlib(module_name: str) -> bool:
    """True when ``module_name`` is standard library in Python 3.9, any later release listed, or this one."""
    if not module_name or module_name.startswith("."):
        return False
    top = top_level(module_name)
    return top in PY39_STDLIB_MODULES or top in POST_PY39_STDLIB_MODULES or is_stdlib(module_name)
