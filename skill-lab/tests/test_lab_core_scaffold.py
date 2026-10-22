"""skill-lab new (SPEC-101 FR-020..FR-022): the scaffold validates, its tests and cases pass, refusals hold."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest

from tests import test_lab_core_fixtures as fx

from _skillkit import assertions, frontmatter, jsonschema_mini, schemas
from lab import install, paths, scaffold, validate

NAME = "demo-skill"


class ScaffoldTestCase(unittest.TestCase):
    def setUp(self):
        self.repo = fx.Repo.for_test(self)

    def new(self, *args):
        code, envelope = fx.run(scaffold.main, ["--repo", self.repo.root, "--now", fx.NOW] + list(args))
        fx.assert_envelope(self, envelope, code, scaffold.PAYLOAD_SCHEMA)
        return code, envelope

    def validate(self, *args):
        code, envelope = fx.run(validate.main, ["--repo", self.repo.root] + list(args))
        fx.assert_envelope(self, envelope, code)
        return code, envelope


class TestScaffoldOutput(ScaffoldTestCase):
    """One scaffold, inspected from every angle."""

    def setUp(self):
        super().setUp()
        code, self.envelope = self.new(NAME, "--family", "roles")
        self.assertEqual(code, 0, self.envelope)
        self.skill = self.repo.skill(NAME)

    def test_payload_lists_the_skill_and_spec(self):
        payload = self.envelope["payload"]
        self.assertEqual((payload["name"], payload["spec"], payload["family"]), (NAME, "SPEC-001", "roles"))
        self.assertEqual(payload["skill_path"], "skills/demo-skill")
        self.assertEqual(payload["spec_path"], "skill-lab/specs/001-demo-skill")
        for relative in payload["files"]:
            self.assertTrue(os.path.isfile(self.repo.path(*relative.split("/"))), relative)
        self.assertIn("skills/demo-skill/scripts/_skillkit/envelope.py", payload["files"])
        self.assertIn("skills/demo-skill/assets/schemas/envelope.v1.schema.json", payload["files"])
        self.assertFalse([f for f in payload["files"] if f.endswith(".tmpl") or "/_spec/" in f])

    def test_validates_with_zero_errors_and_only_scaffold_and_install_warnings(self):
        code, envelope = self.validate("--skill", NAME)
        self.assertEqual(code, 0, fx.rules(envelope))
        self.assertEqual(set(fx.rules(envelope)), {"scaffold.todo", "install.not-installed"})
        self.assertEqual(fx.run(install.main, ["--repo", self.repo.root])[0], 0)
        code, envelope = self.validate("--skill", NAME)
        self.assertEqual(set(fx.rules(envelope)), {"scaffold.todo"})

    def test_frontmatter_is_filled_in(self):
        with open(os.path.join(self.skill, "SKILL.md"), encoding="utf-8") as handle:
            parsed = frontmatter.parse(handle.read())
        self.assertTrue(parsed.ok, parsed.issues)
        self.assertEqual(frontmatter.lint(parsed, folder_name=NAME), [])
        self.assertEqual(
            parsed.data["metadata"],
            {"version": "0.1.0", "family": "roles", "spec": "SPEC-001", "author": "TODO(scaffold) author"},
        )
        self.assertIn("TODO(scaffold)", parsed.data["description"])
        self.assertGreaterEqual(len(parsed.data["description"]), 350)

    def test_example_script_is_executable_and_its_unit_tests_pass(self):
        self.assertTrue(os.access(os.path.join(self.skill, "scripts", "example.py"), os.X_OK))
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=self.skill,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout.decode())
        self.assertIn("Ran 4 tests", proc.stdout.decode())

    def test_every_case_is_valid_and_every_deterministic_case_passes(self):
        case_schema = schemas.load_schema("benchmark-case", [fx.support.SCHEMA_DIR])
        cases_dir = os.path.join(self.skill, "evals", "cases")
        tiers = []
        for filename in sorted(os.listdir(cases_dir)):
            with open(os.path.join(cases_dir, filename), encoding="utf-8") as handle:
                case = json.load(handle)
            with self.subTest(case=filename):
                self.assertEqual(jsonschema_mini.validate(case, case_schema), [])
                self.assertEqual(case["skill"], NAME)
                tiers.append(case["tier"])
                if case["tier"] == "deterministic":
                    self.assert_case_passes(case)
        self.assertEqual(sorted(set(tiers)), ["agentic", "deterministic", "trigger"])
        self.assertEqual(tiers.count("deterministic"), 4)

    def assert_case_passes(self, case):
        proc = subprocess.run(
            [sys.executable, case["run"]["script"]] + case["run"]["args"],
            cwd=self.skill,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        self.assertEqual(proc.returncode, case["expect"]["exit_code"])
        envelope = json.loads(proc.stdout.decode())
        vendored = [os.path.join(self.skill, "assets", "schemas")]
        self.assertEqual(schemas.validate_envelope(envelope, exit_code=proc.returncode, search_dirs=vendored), [])
        for result in assertions.evaluate_all(envelope, case["expect"]["assertions"]):
            self.assertTrue(result["passed"], result)

    def test_spec_stub_has_the_required_sections_and_complete_traceability(self):
        spec_dir = self.repo.path("skill-lab", "specs", "001-demo-skill")
        with open(os.path.join(spec_dir, "spec.md"), encoding="utf-8") as handle:
            spec = handle.read()
        for heading in (
            "## User Scenarios & Testing",
            "### Functional Requirements",
            "## Success Criteria",
            "## Non-goals",
            "## Contracts",
            "## Error semantics",
            "## Security",
            "## Runtime compatibility",
        ):
            self.assertIn(heading, spec)
        self.assertIn("**Created**: 2026-10-22", spec)
        with open(os.path.join(spec_dir, "traceability.json"), encoding="utf-8") as handle:
            trace = json.load(handle)
        self.assertEqual(trace["spec"], "SPEC-001")
        self.assertEqual([r["id"] for r in trace["requirements"]], ["FR-001", "FR-002"])

    def test_no_staging_folders_are_left_behind(self):
        self.assertEqual(sorted(os.listdir(self.repo.path("skills"))), [NAME])
        self.assertEqual(sorted(os.listdir(self.repo.path("skill-lab", "specs"))), ["001-demo-skill"])


class TestScaffoldOptions(ScaffoldTestCase):
    def test_dry_run_writes_nothing(self):
        code, envelope = self.new(NAME, "--dry-run")
        self.assertEqual(code, 0)
        self.assertTrue(envelope["payload"]["dry_run"])
        self.assertIn("skills/demo-skill/SKILL.md", envelope["payload"]["files"])
        self.assertEqual(os.listdir(self.repo.path("skills")), [])
        self.assertEqual(os.listdir(self.repo.path("skill-lab", "specs")), [])

    def test_description_and_author_are_escaped(self):
        description = 'Checks "quoted" input and a back\\slash. Use when a user asks to check documents. ' * 4
        code, _envelope = self.new(NAME, "--description", description.strip(), "--author", 'Ada "A" Lovelace')
        self.assertEqual(code, 0)
        with open(self.repo.skill(NAME, "SKILL.md"), encoding="utf-8") as handle:
            parsed = frontmatter.parse(handle.read())
        self.assertTrue(parsed.ok, parsed.issues)
        self.assertEqual(parsed.data["description"], description.strip())
        self.assertEqual(parsed.data["metadata"]["author"], 'Ada "A" Lovelace')

    def test_spec_numbers_skip_used_ones(self):
        os.makedirs(self.repo.path("skill-lab", "specs", "001-taken"))
        os.makedirs(self.repo.path("skill-lab", "specs", "100-lab"))
        self.repo.add_skill("other-skill", spec_number=2)
        code, envelope = self.new(NAME)
        self.assertEqual(envelope["payload"]["spec"], "SPEC-003")
        code, envelope = self.new("named-skill", "--spec", "SPEC-042")
        self.assertEqual((code, envelope["payload"]["spec_path"]), (0, "skill-lab/specs/042-named-skill"))


class TestScaffoldRefusals(ScaffoldTestCase):
    def assertRefused(self, args, code, error_code):
        actual, envelope = self.new(*args)
        self.assertEqual((actual, envelope["errors"][0]["code"]), (code, error_code))

    def test_invalid_names_exit_2(self):
        for name in ("Bad", "bad_name", "bad-", "a" * 65, "bad--name"):
            with self.subTest(name=name):
                self.assertRefused([name], 2, "INVALID_NAME")
        self.assertRefused(["-bad"], 2, "USAGE")  # argparse reads a leading dash as a flag

    def test_reserved_name_exits_4(self):
        self.assertRefused(["create-skill"], 4, "SKILL_NAME_RESERVED")

    def test_existing_skill_exits_4_and_is_untouched(self):
        self.repo.add_skill(NAME)
        before = self.repo.read("skills/%s/SKILL.md" % NAME)
        self.assertRefused([NAME], 4, "SKILL_EXISTS")
        self.assertEqual(self.repo.read("skills/%s/SKILL.md" % NAME), before)

    def test_spec_conflicts(self):
        os.makedirs(self.repo.path("skill-lab", "specs", "007-someone"))
        self.assertRefused([NAME, "--spec", "SPEC-007"], 4, "SPEC_EXISTS")
        self.assertRefused([NAME, "--spec", "SPEC-7"], 2, "INVALID_SPEC")

    def test_bad_text_options(self):
        self.assertRefused([NAME, "--description", "two\nlines"], 2, "INVALID_TEXT")
        self.assertRefused([NAME, "--description", "x" * 1025], 2, "INVALID_TEXT")

    def test_unknown_placeholder_is_a_template_error(self):
        self.repo.write("skill-lab/templates/skill/references/extra.md.tmpl", "{{nonsense}}\n")
        self.assertRefused([NAME], 2, "TEMPLATE_INVALID")
        self.assertEqual(os.listdir(self.repo.path("skills")), [], "a failed render leaves nothing behind")

    def test_missing_template(self):
        shutil.rmtree(self.repo.path("skill-lab", "templates"))
        self.assertRefused([NAME], 2, "TEMPLATE_INVALID")


CONVENTIONS_TABLE = """# Conventions

## 6. Specs, ADRs, traceability

| Spec | Skill / component | Family |
|---|---|---|
| SPEC-001 | `lead-architect` | roles |
| SPEC-003 | `review-verifier` | roles |
| SPEC-100 | JSON contracts + `skillkit` | lab |

## 7. Roles

| SPEC-002 | `not-in-section-6` | meta |
"""


class TestScaffoldConventions(ScaffoldTestCase):
    """CONVENTIONS §6 assigns spec numbers and families; the scaffold follows it (SPEC-101 FR-020)."""

    def setUp(self):
        super().setUp()
        self.repo.write("skill-lab/docs/CONVENTIONS.md", CONVENTIONS_TABLE)

    def assertResult(self, args, code, error_code=None):
        actual, envelope = self.new(*args)
        self.assertEqual(actual, code, envelope)
        if error_code:
            self.assertEqual(envelope["errors"][0]["code"], error_code)
        return envelope

    def test_planned_skills_reads_only_the_section_6_skill_rows(self):
        planned = scaffold.planned_skills(paths.Layout.at(self.repo.root))
        self.assertEqual(planned, {"lead-architect": (1, "roles"), "review-verifier": (3, "roles")})

    def test_the_real_table_lists_the_thirteen_catalog_skills(self):
        planned = scaffold.planned_skills(paths.Layout.at())
        self.assertEqual(len(planned), 13)
        self.assertEqual(planned["review-verifier"], (3, "roles"))
        self.assertEqual(planned["speckit-development"], (13, "speckit-gitea"))

    def test_a_catalog_skill_gets_its_assigned_spec_and_family(self):
        payload = self.assertResult(["review-verifier"], 0)["payload"]
        self.assertEqual((payload["spec"], payload["family"]), ("SPEC-003", "roles"))
        with open(self.repo.skill("review-verifier", "SKILL.md"), encoding="utf-8") as handle:
            metadata = frontmatter.parse(handle.read()).data["metadata"]
        self.assertEqual((metadata["spec"], metadata["family"]), ("SPEC-003", "roles"))

    def test_matching_flags_are_accepted(self):
        payload = self.assertResult(["review-verifier", "--spec", "SPEC-003", "--family", "roles"], 0)["payload"]
        self.assertEqual(payload["spec_path"], "skill-lab/specs/003-review-verifier")

    def test_contradicting_flags_exit_2(self):
        self.assertResult(["review-verifier", "--spec", "SPEC-009"], 2, "SPEC_ASSIGNED")
        self.assertResult(["review-verifier", "--family", "meta"], 2, "FAMILY_ASSIGNED")
        self.assertEqual(os.listdir(self.repo.path("skills")), [])

    def test_other_skills_skip_reserved_numbers(self):
        payload = self.assertResult([NAME], 0)["payload"]
        self.assertEqual((payload["spec"], payload["family"]), ("SPEC-002", "meta"))
        self.assertResult(["second-skill", "--spec", "SPEC-001"], 4, "SPEC_RESERVED")

    def test_a_spec_written_first_is_kept_and_only_the_skill_is_rendered(self):
        spec = self.repo.write("skill-lab/specs/003-review-verifier/spec.md", "# Written first\n")
        payload = self.assertResult(["review-verifier"], 0)["payload"]
        self.assertFalse(payload["spec_created"])
        self.assertEqual(payload["spec_path"], "skill-lab/specs/003-review-verifier")
        self.assertFalse([f for f in payload["files"] if f.startswith("skill-lab/specs/")])
        with open(spec, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "# Written first\n")
        self.assertEqual(os.listdir(self.repo.path("skill-lab", "specs", "003-review-verifier")), ["spec.md"])
        self.assertEqual(sorted(os.listdir(self.repo.path("skill-lab", "specs"))), ["003-review-verifier"])
        self.assertTrue(os.path.isfile(self.repo.skill("review-verifier", "SKILL.md")))

    def test_an_unlisted_skill_reuses_its_existing_spec_number(self):
        os.makedirs(self.repo.path("skill-lab", "specs", "014-demo-skill"))
        payload = self.assertResult([NAME], 0)["payload"]
        self.assertEqual((payload["spec"], payload["spec_created"]), ("SPEC-014", False))
        self.assertResult(["other-skill", "--spec", "SPEC-014"], 4, "SPEC_EXISTS")

    def test_a_spec_folder_numbered_against_the_table_exits_2(self):
        os.makedirs(self.repo.path("skill-lab", "specs", "020-review-verifier"))
        self.assertResult(["review-verifier"], 2, "SPEC_ASSIGNED")

    def test_new_specs_are_created(self):
        self.assertTrue(self.assertResult(["lead-architect"], 0)["payload"]["spec_created"])


class TestRendering(unittest.TestCase):
    def test_render_text(self):
        self.assertEqual(scaffold.render_text("a {{name}} b {{ name }}", {"name": "x"}), "a x b x")
        with self.assertRaises(scaffold.TemplateError):
            scaffold.render_text("{{other}}", {"name": "x"})

    def test_title(self):
        self.assertEqual(scaffold.title_of("review-verifier"), "Review Verifier")


if __name__ == "__main__":
    unittest.main()
