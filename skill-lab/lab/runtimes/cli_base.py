"""Shared plumbing for agent CLIs used as single-turn runtimes (``claude``, ``codex``).

The CLI runs in a fresh empty temporary directory so it cannot read or edit
the repository, with the prompt on stdin (no shell, list arguments only).
Authentication is the CLI's own business (its environment and config are
inherited); ``available()`` only checks that the executable is on ``PATH``,
because checking credentials would spend tokens.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Callable, Dict, List, Mapping, Optional, Tuple

from _skillkit.envelope import compact
from _skillkit.redact import redact_text

from . import LIVE_PREREQ_MISSING, Runtime, RuntimeCallError, RuntimeResult

Runner = Callable[[List[str], str, float, Dict[str, str], str], Tuple[int, str, str]]
"""``(argv, stdin_text, timeout, env, cwd) -> (exit_code, stdout, stderr)``."""


def run_subprocess(
    argv: List[str], stdin_text: str, timeout: float, env: Dict[str, str], cwd: str
) -> Tuple[int, str, str]:
    """Run ``argv`` without a shell; map timeouts and launch failures to ``RuntimeCallError``."""
    try:
        completed = subprocess.run(
            argv,
            input=stdin_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            cwd=cwd,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeCallError("RUNTIME_TIMEOUT", "%s did not finish within %.0fs" % (argv[0], timeout)) from None
    except OSError as exc:
        raise RuntimeCallError("RUNTIME_UNREACHABLE", "cannot start %s: %s" % (argv[0], exc)) from None
    return completed.returncode, completed.stdout, completed.stderr


class CliAgentRuntime(Runtime):
    """Base class: subclasses set ``name``/``executable`` and build argv, stdin and the parse."""

    executable = ""

    def __init__(
        self, model: Optional[str], *, environ: Optional[Mapping[str, str]] = None, runner: Optional[Runner] = None
    ) -> None:
        self.model = model
        self._environ = dict(os.environ if environ is None else environ)
        self._runner = runner or run_subprocess

    def resolve(self) -> Optional[str]:
        """Absolute path of the executable on this runtime's ``PATH``, or None."""
        return shutil.which(self.executable, path=self._environ.get("PATH", os.defpath))

    def available(self) -> Tuple[bool, str]:
        if self.resolve() is None:
            return False, "%s: `%s` is not on PATH" % (LIVE_PREREQ_MISSING, self.executable)
        return True, "ok"

    def run(
        self, system_prompt: str, user_prompt: str, output_schema: Optional[dict], *, timeout: float
    ) -> RuntimeResult:
        executable = self.resolve()
        if executable is None:
            raise RuntimeCallError("RUNTIME_UNREACHABLE", "`%s` is not on PATH" % self.executable)
        argv, stdin_text = self.command(executable, system_prompt, user_prompt, output_schema)
        with tempfile.TemporaryDirectory(prefix="skill-lab-%s-" % self.name) as workdir:
            code, stdout, stderr = self._runner(argv, stdin_text, timeout, self._environ, workdir)
        if code != 0:
            tail = compact(redact_text(stderr.strip() or stdout.strip() or "no output"), 200)
            raise RuntimeCallError("RUNTIME_FAILED", "%s exited %d: %s" % (self.executable, code, tail))
        return self.parse(stdout)

    def command(
        self, executable: str, system_prompt: str, user_prompt: str, output_schema: Optional[dict]
    ) -> Tuple[List[str], str]:
        """``(argv, stdin_text)`` for one turn."""
        raise NotImplementedError

    def parse(self, stdout: str) -> RuntimeResult:
        """Turn the CLI's stdout into a ``RuntimeResult``; raise ``RuntimeCallError`` when unusable."""
        raise NotImplementedError
