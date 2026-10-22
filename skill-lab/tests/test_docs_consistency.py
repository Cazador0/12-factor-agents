"""Cross-document consistency: every lab doc's links resolve and its commands match the real CLI.

``test_configs.py`` checks the docs written alongside the runtime templates. This module applies
the same checks to every document in the lab (README files, CONVENTIONS, ADRs, architecture,
runbooks, specs 100-104), and also checks the shorthand ``skill-lab <command> ...`` that the prose
uses. Commands and flags that a release spec plans but the lab does not have yet are allowed only
while SPEC-201 still names them, so the allowance cannot outlive the plan.
"""

from __future__ import annotations

import glob
import os
import re
import unittest
from typing import Iterator, List, Tuple

from tests import test_configs as cfg

from lab import cli as labcli

REPO_ROOT = cfg.REPO_ROOT
LAB_ROOT = cfg.LAB_ROOT


def lab_docs() -> List[str]:
    """Every Markdown document of the lab, plus AGENTS.md and skills/README.md."""
    patterns = (
        "README.md",
        "benchmarks/README.md",
        "contracts/README.md",
        "config/*/README.md",
        "templates/skill/_README.md",
        "docs/CONVENTIONS.md",
        "docs/architecture.md",
        "docs/adr/*.md",
        "docs/runbooks/*.md",
        "specs/10[0-9]-*/spec.md",
    )
    found = [path for pattern in patterns for path in glob.glob(os.path.join(LAB_ROOT, *pattern.split("/")))]
    return sorted(set(found)) + [cfg.AGENTS_MD, cfg.SKILLS_README]


PLANNED_COMMANDS = ("policy", "release", "streak", "report")
"""``skill-lab`` subcommands that SPEC-201 adds in R1 (``streak`` and ``report`` come with SPEC-105, delivered in R1)."""

PLANNED_FLAGS = (("validate", "--config"), ("validate", "--specs"), ("validate", "--rule"), ("install", "--inference"))
"""Flags that SPEC-201 adds to existing commands in R1."""

_FENCE_RE = re.compile(r"^\s*```")
_SPAN_RE = re.compile(r"`([^`\n]+)`")
_MENTION_RE = re.compile(r"(?:^|[\s(])skill-lab(?:/bin/skill-lab)? ([a-z][a-z-]*)([^|;&>]*)")
_FLAG_RE = re.compile(r"(?<![\w-])(--[a-z][a-z0-9-]*)")


def spec201_text() -> str:
    folder = os.path.join(LAB_ROOT, "specs", "201-release-shadow")
    return "\n".join(cfg.read_text(path) for path in sorted(glob.glob(os.path.join(folder, "*.md"))))


def prose_mentions(path: str) -> Iterator[Tuple[int, str, List[str]]]:
    """``(line, command, flags)`` for each ``skill-lab <command> ...`` in an inline code span."""
    fenced = False
    for number, line in enumerate(cfg.read_text(path).splitlines(), 1):
        if _FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        for span in _SPAN_RE.findall(line):
            for match in _MENTION_RE.finditer(span):
                yield number, match.group(1), _FLAG_RE.findall(match.group(2))


class TestLabDocs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = lab_docs()
        cls.invocations = [
            (os.path.relpath(path, REPO_ROOT), tokens)
            for path in cls.docs + [cfg.WORKFLOW]
            for tokens in cfg.lab_invocations(cfg.read_text(path))
        ]

    def test_the_document_set_is_complete(self):
        names = {os.path.relpath(path, REPO_ROOT) for path in self.docs}
        for expected in (
            "skill-lab/docs/runbooks/setup-jev.md",
            "skill-lab/docs/architecture.md",
            "skill-lab/docs/adr/0001-two-folder-monorepo.md",
            "skill-lab/specs/104-scoring-gates/spec.md",
        ):
            self.assertIn(expected, names)

    def test_relative_links_resolve(self):
        for path in self.docs:
            for target in cfg.local_links(path):
                with self.subTest(doc=os.path.relpath(path, REPO_ROOT), link=target):
                    self.assertTrue(os.path.exists(os.path.join(os.path.dirname(path), target)))

    def test_full_invocations_use_real_commands_and_flags(self):
        self.assertGreater(len(self.invocations), 40)
        for doc, tokens in self.invocations:
            for command in tokens[0].split("|"):  # prose may write `skill-lab validate|bench|score ...`
                with self.subTest(doc=doc, command=" ".join([command] + tokens[1:])):
                    self.assertIn(command, labcli.COMMANDS)
                    help_text = cfg.lab_help(command)
                    for flag in cfg.flag_values(tokens):
                        self.assertTrue(cfg.mentions_flag(help_text, flag), "%s has no %s" % (command, flag))

    def test_full_invocations_pass_the_required_arguments(self):
        for doc, tokens in self.invocations:
            flags = cfg.flag_values(tokens)
            with self.subTest(doc=doc, command=" ".join(tokens)):
                if tokens[0] == "score":
                    self.assertIn("--skill", flags, "score needs --skill")
                if tokens[0] == "bench" and flags.get("--runtime") in ("ollama-cloud", "ollama-local", "replay"):
                    self.assertIn("--model", flags, "this runtime skips every case without --model")

    def test_prose_mentions_name_real_or_planned_commands_and_flags(self):
        checked = 0
        for path in self.docs:
            for number, command, flags in prose_mentions(path):
                checked += 1
                where = "%s:%d" % (os.path.relpath(path, REPO_ROOT), number)
                with self.subTest(where=where, command=command):
                    if command in PLANNED_COMMANDS:
                        continue
                    self.assertIn(command, labcli.COMMANDS)
                    help_text = cfg.lab_help(command)
                    for flag in flags:
                        if (command, flag) not in PLANNED_FLAGS:
                            self.assertTrue(cfg.mentions_flag(help_text, flag), "%s has no %s" % (command, flag))
        self.assertGreater(checked, 50)

    def test_planned_commands_and_flags_are_still_planned(self):
        plan = spec201_text()
        for command in PLANNED_COMMANDS:
            with self.subTest(command=command):
                self.assertNotIn(command, labcli.COMMANDS, "implemented: drop it from PLANNED_COMMANDS")
                self.assertIn("skill-lab %s" % command, plan)
        for command, flag in PLANNED_FLAGS:
            with self.subTest(command=command, flag=flag):
                self.assertFalse(cfg.mentions_flag(cfg.lab_help(command), flag), "implemented: drop it")
                self.assertIn("%s %s" % (command, flag), plan)


if __name__ == "__main__":
    unittest.main()
