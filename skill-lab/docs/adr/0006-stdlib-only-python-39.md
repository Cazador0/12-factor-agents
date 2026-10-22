# ADR-0006: Python 3.9+ standard library only, for every skill script and the lab

## Status

Accepted

## Date

2026-10-22

## Context

Skill scripts run on the user's machine, inside the user's project, launched by an agent through a
terminal tool. The lab runs on the same machines and in CI. The constraints:

- **Whatever `python3` is on the PATH.** The user named macOS's system Python 3.9 as a target.
  None of the three runtimes provides a Python environment for skills. A global skill under
  `~/.agents/skills/` cannot declare dependencies at all.
- **Zero install.** A skill must work right after `skill-lab install` or a plain folder copy: no
  pip, no venv, no network. Codex runs in sandboxes that may block network access, and the build
  container blocks most hosts today.
- **Supply chain.** These scripts run with `GITEA_TOKEN`, `OLLAMA_API_KEY` and `TYPESAFE_API_KEY`
  in their environment. Every third-party package would be code running with the user's
  credentials (report
  [§Independent quality assurance and engineering gates](../research/engineering-team-report.md#independent-quality-assurance-and-engineering-gates),
  supply-chain layer).
- **Agent legibility.** Models read and change these scripts. Plain stdlib Python is the code they
  read most reliably, and it needs no build step.

## Decision

1. **Everything under `skills/` and `skill-lab/` is Python 3.9 or later, standard library only.**
   Imports are limited to modules present in **both** Python 3.9 and the running interpreter
   (`_skillkit.stdlib_modules.is_portable_stdlib`; for example `tomllib` is rejected because 3.9
   lacks it), plus `_skillkit`, `lab` (lab code only) and modules local to the script.
2. **3.9-compatible source.** Each file starts with a docstring and
   `from __future__ import annotations`. There are no `match` statements, no runtime `X | Y`
   unions (they are allowed only inside annotations), and no 3.10+ APIs without a fallback. For
   example, `sys.stdlib_module_names` falls back to the shipped `PY39_STDLIB_MODULES` list.
3. **Tests use `unittest`** and run through `python3 -m unittest discover`.
4. **Third-party tools only as optional oracles.** A test may use a third-party package to
   cross-check our code, and must skip cleanly when it is absent. The differential tests against
   `jsonschema` and `rfc3339-validator` are the one case today. Linters such as ruff run outside
   the shipped code. No shipped code path imports them.
5. **We own the small pieces we would otherwise import**: a strict JSON reader, a JSON Schema
   subset validator (`jsonschema_mini`), a frontmatter parser for the strict subset, RFC 3339
   time parsing, an HTTP transport with retry on `urllib`, file locking, redaction and the
   cassette recorder. Each one has its own tests.

## Consequences

### Positive

- `python3 scripts/x.py` works anywhere Python 3.9+ exists, offline, the moment a skill is
  installed.
- No dependency resolution, no lock files, and no third-party code running with the user's
  tokens.
- One interpreter rule covers skills, lab and CI, and the validator can check it statically.

### Negative

- **We maintain a JSON Schema validator.** It supports only the subset the contracts use
  (ADR-0004), and a bug in it is a bug in every gate. Mitigations: unit tests per keyword, crafted
  invalid instances for every contract, and differential tests against `jsonschema` 4.26.0 with
  `rfc3339-validator` 0.1.4 over more than 150 instances when those packages are installed. One
  divergence is known and deliberate: the reference date-time checker rejects every leap second,
  `jsonschema_mini` accepts `23:59:60` in UTC as RFC 3339 does. That case is excluded from the
  differential comparison and covered by unit tests instead.
- **The floor is an end-of-life interpreter.** Python 3.9 no longer receives security fixes
  upstream. Supporting it is a compatibility floor, not a recommendation, and our code must not
  rely on a 3.9-specific behaviour.
- **3.9 is not installed in the build container.** Compatibility is checked statically:
  `ast.parse(..., feature_version=(3, 9))`, a ban on runtime PEP 604 unions, a list of 3.10-only
  APIs, and portable-import checks. At run time the suite has passed on 3.11, 3.12 and 3.13 only.
  `feature_version` is best-effort, so static checks can miss a construct. The CI matrix with a
  real 3.9 (G-OFF-03) closes that gap, and a missing 3.9 interpreter counts as `not_run`, which
  blocks the merge.
- Some conveniences are unavailable: `tomllib`, structural pattern matching,
  `dataclass(slots=True)`, `zip(strict=True)` and `ExceptionGroup`.

### Residual risks

| Risk | Why it remains | Mitigation |
|---|---|---|
| A subtle validator bug lets an invalid document pass a gate | Hand-written code | Differential tests run wherever `jsonschema` is installed; schema invariants are also tested with crafted invalid documents |
| A 3.10+ construct passes the static checks and fails on 3.9 | `feature_version` is best-effort | G-OFF-03 runs the whole suite on a real 3.9 in CI |
| The user's `python3` is older than 3.9 | Some systems still ship older interpreters | `skill-lab doctor` fails `python` below 3.9; scripts are not guarded individually |

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Allow a few vetted packages (`jsonschema`, `pyyaml`, `requests`) | Needs pip and network at install time. Current `jsonschema` depends on `referencing` and `rpds-py`, a compiled Rust extension, so it cannot be vendored as pure Python |
| PEP 723 inline-dependency scripts run through `uv run` | Needs `uv` and network on first run; fails in offline sandboxes |
| Raise the floor to 3.11 (`tomllib`, `ExceptionGroup`) | Excludes the macOS system Python the user named |
| Compiled helpers (Go or Rust binaries) | Per-platform builds, unsigned binaries on macOS, and code models cannot read or patch in place |
| Node.js scripts | Not reliably present; the same dependency problem in another ecosystem |

## Compliance

| Rule | Verified by | State on 2026-10-22 |
|---|---|---|
| Skill scripts: 3.9 grammar, header, stdlib-only, portable imports | `scripts.syntax`, `scripts.shebang`, `scripts.docstring`, `scripts.future-import`, `scripts.executable`, `scripts.import-third-party`, `scripts.import-not-portable`; `test_lab_core_validate.py::TestScriptRules::test_python_310_syntax`, `test_lab_core_validate.py::TestScriptRules::test_module_missing_from_python_39`, `test_lab_core_validate.py::TestScriptRules::test_third_party_import` | enforced |
| Lab sources follow the same rules | `test_lab_core_sources.py::TestLabSources::test_python39_grammar_docstring_and_future_import`, `test_lab_core_sources.py::TestLabSources::test_imports_are_stdlib_lab_or_skillkit`, `test_lab_core_sources.py::TestLabSources::test_no_shell_eval_exec_or_runtime_unions` | enforced |
| `_skillkit` follows the same rules | `test_skillkit_package.py::TestSourceRules::test_python39_grammar`, `test_skillkit_package.py::TestSourceRules::test_no_runtime_pep604_unions`, `test_skillkit_package.py::TestSourceRules::test_no_python310_only_apis`, `test_skillkit_package.py::TestSourceRules::test_imports_are_portable_stdlib_or_relative` | enforced |
| The 3.9 module list is right and has a fallback | `test_skillkit_stdlib_modules.py::TestIsStdlib::test_fallback_without_stdlib_module_names`, `test_skillkit_stdlib_modules.py::TestIsStdlib::test_portable_requires_python39_and_current` | enforced |
| `jsonschema_mini` agrees with the reference validator | `test_contracts.py::TestDifferential::test_validity_agrees_on_every_instance`, `test_contracts.py::TestDifferential::test_keyword_level_agreement` | enforced when `jsonschema` is installed |
| The suite passes on a real Python 3.9 and on the current Python | G-OFF-03 and G-OFF-04 (CI matrix in `skill-lab/config/export/ci.yml`) | planned (SPEC-201 T118) |
| A user's interpreter is new enough | `skill-lab doctor` check `python` fails below 3.9; `test_lab_core_doctor.py::TestChecks::test_python_version_floor` | enforced |

**Revisit when** the user no longer needs macOS's system Python 3.9, or when a needed capability
cannot reasonably be written on the standard library.

## References

- [CONVENTIONS §3 Script contract](../CONVENTIONS.md#3-script-contract-v),
  [§9 Definition of done](../CONVENTIONS.md#9-definition-of-done-for-a-skill-v) (tests on 3.9 and current)
- [SPEC-100](../../specs/100-contracts-skillkit/spec.md), [SPEC-101](../../specs/101-lab-core/spec.md) FR-006, FR-027
- [SPEC-201 R1](../../specs/201-release-shadow/spec.md) gates G-OFF-03, G-OFF-04
- ADR-0001 (vendoring), ADR-0004 (keyword subset)
