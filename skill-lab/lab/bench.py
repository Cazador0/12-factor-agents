"""``skill-lab bench``: run benchmark cases and write graded results (SPEC-102).

Reads every ``skills/<name>/evals/cases/*.json`` (``benchmark-case.v1``),
runs the selected cases, grades them with ``lab.graders``, writes one
``benchmark-result.v1`` per case plus a ``benchmark-run.v1`` summary, and
prints the run as an ``envelope.v1``.

* deterministic: the case's script runs with ``sys.executable``, cwd = the
  skill folder, a minimal environment plus the case's ``env``, stdin from
  ``stdin_file`` and a 60 s timeout. ``{tmp}`` in args or env becomes a fresh
  per-case temporary directory (use it for ``--state-dir`` so a case never
  writes into the skill folder).
* agentic: a model runtime gets the skill the way Zed presents it
  (``lab.runtimes.zed_emulation``) and must answer with JSON for
  ``output_schema``; Jev judges the answer.
* trigger: the query is routed across the whole catalog, by a Jev choice
  question (``--router jev``) or by the model runtime (``--router runtime``);
  ``auto`` prefers Jev when it is available.

Nothing is ever fabricated: when a runtime or Jev is unavailable the case is
``skipped`` with a reason (prefixed ``LIVE_PREREQ_MISSING``), and replays come
only from cassettes a live run recorded (``--record``, ``--cassettes``).
Exit codes: 0 every graded case passed, 1 a case failed or errored or a case
file is invalid, 2 usage, 4 an output path inside ``skills/``.
"""

from __future__ import annotations

import datetime as _dt
import os
import platform
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Dict, List, Mapping, NamedTuple, Optional, Sequence, Tuple

from _skillkit import EXIT_FAIL, EXIT_OK, EXIT_USAGE, cli, envelope, fsutil, ids, schemas
from _skillkit.envelope import ScriptError, ScriptResult
from _skillkit.jsonschema_mini import validate
from _skillkit.redact import redact

from . import LAB_VERSION, graders, paths
from . import cli as labcli
from . import jev as jevlib
from .cassette import Cassette, CassetteError, CassetteMiss, CassetteTransport
from .runtimes import (
    LIVE_PREREQ_MISSING,
    RUNTIME_ALIASES,
    RUNTIME_NAMES,
    Runtime,
    RuntimeCallError,
    canonical_name,
    create_runtime,
    zed_emulation,
)
from .runtimes.ollama_cloud import DEFAULT_MAX_REPAIRS
from .runtimes.ollama_local import DEFAULT_NUM_CTX
from .runtimes.replay import RecordingRuntime
from .runtimes.transport import NO_RETRY, Transport, urllib_transport

SCHEMA_DIRS = (os.path.join(paths.LAB_ROOT, "contracts", "schemas"),)
"""Results are always graded against the lab's canonical contracts."""
DEFAULT_RUNS_DIR = os.path.join("benchmarks", "runs")
DETERMINISTIC_TIMEOUT = 60.0
MODEL_TIMEOUT = 300.0
JEV_PROBE_TIMEOUT = 5.0
MAX_FIXTURE_BYTES = 64 * 1024
TMP_PLACEHOLDER = "{tmp}"
ALL_TIERS = graders.TIERS
JEV_ROUTER_LABEL = "jev-choice"
ROUTING_QUESTION_ID = "routing"
ROUTING_INSTRUCTION = (
    "Do not carry out this request. Answer only which skill from <available_skills> you would load with the "
    '`skill` tool to handle it, as {"skill": "<name>"}, or {"skill": "none"} when no installed skill fits.'
)
_ENV_PASSTHROUGH = ("PATH", "SYSTEMROOT", "LANG", "LC_ALL")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for ``skill-lab bench``; prints one envelope and returns the exit code."""
    argv = list(sys.argv[1:] if argv is None else argv)
    return labcli.run_command(lambda: run(argv), command="bench", kind="benchmark-run", argv=argv)


def build_parser() -> cli.SkillArgumentParser:
    parser = labcli.command_parser("bench", "Run benchmark cases and grade them.")
    parser.add_argument("--skill", action="append", metavar="NAME", help="skill to run (repeatable; default all)")
    parser.add_argument(
        "--tier",
        action="append",
        metavar="TIER",
        help="deterministic, agentic, trigger or all; repeatable or comma-separated (default deterministic)",
    )
    parser.add_argument("--tag", action="append", metavar="TAG", help="only cases carrying every given tag")
    parser.add_argument("--runtime", choices=RUNTIME_NAMES + tuple(sorted(RUNTIME_ALIASES)), help="model runtime")
    parser.add_argument("--model", help="model name for the runtime (e.g. qwen3:14b)")
    parser.add_argument(
        "--num-ctx", type=_positive_int, default=DEFAULT_NUM_CTX, help="ollama-local context (default %(default)s)"
    )
    parser.add_argument(
        "--max-repairs",
        type=_non_negative_int,
        default=DEFAULT_MAX_REPAIRS,
        help="ollama-cloud repair turns (default %(default)s)",
    )
    parser.add_argument(
        "--jev", choices=("live", "replay", "off"), help="default: live when a key is set and the API answers, else off"
    )
    parser.add_argument(
        "--router", choices=("auto", "jev", "runtime"), default="auto", help="how trigger cases are routed"
    )
    parser.add_argument("--record", metavar="DIR", help="record live Jev and runtime exchanges into this cassette")
    parser.add_argument("--cassettes", metavar="DIR", help="cassette to replay from (--jev replay, --runtime replay)")
    parser.add_argument("--out", metavar="DIR", help="output folder (default skill-lab/benchmarks/runs/<run_id>)")
    return parser


def run(argv: Sequence[str], *, environ: Optional[Mapping[str, str]] = None) -> ScriptResult:
    """Parse ``argv``, run the cases, write the results and return the envelope content.

    ``environ`` (default ``os.environ``) supplies the runtime and Jev settings, so tests can point
    them at local fake servers.
    """
    environ = os.environ if environ is None else environ
    args = build_parser().parse_args(list(argv))
    now = cli.parse_now(args.now)
    layout = labcli.layout_from(args)
    tiers = parse_tiers(args.tier)
    tags = paths.split_csv(args.tag)
    requested = paths.split_csv(args.skill)
    selected = select_skills(layout, requested)
    cases, errors = load_cases(layout, selected, tiers, tags)

    run_id = make_run_id(now, argv)
    out_dir = os.path.abspath(args.out) if args.out else os.path.join(layout.lab_root, DEFAULT_RUNS_DIR, run_id)
    fsutil.ensure_not_inside(out_dir, layout.skills_dir)
    aliases = {layout.repo_root: "<repo>"}
    record = _cassette(args.record, aliases, layout)
    replay = _cassette(args.cassettes, aliases, layout)
    bench = Bench(
        layout=layout,
        args=args,
        started=now,
        environ=environ,
        record=record,
        replay=replay,
    )
    results = [bench.run_case(skill, case) for skill, case, _ in cases]
    for result in results:
        _check_contract("benchmark-result", result)

    run_doc = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at": cli.to_iso(now),
        "finished_at": cli.to_iso(now if args.now else cli.parse_now(None)),
        "runtime": canonical_name(args.runtime) if args.runtime else "script",
        "model": args.model,
        "jev_mode": bench.jev_mode_used(),
        "filters": {
            "skill": requested[0] if len(requested) == 1 else None,
            "tier": tiers[0] if len(tiers) == 1 else None,
        },
        "environment": {"python": platform.python_version(), "platform": sys.platform},
        "lab_version": LAB_VERSION,
        "results": results,
        "summary": graders.summarize(results),
        "notes": run_notes(layout, cases, bench, tags),
    }
    _check_contract("benchmark-run", run_doc)
    write_run(out_dir, run_doc)
    failed = any(result["status"] in ("fail", "error") for result in results)
    exit_code = EXIT_FAIL if failed or errors else EXIT_OK
    return ScriptResult(exit_code, run_doc, labcli.capped(errors), labcli.capped(skip_warnings(results, bool(cases))))


# ---------------------------------------------------------------------------
# Selecting cases
# ---------------------------------------------------------------------------


def parse_tiers(values: Optional[Sequence[str]]) -> List[str]:
    """``--tier`` values (repeatable, comma-separated, ``all``) as an ordered tier list."""
    requested = paths.split_csv(values) or ["deterministic"]
    unknown = [tier for tier in requested if tier not in ALL_TIERS + ("all",)]
    if unknown:
        raise ScriptError("USAGE", "unknown tier %s (use deterministic, agentic, trigger or all)" % ", ".join(unknown))
    if "all" in requested:
        return list(ALL_TIERS)
    return [tier for tier in ALL_TIERS if tier in requested]


def select_skills(layout: paths.Layout, requested: Sequence[str]) -> List[str]:
    available = paths.skill_names(layout)
    missing = [name for name in requested if name not in available]
    if missing:
        raise ScriptError(
            "SKILL_NOT_FOUND",
            "no skill folder with SKILL.md for %s" % ", ".join(missing),
            path=layout.rel(layout.skills_dir),
        )
    return list(requested) if requested else available


def load_cases(
    layout: paths.Layout, skill_names: Sequence[str], tiers: Sequence[str], tags: Sequence[str]
) -> Tuple[List[Tuple[str, Dict[str, Any], str]], List[Dict[str, Any]]]:
    """``([(skill, case, relative path)], errors)``: valid selected cases and every invalid case file."""
    case_schema = schemas.load_schema("benchmark-case", SCHEMA_DIRS)
    cases, errors = [], []
    for name in skill_names:
        for path in paths.case_files(layout.skill_dir(name)):
            rel = layout.rel(path)
            try:
                case = cli.read_json(path)
            except ScriptError as exc:
                errors.append(envelope.error("CASE_INVALID", exc.message, (exc.path or path).replace(path, rel)))
                continue
            problem = case_problem(case, case_schema, name, os.path.basename(path)[: -len(".json")])
            if problem:
                errors.append(envelope.error("CASE_INVALID", problem, rel))
            elif case["tier"] in tiers and set(tags) <= set(case.get("tags", ())):
                cases.append((name, case, rel))
    return cases, errors


def case_problem(case: Any, case_schema: Any, skill: str, stem: str) -> Optional[str]:
    """Why a case document cannot run, or None."""
    issues = validate(case, case_schema)
    if issues:
        return "%s: %s" % (issues[0].path or "/", issues[0].message)
    if case["id"] != stem:
        return "id %r must equal the file name %r" % (case["id"], stem)
    if case["skill"] != skill:
        return "skill %r must equal the folder name %r" % (case["skill"], skill)
    for judgment in case.get("judgments", ()):
        if judgment["type"] == "choice" and judgment["pass_if"]["eq"] not in judgment["criteria"]:
            return "judgment %s passes on %r, which is not one of its labels" % (
                judgment["id"],
                judgment["pass_if"]["eq"],
            )
    return None


def make_run_id(now: _dt.datetime, argv: Sequence[str]) -> str:
    """``run-<UTC stamp>-<8 hex of the arguments>``: the same ``--now`` and arguments give the same ID."""
    stable = [arg for arg in argv if arg != "--pretty"]
    return "run-%s-%s" % (now.strftime("%Y%m%dT%H%M%SZ"), ids.digest(stable)[len("sha256:") :][:8])


# ---------------------------------------------------------------------------
# Running cases
# ---------------------------------------------------------------------------


class JevSetup(NamedTuple):
    mode: str
    """``live``, ``replay`` or ``off``."""
    client: Optional[jevlib.JevClient]
    reason: str


class Bench:
    """Runs cases; the runtime and Jev are resolved lazily, once, and only when a case needs them."""

    def __init__(
        self,
        *,
        layout: paths.Layout,
        args: Any,
        started: _dt.datetime,
        environ: Mapping[str, str],
        record: Optional[Cassette],
        replay: Optional[Cassette],
    ) -> None:
        self.layout = layout
        self.args = args
        self.started = cli.to_iso(started)
        self.environ = environ
        self.record = record
        self.replay = replay
        self.installed = zed_emulation.discover(layout.skills_dir)
        self.worktree = os.path.basename(layout.repo_root)
        self._runtime: Optional[Tuple[Optional[Runtime], str]] = None
        self._jev: Optional[JevSetup] = None
        self.jev_calls = 0
        self.runtime_used = False

    # -- shared services ----------------------------------------------------

    def runtime(self) -> Tuple[Optional[Runtime], str]:
        if self._runtime is None:
            self._runtime = self._resolve_runtime()
        return self._runtime

    def jev(self) -> JevSetup:
        if self._jev is None:
            self._jev = self._resolve_jev()
        return self._jev

    def jev_mode_used(self) -> str:
        return self.jev().mode if self.jev_calls else "off"

    def service_reasons(self) -> List[str]:
        """Why a runtime or Jev that cases asked for could not be used (only services that were resolved)."""
        reasons = []
        if self._runtime is not None and self._runtime[0] is None:
            reasons.append("runtime unavailable: " + self._runtime[1])
        if self._jev is not None:
            reasons.append("jev: " + self._jev.reason)
        return reasons

    def _resolve_runtime(self) -> Tuple[Optional[Runtime], str]:
        args = self.args
        if args.runtime is None:
            return None, "%s: no --runtime given" % LIVE_PREREQ_MISSING
        name = canonical_name(args.runtime)
        if name == "replay" and self.replay is None:
            raise ScriptError("USAGE", "--runtime replay needs --cassettes DIR")
        runtime = create_runtime(
            name,
            model=args.model,
            num_ctx=args.num_ctx,
            max_repairs=args.max_repairs,
            cassette=self.replay,
            environ=self.environ,
        )
        ok, reason = runtime.available()
        if not ok:
            return None, reason
        if self.record is not None and name != "replay":
            runtime = RecordingRuntime(runtime, self.record, recorded_at=self.started)
        return runtime, "ok"

    def _resolve_jev(self) -> JevSetup:
        requested = self.args.jev
        if requested == "off":
            return JevSetup("off", None, "Jev disabled with --jev off")
        if requested == "replay":
            if self.replay is None:
                raise ScriptError("USAGE", "--jev replay needs --cassettes DIR")
            transport = CassetteTransport(self.replay, mode="replay")
            client = jevlib.JevClient(None, transport=transport, **jevlib.settings_from_env(self.environ))
            return JevSetup("replay", client, "Jev answers replayed from %s" % self.layout.rel(self.replay.root))
        try:
            probe = jevlib.JevClient.from_env(self.environ, log=None)
            probe.list_models(timeout=JEV_PROBE_TIMEOUT, retry=NO_RETRY)
        except jevlib.JevError as exc:
            return JevSetup(
                "off", None, "%s: Jev is not usable (%s: %s)" % (LIVE_PREREQ_MISSING, exc.code, exc.message)
            )
        transport: Transport = urllib_transport
        if self.record is not None:
            transport = CassetteTransport(self.record, mode="record", inner=transport, recorded_at=self.started)
        return JevSetup(
            "live", jevlib.JevClient.from_env(self.environ, transport=transport), "live Jev at %s" % probe.base_url
        )

    # -- cases --------------------------------------------------------------

    def run_case(self, skill: str, case: Dict[str, Any]) -> Dict[str, Any]:
        runner = {"deterministic": self._deterministic, "agentic": self._agentic, "trigger": self._trigger}[
            case["tier"]
        ]
        result = {
            "schema_version": 1,
            "case_id": case["id"],
            "skill": skill,
            "tier": case["tier"],
            "runtime": "script",
            "model": None,
            "status": "error",
            "assertions": [],
            "judgments": [],
            "duration_ms": 0,
            "jev_mode": "off",
            "notes": [],
            "started_at": self.started,
        }
        clock = time.monotonic()
        runner(case, result)
        result["duration_ms"] = int((time.monotonic() - clock) * 1000)
        return result

    def _deterministic(self, case: Dict[str, Any], result: Dict[str, Any]) -> None:
        skill_dir = self.layout.skill_dir(case["skill"])
        spec = case["run"]
        try:
            script = fsutil.safe_join(skill_dir, *spec["script"].split("/"))
            stdin_path = fsutil.safe_join(skill_dir, *spec["stdin_file"].split("/")) if "stdin_file" in spec else None
        except ScriptError as exc:
            return _error(result, "CASE_INVALID", exc.message)
        if not os.path.isfile(script):
            return _error(result, "SCRIPT_NOT_FOUND", "%s does not exist" % spec["script"])
        if stdin_path is not None and not os.path.isfile(stdin_path):
            return _error(result, "CASE_INVALID", "stdin_file %s does not exist" % spec["stdin_file"])
        timeout = case.get("timeout_s", DETERMINISTIC_TIMEOUT)
        with tempfile.TemporaryDirectory(prefix="skill-lab-case-") as tmp:
            argv = [sys.executable, script] + [arg.replace(TMP_PLACEHOLDER, tmp) for arg in spec["args"]]
            env = case_environment(spec.get("env", {}), tmp)
            try:
                completed = _run_script(argv, skill_dir, env, stdin_path, timeout)
            except subprocess.TimeoutExpired:
                return _error(result, "TIMEOUT", "script did not finish within %.0fs" % timeout)
            except OSError as exc:
                return _error(result, "SCRIPT_NOT_RUNNABLE", str(exc))
        grade = graders.grade_deterministic(
            case["expect"], completed.returncode, completed.stdout.decode("utf-8", "replace"), schema_dirs=SCHEMA_DIRS
        )
        result.update(exit_code=completed.returncode)
        _apply(result, grade)
        stderr = completed.stderr.decode("utf-8", "replace").strip()
        if grade.status != "pass" and stderr:
            result["notes"].append(graders.note("stderr: " + stderr.splitlines()[-1]))

    def _agentic(self, case: Dict[str, Any], result: Dict[str, Any]) -> None:
        runtime, reason = self.runtime()
        result.update(runtime=self._label(runtime), model=self.args.model)
        if runtime is None:
            return _skip(result, reason)
        skill = self._installed(case["skill"])
        if skill is None:
            return _error(result, "SKILL_NOT_LOADABLE", "SKILL.md has no usable name and description")
        try:
            schema = _output_schema(case["output_schema"])
            fixture_text, fixture_state = load_fixtures(skill.directory, case["fixtures"])
        except ScriptError as exc:
            return _error(result, exc.code, exc.message)
        system = zed_emulation.system_prompt(self.installed)
        user = zed_emulation.user_prompt(skill, case["prompt"], fixtures=fixture_text, worktree=self.worktree)
        reply = self._call_runtime(runtime, system, user, schema, case.get("timeout_s", MODEL_TIMEOUT), result)
        if reply is None:
            return None
        grade = graders.grade_output(case["expect"], reply.json_or_none, schema)
        _apply(result, grade)
        if grade.status != "pass" or not case["judgments"]:
            if case["judgments"] and grade.status == "fail":
                result["notes"].append("judgments not asked: the output failed its deterministic checks")
            return None
        jev = self.jev()
        if jev.mode == "off":
            return _skip(result, graders.note("%s; %d judgments not graded" % (jev.reason, len(case["judgments"]))))
        skill_state = {"name": skill.name, "description": skill.description, "instructions": skill.body}

        def state_for(state_from: Sequence[str]) -> Dict[str, Any]:
            return jevlib.build_state(
                state_from, skill=skill_state, prompt=case["prompt"], fixtures=fixture_state, output=reply.json_or_none
            )

        judged = self._ask_judgments(case["judgments"], state_for, result)
        if judged is not None:
            result["judgments"] = judged
            result["status"] = "pass" if all(item["pass"] for item in judged) else "fail"
            uncertain = [item["id"] for item in judged if item["band"] == "uncertain"]
            if uncertain:
                result["notes"].append(graders.note("needs human review (uncertain): %s" % ", ".join(uncertain)))
        return None

    def _trigger(self, case: Dict[str, Any], result: Dict[str, Any]) -> None:
        catalog = [(skill.name, skill.description) for skill in zed_emulation.catalog_skills(self.installed)]
        names = [name for name, _ in catalog]
        expected = case["expect_skill"]
        if expected is not None and expected not in names:
            result["runtime"] = "none"
            return _error(
                result, "CASE_INVALID", "expect_skill %s is not an installed, model-invocable skill" % expected
            )
        method, service, reason = self._router()
        if method == "jev":
            return self._route_with_jev(case, result, service, catalog)
        if method == "runtime":
            return self._route_with_runtime(case, result, service, names)
        result["runtime"] = self._label(None)
        return _skip(result, reason)

    # -- helpers ------------------------------------------------------------

    def _router(self) -> Tuple[Optional[str], Any, str]:
        preference = self.args.router
        jev_reason = ""
        if preference in ("auto", "jev"):
            jev = self.jev()
            if jev.mode != "off":
                return "jev", jev, ""
            jev_reason = jev.reason
            if preference == "jev":
                return None, None, jev_reason
        runtime, runtime_reason = self.runtime()
        if runtime is not None:
            return "runtime", runtime, ""
        return None, None, graders.note("; ".join(part for part in (jev_reason, runtime_reason) if part))

    def _route_with_jev(
        self, case: Dict[str, Any], result: Dict[str, Any], jev: JevSetup, catalog: List[Tuple[str, str]]
    ) -> None:
        result["runtime"] = JEV_ROUTER_LABEL
        try:
            question = jevlib.routing_question(catalog)
        except jevlib.JevConfigError as exc:
            return _error(result, exc.code, exc.message)
        reply = self._ask(jev, result, case["query"], {ROUTING_QUESTION_ID: question})
        if reply is None:
            return None
        answer = reply.answers[ROUTING_QUESTION_ID]
        result["model"] = reply.model
        routed = graders.routed_skill(answer.choice, jevlib.NONE_LABEL)
        passed = routed == case["expect_skill"]
        result.update(
            routed_skill=routed,
            status="pass" if passed else "fail",
            judgments=[
                {
                    "id": ROUTING_QUESTION_ID,
                    "type": "choice",
                    "value": answer.choice,
                    "confidence": answer.confidence,
                    "pass": passed,
                    "band": "pass" if passed else "fail",
                    "needs_human": False,
                    "request_id": reply.request_id,
                }
            ],
        )
        probabilities = graders.top_probabilities(answer.probabilities)
        result["notes"].extend(["routing_method=jev-choice", graders.note("probabilities: " + probabilities)])
        return None

    def _route_with_runtime(
        self, case: Dict[str, Any], result: Dict[str, Any], runtime: Runtime, names: List[str]
    ) -> None:
        result.update(runtime=self._label(runtime), model=self.args.model)
        schema = routing_schema(names)
        system = zed_emulation.system_prompt(self.installed)
        user = case["query"] + "\n\n" + ROUTING_INSTRUCTION
        reply = self._call_runtime(runtime, system, user, schema, MODEL_TIMEOUT, result)
        if reply is None:
            return None
        result["notes"].append("routing_method=runtime")
        data = reply.json_or_none
        if data is None or validate(data, schema):
            result["status"] = "fail"
            result["notes"].append(graders.note("routing reply is not a valid choice: %s" % reply.text))
            return None
        routed = graders.routed_skill(data["skill"], jevlib.NONE_LABEL)
        result.update(routed_skill=routed, status="pass" if routed == case["expect_skill"] else "fail")
        return None

    def _call_runtime(
        self, runtime: Runtime, system: str, user: str, schema: dict, timeout: float, result: Dict[str, Any]
    ) -> Any:
        """One runtime turn; on failure the result is marked and None is returned."""
        self.runtime_used = True
        try:
            reply = runtime.run(system, user, schema, timeout=timeout)
        except RuntimeCallError as exc:
            return _error(result, exc.code, exc.message)
        except CassetteMiss:
            return _skip(result, "CASSETTE_MISS: this model turn was not recorded in the cassette")
        except CassetteError as exc:
            return _error(result, "CASSETTE_INVALID", str(exc))
        result["notes"].extend(runtime_notes(reply.raw_meta, reply.usage))
        return reply

    def _ask_judgments(
        self, judgments: Sequence[Mapping[str, Any]], state_for: Callable[[Sequence[str]], Any], result: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """Grade every judgment, one Jev request per distinct ``state_from``; None when a request failed."""
        jev = self.jev()
        graded: Dict[str, Dict[str, Any]] = {}
        for state_from, group in jevlib.judgment_batches(judgments):
            questions = {judgment["id"]: jevlib.question_for(judgment) for judgment in group}
            reply = self._ask(jev, result, state_for(state_from), questions)
            if reply is None:
                return None
            for judgment in group:
                answer = reply.answers[judgment["id"]]
                graded[judgment["id"]] = graders.grade_judgment(judgment, answer, reply.request_id)
        return [graded[judgment["id"]] for judgment in judgments]

    def _ask(self, jev: JevSetup, result: Dict[str, Any], state: Any, questions: Dict[str, Any]) -> Any:
        """One Jev request; on failure the result is marked and None is returned."""
        self.jev_calls += 1
        result["jev_mode"] = jev.mode
        try:
            reply = jev.client.ask(state, questions)
        except CassetteMiss:
            result["jev_mode"] = "off"
            return _skip(result, "CASSETTE_MISS: this Jev request was not recorded in the cassette")
        except CassetteError as exc:
            result["jev_mode"] = "off"
            return _error(result, "CASSETTE_INVALID", str(exc))
        except jevlib.JevError as exc:
            result["jev_mode"] = "off"
            return _error(result, exc.code, exc.message)
        usage = reply.usage
        result["notes"].append(
            "jev: model=%s tokens in=%d out=%d" % (reply.model, usage.input_tokens, usage.output_tokens)
        )
        return reply

    def _installed(self, name: str) -> Optional[zed_emulation.InstalledSkill]:
        return next((skill for skill in self.installed if skill.name == name), None)

    def _label(self, runtime: Optional[Runtime]) -> str:
        if runtime is not None:
            return zed_emulation.runtime_label(runtime.name)
        return canonical_name(self.args.runtime) if self.args.runtime else "none"


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


def case_environment(extra: Mapping[str, str], tmp: str) -> Dict[str, str]:
    """A minimal, deterministic environment: no secrets, HOME and TMPDIR in the case's temporary folder."""
    env = {name: os.environ[name] for name in _ENV_PASSTHROUGH if name in os.environ}
    env.update(
        {
            "HOME": tmp,
            "TMPDIR": tmp,
            "TEMP": tmp,
            "TMP": tmp,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    env.update({name: value.replace(TMP_PLACEHOLDER, tmp) for name, value in extra.items()})
    return env


def load_fixtures(skill_dir: str, fixtures: Sequence[str]) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """``(text by path, Jev state by path)``; JSON fixtures are parsed for the state."""
    texts: Dict[str, str] = {}
    state: Dict[str, Any] = {}
    for rel in fixtures:
        path = fsutil.safe_join(skill_dir, *rel.split("/"))
        if not os.path.isfile(path):
            raise ScriptError("FIXTURE_NOT_FOUND", "fixture %s does not exist" % rel, path=rel)
        if os.path.getsize(path) > MAX_FIXTURE_BYTES:
            raise ScriptError("FIXTURE_TOO_LARGE", "fixture %s exceeds %d bytes" % (rel, MAX_FIXTURE_BYTES), path=rel)
        text = cli.read_text(path)
        texts[rel] = text
        try:
            state[rel] = cli.loads_strict(text) if rel.endswith(".json") else text
        except ValueError:
            state[rel] = text
    return texts, state


def routing_schema(names: Sequence[str]) -> Dict[str, Any]:
    """The JSON a runtime router must return: one catalog skill name or ``none``."""
    return {
        "type": "object",
        "required": ["skill"],
        "properties": {"skill": {"enum": list(names) + [jevlib.NONE_LABEL]}},
        "additionalProperties": False,
    }


def runtime_notes(meta: Mapping[str, Any], usage: Mapping[str, int]) -> List[str]:
    """Compact facts about one runtime turn (repairs, extraction mode, tokens)."""
    facts = ["%s=%s" % (key, meta[key]) for key in sorted(meta) if key != "validation_errors" and meta[key] is not None]
    notes = [graders.note("runtime: " + " ".join(facts))] if facts else []
    if usage:
        notes.append("tokens: in=%s out=%s" % (usage.get("input_tokens", "?"), usage.get("output_tokens", "?")))
    for problem in (meta.get("validation_errors") or [])[:2]:
        notes.append(graders.note("last reply invalid: " + problem))
    return notes


def run_notes(
    layout: paths.Layout, cases: Sequence[Tuple[str, Dict[str, Any], str]], bench: Bench, tags: Sequence[str]
) -> List[str]:
    """Run-level facts: suite digest, commit, num_ctx, tags, and why the runtime or Jev was not used.

    ``suite_digest=``, ``commit=`` and ``num_ctx=`` are strict ``key=value`` lines
    other tools parse (SPEC-202 D-17 fallback).
    """
    notes = ["suite_digest=%s" % suite_digest(layout, cases)]
    commit = git_commit(layout.repo_root)
    if commit:
        notes.append("commit=%s" % commit)
    if bench.runtime_used and canonical_name(bench.args.runtime) == "ollama-local":
        notes.append("num_ctx=%d" % bench.args.num_ctx)
    if tags:
        notes.append(graders.note("tags=%s" % ",".join(tags)))
    notes.extend(graders.note(reason) for reason in bench.service_reasons())
    return notes


def suite_digest(layout: paths.Layout, cases: Sequence[Tuple[str, Dict[str, Any], str]]) -> str:
    """Digest of the selected case files and the SKILL.md of every skill they belong to."""
    skill_files = {layout.rel(os.path.join(layout.skill_dir(skill), paths.SKILL_FILE)) for skill, _, _ in cases}
    files = sorted({rel for _, _, rel in cases} | skill_files)
    return ids.digest([[rel, ids.digest_file(os.path.join(layout.repo_root, *rel.split("/")))] for rel in files])


def git_commit(repo_root: str) -> Optional[str]:
    """``HEAD`` of the repository, or None when git or the repository is unavailable."""
    try:
        completed = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    commit = completed.stdout.strip()
    return commit if completed.returncode == 0 and len(commit) in (40, 64) else None


def skip_warnings(results: Sequence[Mapping[str, Any]], had_cases: bool) -> List[Dict[str, Any]]:
    """One ``CASES_SKIPPED`` warning per distinct reason, or ``NO_CASES`` when nothing was selected."""
    if not had_cases:
        return [envelope.error("NO_CASES", "no benchmark case matched the filters")]
    reasons: Dict[str, int] = {}
    for result in results:
        if result["status"] == "skipped":
            reasons[result["skip_reason"]] = reasons.get(result["skip_reason"], 0) + 1
    return [
        envelope.error("CASES_SKIPPED", "%d skipped: %s" % (count, reason)) for reason, count in sorted(reasons.items())
    ]


def write_run(out_dir: str, run_doc: Dict[str, Any]) -> None:
    """``<out>/results/<skill>/<case_id>.json`` per result and ``<out>/benchmark-run.json``, redacted."""
    for result in run_doc["results"]:
        path = os.path.join(out_dir, "results", result["skill"], result["case_id"] + ".json")
        fsutil.atomic_write_json(path, redact(result))
    fsutil.atomic_write_json(os.path.join(out_dir, "benchmark-run.json"), redact(run_doc))


def _run_script(argv: List[str], cwd: str, env: Dict[str, str], stdin_path: Optional[str], timeout: float) -> Any:
    if stdin_path is None:
        return subprocess.run(
            argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, check=False
        )
    with open(stdin_path, "rb") as stdin:
        return subprocess.run(argv, cwd=cwd, env=env, stdin=stdin, capture_output=True, timeout=timeout, check=False)


def _output_schema(urn: str) -> Dict[str, Any]:
    name, version = schemas.parse_urn(urn)
    return schemas.load_schema(name, SCHEMA_DIRS, version)


def _cassette(directory: Optional[str], aliases: Dict[str, str], layout: paths.Layout) -> Optional[Cassette]:
    if not directory:
        return None
    root = os.path.abspath(directory)
    fsutil.ensure_not_inside(root, layout.skills_dir)
    return Cassette(root, aliases=aliases)


def _check_contract(name: str, document: Dict[str, Any]) -> None:
    """Refuse to write a document that breaks its own contract (a lab bug, never a skill failure)."""
    issues = schemas.validate_payload(name, document, SCHEMA_DIRS)
    if issues:
        first = issues[0]
        message = "%s document invalid at %s: %s" % (name, first.path or "/", first.message)
        raise ScriptError("RESULT_INVALID", message, exit_code=EXIT_USAGE)


def _apply(result: Dict[str, Any], grade: graders.Grade) -> None:
    result.update(status=grade.status, schema_valid=grade.schema_valid, assertions=grade.assertions)
    result["notes"].extend(grade.notes)
    if grade.error is not None:
        result["error"] = grade.error


def _error(result: Dict[str, Any], code: str, message: str) -> None:
    result.update(status="error", error={"code": code, "message": envelope.compact(message, 300)})
    return None


def _skip(result: Dict[str, Any], reason: str) -> None:
    result.update(status="skipped", skip_reason=graders.note(reason))
    return None


def _positive_int(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise ValueError("must be positive")
    return value


def _non_negative_int(text: str) -> int:
    value = int(text)
    if value < 0:
        raise ValueError("must not be negative")
    return value


if __name__ == "__main__":
    sys.exit(main())
