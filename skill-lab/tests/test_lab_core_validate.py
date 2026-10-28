"""skill-lab validate (SPEC-101 FR-002..FR-012): every [V] rule fires on a skill that breaks it."""

from __future__ import annotations

import json
import os
import shutil
import sys
import types
import unittest
from unittest import mock

from tests import test_lab_core_fixtures as fx

from _skillkit import schemas, stdlib_modules
from lab import catalog, validate

SKILL = "demo-skill"


class ValidateTestCase(unittest.TestCase):
    """Starts from the clean fixture skill; each test breaks one thing."""

    def setUp(self):
        self.repo = fx.Repo.for_test(self)
        self.repo.add_skill(SKILL)

    def validate(self, *args, run_scripts=False):
        argv = ["--repo", self.repo.root, "--now", fx.NOW] + ([] if run_scripts else ["--no-run"]) + list(args)
        code, envelope = fx.run(validate.main, argv)
        fx.assert_envelope(self, envelope, code)
        if envelope["payload"] is not None:
            issues = schemas.validate_payload("validation-report", envelope["payload"], [fx.support.SCHEMA_DIR])
            self.assertEqual(issues, [])
        return code, envelope

    def assertRule(self, rule, severity="error", *args, run_scripts=False):
        code, envelope = self.validate(*args, run_scripts=run_scripts)
        self.assertIn(rule, fx.rules(envelope, severity), fx.rules(envelope))
        if severity == "error":
            self.assertEqual(code, 1)
            self.assertIn(rule.upper().replace(".", "_").replace("-", "_"), [e["code"] for e in envelope["errors"]])
        return envelope

    def assertNoErrors(self, *args, run_scripts=False):
        code, envelope = self.validate(*args, run_scripts=run_scripts)
        self.assertEqual(fx.rules(envelope, "error"), [])
        self.assertEqual(code, 0)
        return envelope

    def skill_md(self):
        return self.repo.read("skills/%s/SKILL.md" % SKILL)

    def replace_in(self, relative, old, new):
        text = self.repo.read(relative)
        self.assertIn(old, text)
        self.repo.write(relative, text.replace(old, new, 1))

    def replace_in_skill_md(self, old, new):
        self.replace_in("skills/%s/SKILL.md" % SKILL, old, new)

    def finding(self, envelope, rule):
        return next(f for s in envelope["payload"]["skills"] for f in s["findings"] if f["rule"] == rule)


class TestBaseline(ValidateTestCase):
    def test_clean_skill_has_only_install_warnings(self):
        envelope = self.assertNoErrors()
        self.assertEqual(sorted(set(fx.rules(envelope))), ["install.not-installed"])
        self.assertEqual([w["code"] for w in envelope["warnings"]], ["SCRIPTS_NOT_RUN", "CATALOG_MISSING"])
        payload = envelope["payload"]
        self.assertEqual(payload["runtime_profiles"], ["zed", "claude", "codex"])
        self.assertEqual(payload["generated_at"], fx.NOW)
        self.assertEqual(payload["target"], "skills")

    def test_help_check_runs_and_passes(self):
        envelope = self.assertNoErrors(run_scripts=True)
        self.assertNotIn("SCRIPTS_NOT_RUN", [w["code"] for w in envelope["warnings"]])


class TestFrontmatterRules(ValidateTestCase):
    def test_block_scalar_is_rejected_with_its_line(self):
        self.replace_in_skill_md('description: "', 'description: >\n  "')
        envelope = self.assertRule("frontmatter.block-scalar")
        self.assertEqual(self.finding(envelope, "frontmatter.block-scalar")["path"], "skills/demo-skill/SKILL.md:3")

    def test_unknown_key(self):
        self.replace_in_skill_md("license: Apache-2.0\n", "license: Apache-2.0\nversion: x\n")
        self.assertRule("frontmatter.unknown-key")

    def test_name_must_equal_folder(self):
        self.replace_in_skill_md("name: demo-skill", "name: other-skill")
        self.assertRule("frontmatter.name-folder-mismatch")

    def test_reserved_name(self):
        shutil.move(self.repo.skill(SKILL), self.repo.skill("create-skill"))
        self.repo.write("skills/create-skill/SKILL.md", fx.skill_md("create-skill", "SPEC-001"))
        self.assertRule("frontmatter.name-reserved", "error", "--skill", "create-skill")

    def test_name_pattern(self):
        shutil.move(self.repo.skill(SKILL), self.repo.skill("Bad_Name"))
        self.repo.write("skills/Bad_Name/SKILL.md", fx.skill_md("Bad_Name", "SPEC-001"))
        self.assertRule("frontmatter.name-pattern")

    def test_description_must_be_double_quoted(self):
        self.replace_in_skill_md(
            'description: "%s"' % fx.DESCRIPTION, "description: %s" % fx.DESCRIPTION.replace(":", "")
        )
        self.assertRule("frontmatter.not-double-quoted")

    def test_description_over_1024_chars(self):
        self.replace_in_skill_md(fx.DESCRIPTION, "Use when x. " + "y" * 1100)
        self.assertRule("frontmatter.too-long")

    def test_description_length_and_use_when_are_warnings(self):
        self.replace_in_skill_md(fx.DESCRIPTION, "Checks JSON.")
        envelope = self.assertNoErrors()
        warnings = fx.rules(envelope, "warning")
        self.assertIn("frontmatter.description-length", warnings)
        self.assertIn("frontmatter.description-use-when", warnings)

    def test_unescaped_quote_in_description(self):
        self.replace_in_skill_md("Check a JSON", 'Check a "JSON')
        self.assertRule("frontmatter.trailing-content")

    def test_metadata_rules(self):
        self.replace_in_skill_md("  family: meta\n", "  family: kitchen\n")
        self.replace_in_skill_md('  author: "Skill Lab Tests"\n', "")
        envelope = self.assertRule("frontmatter.bad-metadata-value")
        self.assertIn("frontmatter.missing-metadata-key", fx.rules(envelope, "error"))

    def test_bom_is_an_error_for_zed_and_a_warning_otherwise(self):
        self.repo.write("skills/%s/SKILL.md" % SKILL, "﻿" + self.skill_md())
        self.assertRule("frontmatter.bom", "error")
        envelope = self.assertNoErrors("--runtime", "claude,codex")
        self.assertIn("frontmatter.bom", fx.rules(envelope, "warning"))

    def test_disable_model_invocation_warns(self):
        self.replace_in_skill_md("license: Apache-2.0\n", "license: Apache-2.0\ndisable-model-invocation: true\n")
        envelope = self.assertNoErrors()
        self.assertIn("frontmatter.disable-model-invocation", fx.rules(envelope, "warning"))

    def test_missing_frontmatter_skips_body_rules(self):
        self.repo.write("skills/%s/SKILL.md" % SKILL, "# Just a title\n")
        envelope = self.assertRule("frontmatter.missing-open-delimiter")
        self.assertFalse([rule for rule in fx.rules(envelope) if rule.startswith("body.")])

    def test_not_utf8(self):
        with open(self.repo.skill(SKILL, "SKILL.md"), "wb") as handle:
            handle.write(b"---\nname: demo-skill\xff\n---\n")
        self.assertRule("frontmatter.unreadable")


class TestBodyRules(ValidateTestCase):
    def test_line_limit(self):
        self.repo.write("skills/%s/SKILL.md" % SKILL, self.skill_md() + "\n" * 260)
        self.assertRule("body.too-many-lines")

    def test_byte_limit(self):
        self.repo.write("skills/%s/SKILL.md" % SKILL, self.skill_md() + ("x" * 100 + "\n") * 125)
        self.assertRule("body.too-large")

    def test_required_heading_missing(self):
        self.replace_in_skill_md("## Guardrails\n", "## Safety\n")
        envelope = self.assertRule("body.heading-missing")
        self.assertIn("Guardrails", self.finding(envelope, "body.heading-missing")["message"])

    def test_heading_order(self):
        self.replace_in_skill_md("## Inputs\n", "## Inputs-moved\n")
        self.replace_in_skill_md("## Outputs\n", "## Inputs\n\n## Outputs\n")
        self.assertRule("body.heading-order")

    def test_runtime_notes_must_be_last(self):
        self.repo.write("skills/%s/SKILL.md" % SKILL, self.skill_md() + "\n## Appendix\n\nMore.\n")
        self.assertRule("body.heading-order")

    def test_extra_sections_are_allowed_before_runtime_notes(self):
        self.replace_in_skill_md("## Runtime notes\n", "## Examples\n\nOne.\n\n## Runtime notes\n")
        self.assertNoErrors()

    def test_duplicate_heading(self):
        self.replace_in_skill_md("## Outputs\n", "## Outputs\n\nA.\n\n## Outputs\n")
        self.assertRule("body.heading-duplicate")

    def test_title_required(self):
        self.replace_in_skill_md("# Fixture Skill\n", "")
        self.assertRule("body.title")

    def test_single_title(self):
        self.replace_in_skill_md("## Outputs\n", "# Second title\n\n## Outputs\n")
        self.assertRule("body.title")

    def test_procedure_must_be_numbered(self):
        self.replace_in_skill_md("1. Run", "- Run")
        self.replace_in_skill_md("2. Report", "- Report")
        self.assertRule("body.procedure-not-numbered")

    def test_broken_relative_link(self):
        self.replace_in_skill_md("(references/guide.md)", "(references/missing.md)")
        envelope = self.assertRule("body.link-broken")
        self.assertRegex(self.finding(envelope, "body.link-broken")["path"], r"^skills/demo-skill/SKILL\.md:\d+$")

    def test_link_leaving_the_skill(self):
        self.replace_in_skill_md("(references/guide.md)", "(../other/SKILL.md)")
        self.assertRule("body.link-escapes")

    def test_absolute_link(self):
        self.replace_in_skill_md("(references/guide.md)", "(/etc/passwd)")
        self.assertRule("body.link-escapes")

    def test_skill_path_in_inline_code_must_exist(self):
        self.replace_in_skill_md("scripts/check.py --input", "scripts/missing.py --input")
        self.assertRule("body.link-broken")

    def test_urls_anchors_code_fences_and_placeholders_are_ignored(self):
        extra = (
            "\nSee [docs](https://zed.dev/docs), [above](#inputs) and [mail](mailto:a@b.c).\n\n"
            "```sh\npython3 scripts/not-here.py\n[x](missing.md)\n```\n\n"
            "Use `references/<topic>.md` or `assets/schemas/*.json`.\n\n"
        )
        self.replace_in_skill_md("## Outputs\n", extra + "## Outputs\n")
        self.assertNoErrors()

    def test_link_with_fragment_and_title(self):
        self.replace_in_skill_md("(references/guide.md)", '(references/guide.md#top "Guide")')
        self.assertNoErrors()


class TestReferenceRules(ValidateTestCase):
    def test_long_reference_without_toc_warns(self):
        self.repo.write("skills/%s/references/guide.md" % SKILL, "# Guide\n" + "line\n" * 320)
        envelope = self.assertNoErrors()
        self.assertIn("references.too-long", fx.rules(envelope, "warning"))
        self.assertIn("references.no-toc", fx.rules(envelope, "warning"))

    def test_unreadable_reference(self):
        with open(self.repo.skill(SKILL, "references", "guide.md"), "wb") as handle:
            handle.write(b"# Guide \xff\n")
        self.assertRule("references.unreadable")

    def test_toc_satisfies_the_rule(self):
        self.repo.write(
            "skills/%s/references/guide.md" % SKILL, "# Guide\n\n## Contents\n\n- [A](#a)\n" + "line\n" * 150
        )
        envelope = self.assertNoErrors()
        self.assertNotIn("references.no-toc", fx.rules(envelope))


class TestScriptRules(ValidateTestCase):
    SCRIPT = "skills/%s/scripts/check.py" % SKILL

    def test_shebang(self):
        self.replace_in(self.SCRIPT, "#!/usr/bin/env python3\n", "#!/usr/bin/python\n")
        self.assertRule("scripts.shebang")

    def test_docstring(self):
        self.replace_in(self.SCRIPT, '"""Echo a JSON input document as the payload (lab-core test fixture)."""\n', "")
        self.assertRule("scripts.docstring")

    def test_future_import(self):
        self.replace_in(self.SCRIPT, "from __future__ import annotations\n", "")
        self.assertRule("scripts.future-import")

    def test_unreadable_source(self):
        with open(self.repo.path(*self.SCRIPT.split("/")), "wb") as handle:
            handle.write(b"#!/usr/bin/env python3\n\xff\n")
        self.assertRule("scripts.unreadable")

    def test_executable_bit(self):
        os.chmod(self.repo.path(*self.SCRIPT.split("/")), 0o644)
        self.assertRule("scripts.executable")

    def test_third_party_import(self):
        self.replace_in(self.SCRIPT, "import os\n", "import os\nimport requests\n")
        envelope = self.assertRule("scripts.import-third-party")
        self.assertRegex(self.finding(envelope, "scripts.import-third-party")["path"], r"check\.py:\d+$")

    def test_module_missing_from_python_39(self):
        self.replace_in(self.SCRIPT, "import os\n", "import os\nimport tomllib\n")
        self.assertRule("scripts.import-not-portable")

    def test_newer_stdlib_module_is_not_portable_when_validating_on_python_39(self):
        self.replace_in(self.SCRIPT, "import os\n", "import os\nimport tomllib\n")
        python39_sys = types.SimpleNamespace(builtin_module_names=sys.builtin_module_names)
        with mock.patch.object(stdlib_modules, "sys", python39_sys):
            envelope = self.assertRule("scripts.import-not-portable")
        self.assertNotIn("scripts.import-third-party", fx.rules(envelope))

    def test_local_modules_and_relative_imports_are_allowed(self):
        helper = '"""Shared helpers."""\n\nfrom __future__ import annotations\n\nimport json\n'
        self.repo.write("skills/%s/scripts/_helpers.py" % SKILL, helper)
        self.repo.write(
            "skills/%s/scripts/pkg/__init__.py" % SKILL,
            '"""Package."""\n\nfrom __future__ import annotations\n\nfrom . import json_tools  # noqa\n',
        )
        self.replace_in(
            self.SCRIPT, "import os\n", "import os\n\nimport _helpers  # noqa: F401\nimport pkg  # noqa: F401\n"
        )
        self.assertNoErrors()

    def test_helper_modules_need_future_import_but_no_shebang(self):
        self.repo.write("skills/%s/scripts/_helpers.py" % SKILL, '"""Helpers."""\n\nimport json\n')
        envelope = self.assertRule("scripts.future-import")
        self.assertNotIn("scripts.shebang", fx.rules(envelope))
        self.assertNotIn("scripts.executable", fx.rules(envelope))

    def test_python_310_syntax(self):
        self.replace_in(self.SCRIPT, "def main():\n", "def main():\n    match 1:\n        case 1:\n            pass\n")
        self.assertRule("scripts.syntax")

    def test_shell_true_and_eval(self):
        self.replace_in(
            self.SCRIPT,
            "    args = parser.parse_args()\n",
            "    args = parser.parse_args()\n"
            "    import subprocess\n"
            "    subprocess.run('ls', shell=True)\n"
            "    eval('1')\n",
        )
        envelope = self.assertRule("scripts.shell-true")
        self.assertIn("scripts.eval-exec", fx.rules(envelope, "error"))

    def test_help_must_exit_zero(self):
        self.replace_in(self.SCRIPT, "def main():\n", "if '--help' in sys.argv:\n    sys.exit(3)\n\n\ndef main():\n")
        envelope = self.assertRule("scripts.help", "error", run_scripts=True)
        self.assertIn("exited 3", self.finding(envelope, "scripts.help")["message"])

    def test_help_timeout(self):
        self.replace_in(self.SCRIPT, "def main():\n", "import time\ntime.sleep(10)\n\n\ndef main():\n")
        with mock.patch.object(validate, "HELP_TIMEOUT_S", 1):
            envelope = self.assertRule("scripts.help", "error", run_scripts=True)
        self.assertIn("did not finish", self.finding(envelope, "scripts.help")["message"])

    def test_help_runs_without_secrets(self):
        self.replace_in(
            self.SCRIPT, "def main():\n", "if os.environ.get('GITEA_TOKEN'):\n    sys.exit(9)\n\n\ndef main():\n"
        )
        with fx.support.env(GITEA_TOKEN="a-secret-token-value"):
            self.assertNoErrors(run_scripts=True)


class TestVendorRules(ValidateTestCase):
    def test_modified_vendored_skillkit(self):
        self.replace_in(
            "skills/%s/scripts/_skillkit/ids.py" % SKILL,
            '"""',
            '"""Edited. ',
        )
        envelope = self.assertRule("vendor.skillkit-drift")
        self.assertIn("changed ids.py", self.finding(envelope, "vendor.skillkit-drift")["message"])

    def test_extra_file_in_vendored_skillkit(self):
        self.repo.write("skills/%s/scripts/_skillkit/stale.py" % SKILL, "")
        envelope = self.assertRule("vendor.skillkit-drift")
        self.assertIn("extra stale.py", self.finding(envelope, "vendor.skillkit-drift")["message"])

    def test_pycache_is_ignored(self):
        self.repo.write("skills/%s/scripts/_skillkit/__pycache__/ids.cpython-313.pyc" % SKILL, "x")
        self.assertNoErrors()

    def test_missing_vendored_skillkit(self):
        shutil.rmtree(self.repo.skill(SKILL, "scripts", "_skillkit"))
        self.assertRule("vendor.skillkit-missing")

    def test_unknown_schema(self):
        self.repo.write_json("skills/%s/assets/schemas/mine.v1.schema.json" % SKILL, {})
        self.assertRule("vendor.schema-unknown")

    def test_schema_drift(self):
        self.repo.write_json("skills/%s/assets/schemas/envelope.v1.schema.json" % SKILL, {"edited": True})
        self.assertRule("vendor.schema-drift")

    def test_envelope_schema_required(self):
        os.remove(self.repo.skill(SKILL, "assets", "schemas", "envelope.v1.schema.json"))
        self.assertRule("vendor.envelope-missing")


class TestEvalRules(ValidateTestCase):
    CASES = "skills/%s/evals/cases/" % SKILL

    def edit_case(self, case_id, **changes):
        path = self.CASES + case_id + ".json"
        document = json.loads(self.repo.read(path))
        for key, value in changes.items():
            if value is None:
                document.pop(key, None)
            else:
                document[key] = value
        self.repo.write_json(path, document)

    def test_unreadable_case(self):
        self.repo.write(self.CASES + "det-1.json", "{not json")
        envelope = self.assertRule("evals.case-unreadable")
        self.assertIn("evals.deterministic-count", fx.rules(envelope, "error"))

    def test_duplicate_keys_are_rejected(self):
        self.repo.write(self.CASES + "det-1.json", '{"id": "det-1", "id": "det-1"}')
        self.assertRule("evals.case-unreadable")

    def test_schema_invalid_case(self):
        self.edit_case("det-1", run=None)
        self.assertRule("evals.case-schema")

    def test_id_must_equal_file_name(self):
        self.edit_case("det-1", id="det-one")
        self.assertRule("evals.case-id-mismatch")

    def test_duplicate_ids(self):
        document = json.loads(self.repo.read(self.CASES + "det-1.json"))
        self.repo.write_json(self.CASES + "det-5.json", document)
        envelope = self.assertRule("evals.case-id-duplicate")
        self.assertIn("evals.case-id-mismatch", fx.rules(envelope))

    def test_case_skill_must_be_this_skill(self):
        self.edit_case("det-1", skill="other-skill")
        self.assertRule("evals.case-skill-mismatch")

    def test_case_script_must_exist(self):
        self.edit_case("det-1", run={"script": "scripts/gone.py", "args": []})
        self.assertRule("evals.case-script-missing")

    def test_stdin_fixture_must_exist(self):
        self.edit_case(
            "det-1", run={"script": "scripts/check.py", "args": [], "stdin_file": "evals/fixtures/gone.json"}
        )
        self.assertRule("evals.fixture-missing")

    def test_agentic_fixture_must_exist(self):
        self.edit_case("agentic-1", fixtures=["evals/fixtures/gone.json"])
        self.assertRule("evals.fixture-missing")

    def test_missing_path_argument_is_a_warning(self):
        self.edit_case("det-1", run={"script": "scripts/check.py", "args": ["--input", "evals/fixtures/gone.json"]})
        envelope = self.assertNoErrors()
        self.assertIn("evals.arg-path-missing", fx.rules(envelope, "warning"))

    def test_output_schema_must_be_canonical(self):
        self.edit_case("agentic-1", output_schema="urn:skill-lab:schema:imaginary:v1")
        self.assertRule("evals.output-schema-unknown")

    def test_tier_minimums(self):
        for case_id in ("det-4", "agentic-2", "trigger-pos-3", "trigger-neg-1"):
            os.remove(self.repo.path(*(self.CASES + case_id + ".json").split("/")))
        envelope = self.assertRule("evals.deterministic-count")
        errors = fx.rules(envelope, "error")
        for rule in ("evals.agentic-count", "evals.positive-trigger-count", "evals.negative-trigger-count"):
            self.assertIn(rule, errors)

    def test_no_evals_folder(self):
        shutil.rmtree(self.repo.skill(SKILL, "evals"))
        envelope = self.assertRule("evals.deterministic-count")
        self.assertIn("evals.negative-trigger-count", fx.rules(envelope))

    def test_negative_trigger_may_name_a_neighbour(self):
        self.repo.add_skill("other-skill")
        self.edit_case("trigger-neg-1", expect_skill="other-skill")
        self.assertNoErrors("--skill", SKILL)
        self.edit_case("trigger-neg-1", expect_skill="ghost-skill")
        envelope = self.assertNoErrors("--skill", SKILL)
        self.assertIn("evals.trigger-unknown-skill", fx.rules(envelope, "warning"))


class TestTestsAndSpecRules(ValidateTestCase):
    SPEC_DIR = "skill-lab/specs/001-demo-skill/"

    def trace(self):
        return json.loads(self.repo.read(self.SPEC_DIR + "traceability.json"))

    def write_trace(self, trace):
        self.repo.write_json(self.SPEC_DIR + "traceability.json", trace)

    def test_tests_required(self):
        shutil.rmtree(self.repo.skill(SKILL, "tests"))
        self.assertRule("tests.missing")

    def test_spec_folder_required(self):
        shutil.rmtree(self.repo.path(*self.SPEC_DIR.split("/")))
        self.assertRule("spec.missing")

    def test_spec_folder_must_be_unique(self):
        os.makedirs(self.repo.path("skill-lab", "specs", "001-another"))
        self.assertRule("spec.ambiguous")

    def test_spec_folder_name_is_a_warning(self):
        shutil.move(self.repo.path(*self.SPEC_DIR.split("/")), self.repo.path("skill-lab", "specs", "001-renamed"))
        envelope = self.assertNoErrors()
        self.assertIn("spec.folder-name", fx.rules(envelope, "warning"))

    def test_spec_md_required(self):
        os.remove(self.repo.path(*(self.SPEC_DIR + "spec.md").split("/")))
        self.assertRule("spec.md-missing")

    def test_traceability_required_and_strict(self):
        os.remove(self.repo.path(*(self.SPEC_DIR + "traceability.json").split("/")))
        self.assertRule("spec.traceability-missing")
        self.repo.write(self.SPEC_DIR + "traceability.json", "{")
        self.assertRule("spec.traceability-invalid")
        self.write_trace({"spec": "SPEC-001", "requirements": [{"id": "FR-001"}]})
        self.assertRule("spec.traceability-invalid")

    def test_traceability_spec_id(self):
        trace = self.trace()
        trace["spec"] = "SPEC-002"
        self.write_trace(trace)
        self.assertRule("spec.traceability-mismatch")

    def test_paths_must_exist(self):
        trace = self.trace()
        trace["requirements"][0]["implemented_by"].append("skills/demo-skill/scripts/gone.py")
        self.write_trace(trace)
        self.assertRule("spec.trace-path-missing")

    def test_paths_must_stay_in_the_repository(self):
        trace = self.trace()
        trace["requirements"][0]["implemented_by"] = ["../outside.py"]
        self.write_trace(trace)
        self.assertRule("spec.trace-path-missing")

    def test_test_ids_must_name_real_methods(self):
        trace = self.trace()
        trace["requirements"][0]["verified_by"] = ["skills/demo-skill/tests/test_check.py::TestCheck::test_gone"]
        self.write_trace(trace)
        self.assertRule("spec.trace-test-missing")

    def test_every_fr_needs_verified_by(self):
        trace = self.trace()
        trace["requirements"][0]["verified_by"] = []
        self.write_trace(trace)
        self.assertRule("spec.fr-unverified")

    def test_every_fr_in_spec_md_is_traced(self):
        self.replace_in(self.SPEC_DIR + "spec.md", "- **FR-001**", "- **FR-002**: More.\n- **FR-001**")
        self.assertRule("spec.fr-untraced")

    def test_planned_requirements_only_warn_about_missing_paths(self):
        trace = self.trace()
        trace["requirements"][0]["implemented_by"].append("skills/demo-skill/scripts/later.py")
        trace["requirements"][0]["planned"] = True
        self.write_trace(trace)
        envelope = self.assertNoErrors()
        self.assertIn("spec.trace-path-missing", fx.rules(envelope, "warning"))


class TestInstallParity(ValidateTestCase):
    def test_symlinked_install_is_clean(self):
        self.repo.install(SKILL)
        envelope = self.assertNoErrors()
        self.assertNotIn("install.not-installed", fx.rules(envelope))

    def test_symlink_elsewhere_is_an_error(self):
        os.makedirs(self.repo.path("elsewhere"))
        os.makedirs(self.repo.path(".agents", "skills"))
        os.symlink(self.repo.path("elsewhere"), self.repo.path(".agents", "skills", SKILL))
        envelope = self.assertRule("install.parity")
        self.assertEqual(self.finding(envelope, "install.parity")["path"], ".agents/skills/demo-skill")

    def test_stale_managed_copy_is_an_error(self):
        from lab import install

        self.assertEqual(fx.run(install.main, ["--repo", self.repo.root, "--mode", "copy"])[0], 0)
        self.assertNoErrors()
        self.repo.write("skills/%s/references/guide.md" % SKILL, "# Guide\n\nChanged after install.\n")
        self.assertRule("install.parity")

    def test_runtime_profile_selects_the_discovery_folder(self):
        envelope = self.assertNoErrors("--runtime", "claude")
        paths_seen = [
            f["path"]
            for s in envelope["payload"]["skills"]
            for f in s["findings"]
            if f["rule"] == "install.not-installed"
        ]
        self.assertEqual(paths_seen, [".claude/skills/demo-skill"])


class TestRuntimeProfiles(ValidateTestCase):
    def test_zed_file_size_limit(self):
        self.repo.write("skills/%s/SKILL.md" % SKILL, self.skill_md() + "x" * (101 * 1024))
        envelope = self.assertRule("zed.skill-file-too-large")
        _code, claude_only = self.validate("--runtime", "claude")
        self.assertNotIn("zed.skill-file-too-large", fx.rules(claude_only))
        self.assertIn("body.too-large", fx.rules(envelope))

    def test_zed_flat_layout(self):
        self.repo.write("skills/group/nested-skill/SKILL.md", fx.skill_md("nested-skill", "SPEC-009"))
        envelope = self.assertRule("zed.flat-layout")
        group = next(s for s in envelope["payload"]["skills"] if s["name"] == "group")
        self.assertFalse(group["ok"])
        self.assertNoErrors("--runtime", "claude")

    def test_profile_parsing(self):
        self.assertEqual(validate.parse_profiles(None), ("zed", "claude", "codex"))
        self.assertEqual(validate.parse_profiles(["codex,zed"]), ("zed", "codex"))
        self.assertEqual(validate.parse_profiles(["claude", "zed"]), ("zed", "claude"))
        self.assertEqual(validate.parse_profiles(["all"]), ("zed", "claude", "codex"))
        code, envelope = fx.run(validate.main, ["--repo", self.repo.root, "--runtime", "vscode"])
        self.assertEqual(code, 2)
        self.assertEqual(envelope["errors"][0]["code"], "USAGE")


class TestCatalogBudget(ValidateTestCase):
    def test_over_budget_is_an_error(self):
        with (
            mock.patch.object(catalog, "CATALOG_LIMIT_BYTES", 100),
            mock.patch.object(catalog, "CATALOG_WARN_BYTES", 50),
        ):
            code, envelope = self.validate()
        self.assertEqual(code, 1)
        self.assertFalse(envelope["payload"]["ok"])
        self.assertEqual(envelope["payload"]["catalog"]["limit"], 100)
        self.assertEqual(envelope["errors"][0]["code"], "CATALOG_BUDGET_EXCEEDED")
        self.assertTrue(all(skill["ok"] for skill in envelope["payload"]["skills"]))

    def test_near_budget_is_a_warning(self):
        with mock.patch.object(catalog, "CATALOG_WARN_BYTES", 100):
            code, envelope = self.validate()
        self.assertEqual(code, 0)
        self.assertIn("CATALOG_BUDGET_NEAR", [w["code"] for w in envelope["warnings"]])

    def test_budget_counts_utf8_bytes_of_name_and_description(self):
        self.replace_in_skill_md("Check a JSON", "Check a JSÖN")
        _code, envelope = self.validate()
        expected = len((SKILL + fx.DESCRIPTION.replace("JSON", "JSÖN", 1)).encode("utf-8"))
        self.assertEqual(envelope["payload"]["catalog"]["bytes"], expected)

    def test_stale_catalog_warns(self):
        self.assertEqual(fx.run(catalog.main, ["--repo", self.repo.root])[0], 0)
        _code, envelope = self.validate()
        self.assertNotIn("CATALOG_STALE", [w["code"] for w in envelope["warnings"]])
        self.replace_in_skill_md("Check a JSON", "Check one JSON")
        _code, envelope = self.validate()
        self.assertIn("CATALOG_STALE", [w["code"] for w in envelope["warnings"]])


class TestRepositoryLevel(unittest.TestCase):
    def setUp(self):
        self.repo = fx.Repo.for_test(self)

    def validate(self, *args):
        code, envelope = fx.run(validate.main, ["--repo", self.repo.root, "--no-run"] + list(args))
        fx.assert_envelope(self, envelope, code)
        return code, envelope

    def test_empty_skills_folder_succeeds_with_a_warning(self):
        code, envelope = self.validate()
        self.assertEqual(code, 0)
        self.assertEqual(envelope["payload"]["skills"], [])
        self.assertIn("NO_SKILLS", [w["code"] for w in envelope["warnings"]])
        self.assertEqual(
            schemas.validate_payload("validation-report", envelope["payload"], [fx.support.SCHEMA_DIR]), []
        )

    def test_missing_skills_folder_succeeds_with_a_warning(self):
        shutil.rmtree(self.repo.path("skills"))
        code, envelope = self.validate()
        self.assertEqual(code, 0)
        self.assertIn("NO_SKILLS", [w["code"] for w in envelope["warnings"]])

    def test_ignored_folders(self):
        self.repo.add_skill("real-skill")
        os.makedirs(self.repo.path("skills", "_drafts", "x"))
        self.repo.write("skills/.hidden/SKILL.md", "not a skill")
        self.repo.write("skills/notes/README.md", "no SKILL.md here")
        code, envelope = self.validate()
        self.assertEqual(code, 0)
        self.assertEqual([s["name"] for s in envelope["payload"]["skills"]], ["real-skill"])

    def test_skill_filter(self):
        self.repo.add_skill("good-skill")
        self.repo.add_skill("bad-skill")
        os.remove(self.repo.skill("bad-skill", "tests", "test_check.py"))
        self.assertEqual(self.validate()[0], 1)
        code, envelope = self.validate("--skill", "good-skill")
        self.assertEqual(code, 0)
        self.assertEqual(envelope["payload"]["target"], "skills/good-skill")
        code, envelope = self.validate("--skill", "ghost")
        self.assertEqual(code, 2)
        self.assertEqual(envelope["errors"][0]["code"], "SKILL_NOT_FOUND")

    def test_failure_report_is_a_valid_payload(self):
        self.repo.add_skill("bad-skill")
        os.remove(self.repo.skill("bad-skill", "tests", "test_check.py"))
        code, envelope = self.validate()
        self.assertEqual(code, 1)
        self.assertFalse(envelope["payload"]["ok"])
        # The removed test file is also named in traceability.json, so two rules fire.
        self.assertEqual(fx.rules(envelope, "error"), ["tests.missing", "spec.trace-path-missing"])
        self.assertEqual(envelope["payload"]["summary"]["errors"], 2)
        self.assertEqual([e["code"] for e in envelope["errors"]], ["TESTS_MISSING", "SPEC_TRACE_PATH_MISSING"])
        self.assertEqual(
            schemas.validate_payload("validation-report", envelope["payload"], [fx.support.SCHEMA_DIR]), []
        )

    def test_unknown_repository(self):
        code, envelope = fx.run(validate.main, ["--repo", self.repo.path("nowhere")])
        self.assertEqual(code, 2)
        self.assertEqual(envelope["errors"][0]["code"], "REPO_NOT_FOUND")

    def test_check_hook_list(self):
        self.assertIn(validate.check_frontmatter, validate.SKILL_CHECKS)
        self.assertEqual(validate.SKILL_CHECKS[0], validate.check_frontmatter)


if __name__ == "__main__":
    unittest.main()
