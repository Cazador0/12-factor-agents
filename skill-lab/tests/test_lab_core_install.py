"""skill-lab install (SPEC-101 FR-015..FR-017): symlinks, copies, refusal, dry run, parity check."""

from __future__ import annotations

import json
import os
import shutil
import unittest

from tests import test_lab_core_fixtures as fx

from lab import install, paths

SKILL = "demo-skill"


class InstallTestCase(unittest.TestCase):
    def setUp(self):
        self.repo = fx.Repo.for_test(self)
        self.repo.add_skill(SKILL)
        self.agents = self.repo.path(".agents", "skills", SKILL)
        self.claude = self.repo.path(".claude", "skills", SKILL)

    def install(self, *args):
        code, envelope = fx.run(install.main, ["--repo", self.repo.root] + list(args))
        fx.assert_envelope(self, envelope, code, install.PAYLOAD_SCHEMA)
        return code, envelope

    def entries(self, envelope):
        return [(e["path"], e["state"], e["action"]) for e in envelope["payload"]["entries"]]


class TestProjectSymlinks(InstallTestCase):
    def test_default_creates_relative_symlinks_for_all_runtimes(self):
        code, envelope = self.install()
        self.assertEqual(code, 0)
        for dest in (self.agents, self.claude):
            self.assertTrue(os.path.islink(dest))
            self.assertEqual(os.readlink(dest), os.path.join("..", "..", "skills", SKILL))
            self.assertEqual(os.path.realpath(dest), os.path.realpath(self.repo.skill(SKILL)))
        self.assertEqual(
            self.entries(envelope),
            [(".agents/skills/demo-skill", "missing", "create"), (".claude/skills/demo-skill", "missing", "create")],
        )
        self.assertEqual(envelope["payload"]["entries"][0]["runtimes"], ["codex", "zed"])

    def test_second_run_changes_nothing(self):
        self.install()
        code, envelope = self.install()
        self.assertEqual(code, 0)
        self.assertEqual(envelope["payload"]["summary"]["none"], 2)

    def test_runtime_selection(self):
        self.install("--runtime", "claude")
        self.assertTrue(os.path.islink(self.claude))
        self.assertFalse(os.path.lexists(self.agents))
        self.install("--runtime", "zed")
        self.assertTrue(os.path.islink(self.agents))
        code, envelope = self.install("--runtime", "vscode")
        self.assertEqual((code, envelope["errors"][0]["code"]), (2, "USAGE"))

    def test_dry_run_writes_nothing(self):
        code, envelope = self.install("--dry-run")
        self.assertEqual(code, 0)
        self.assertTrue(envelope["payload"]["dry_run"])
        self.assertEqual(envelope["payload"]["summary"]["create"], 2)
        self.assertFalse(os.path.lexists(self.repo.path(".agents")))

    def test_project_option_installs_into_another_project(self):
        project = self.repo.path("elsewhere")
        os.makedirs(project)
        code, envelope = self.install("--project", project)
        self.assertEqual(code, 0)
        dest = os.path.join(project, ".agents", "skills", SKILL)
        self.assertEqual(os.path.realpath(dest), os.path.realpath(self.repo.skill(SKILL)))
        self.assertFalse(os.path.isabs(os.readlink(dest)))
        code, envelope = self.install("--project", self.repo.path("missing"))
        self.assertEqual((code, envelope["errors"][0]["code"]), (2, "PROJECT_NOT_FOUND"))


class TestCopies(InstallTestCase):
    def test_copy_mode_writes_a_marked_identical_copy(self):
        code, _envelope = self.install("--mode", "copy")
        self.assertEqual(code, 0)
        self.assertFalse(os.path.islink(self.agents))
        with open(os.path.join(self.agents, paths.MANAGED_MARKER), encoding="utf-8") as handle:
            marker = json.load(handle)
        self.assertEqual(marker, {"managed_by": "skill-lab", "skill": SKILL, "source": "skills/demo-skill"})
        self.assertFalse(paths.compare_trees(self.repo.skill(SKILL), self.agents, exclude_top=(paths.MANAGED_MARKER,)))
        self.assertEqual(
            install.classify(paths.Layout.at(self.repo.root), self.agents, self.repo.skill(SKILL)), install.COPIED
        )

    def test_stale_copy_is_refreshed(self):
        self.install("--mode", "copy")
        self.repo.write("skills/%s/references/guide.md" % SKILL, "# Changed\n")
        code, envelope = self.install("--check")
        self.assertEqual(code, 1)
        self.assertEqual({e["state"] for e in envelope["payload"]["entries"]}, {"stale"})
        self.assertEqual(self.install("--mode", "copy")[0], 0)
        self.assertEqual(self.install("--check")[0], 0)

    def test_switching_modes_replaces_managed_entries(self):
        self.install("--mode", "copy")
        code, envelope = self.install()
        self.assertEqual(code, 0)
        self.assertEqual({e["action"] for e in envelope["payload"]["entries"]}, {"replace"})
        self.assertTrue(os.path.islink(self.agents))


class TestRefusal(InstallTestCase):
    def test_unmanaged_path_is_refused_without_changes(self):
        os.makedirs(self.agents)
        self.repo.write(".agents/skills/%s/SKILL.md" % SKILL, "hand-made")
        code, envelope = self.install()
        self.assertEqual(code, 4)
        self.assertEqual(envelope["errors"][0]["code"], "INSTALL_CONFLICT")
        self.assertIn(("/".join([".agents", "skills", SKILL]), "foreign", "refuse"), self.entries(envelope))
        self.assertEqual(self.repo.read(".agents/skills/%s/SKILL.md" % SKILL), "hand-made")
        self.assertFalse(os.path.lexists(self.claude), "nothing is installed when any entry is refused")

    def test_dry_run_also_reports_the_refusal(self):
        os.makedirs(self.agents)
        self.assertEqual(self.install("--dry-run")[0], 4)

    def test_foreign_symlink_is_refused(self):
        os.makedirs(self.repo.path("other"))
        os.makedirs(os.path.dirname(self.agents))
        os.symlink(self.repo.path("other"), self.agents)
        self.assertEqual(self.install()[0], 4)
        self.assertEqual(os.path.realpath(self.agents), self.repo.path("other"))

    def test_force_replaces_the_unmanaged_path(self):
        os.makedirs(self.agents)
        code, envelope = self.install("--force")
        self.assertEqual(code, 0)
        self.assertTrue(os.path.islink(self.agents))
        self.assertTrue(envelope["payload"]["force"])


class TestParityAndPruning(InstallTestCase):
    def test_check_reports_missing_entries(self):
        code, envelope = self.install("--check")
        self.assertEqual(code, 1)
        self.assertEqual(envelope["errors"][0]["code"], "INSTALL_DRIFT")
        self.assertFalse(os.path.lexists(self.repo.path(".agents")))
        self.install()
        self.assertEqual(self.install("--check")[0], 0)

    def test_dangling_managed_symlink_is_stale(self):
        os.makedirs(os.path.dirname(self.agents))
        os.symlink(os.path.join("..", "..", "skills", "renamed"), self.agents)
        layout = paths.Layout.at(self.repo.root)
        self.assertEqual(install.classify(layout, self.agents, self.repo.skill(SKILL)), install.STALE)
        self.assertEqual(self.install()[0], 0)
        self.assertEqual(os.path.realpath(self.agents), os.path.realpath(self.repo.skill(SKILL)))

    def test_orphaned_managed_entries_are_removed(self):
        self.repo.add_skill("old-skill")
        self.install()
        foreign = self.repo.path(".agents", "skills", "someone-elses")
        os.makedirs(foreign)
        shutil.rmtree(self.repo.skill("old-skill"))
        self.assertEqual(self.install("--check")[0], 1)
        code, envelope = self.install("--skill", SKILL)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.lexists(self.repo.path(".agents", "skills", "old-skill")), "--skill never prunes")
        code, envelope = self.install()
        self.assertEqual(code, 0)
        self.assertIn((".agents/skills/old-skill", "orphan", "remove"), self.entries(envelope))
        self.assertFalse(os.path.lexists(self.repo.path(".agents", "skills", "old-skill")))
        self.assertTrue(os.path.isdir(foreign), "unmanaged entries are never pruned")

    def test_unknown_skill(self):
        code, envelope = self.install("--skill", "ghost")
        self.assertEqual((code, envelope["errors"][0]["code"]), (2, "SKILL_NOT_FOUND"))


class TestGlobal(InstallTestCase):
    def test_global_install_uses_absolute_symlinks_under_home(self):
        home = self.repo.path("home")
        os.makedirs(home)
        with fx.support.env(HOME=home):
            code, envelope = self.install("--global")
            self.assertEqual(code, 0)
            self.assertEqual(envelope["payload"]["root"], "~")
            self.assertEqual(envelope["payload"]["entries"][0]["path"], "~/.agents/skills/demo-skill")
            for folder in (".agents", ".claude"):
                dest = os.path.join(home, folder, "skills", SKILL)
                self.assertTrue(os.path.isabs(os.readlink(dest)))
                self.assertEqual(os.path.realpath(dest), os.path.realpath(self.repo.skill(SKILL)))
            self.assertEqual(self.install("--global", "--check")[0], 0)

    def test_global_and_project_are_exclusive(self):
        code, envelope = self.install("--global", "--project", self.repo.root)
        self.assertEqual((code, envelope["errors"][0]["code"]), (2, "USAGE"))


if __name__ == "__main__":
    unittest.main()
