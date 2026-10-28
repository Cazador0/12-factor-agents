"""skill-lab doctor: report whether this machine can build, run and benchmark skills.

Checks, each ``ok``, ``warn`` or ``fail``:

- ``python``          the running interpreter is >= 3.9 (fail otherwise);
- ``git``             git is on PATH (warn when absent);
- ``layout.*``        skills/, the canonical _skillkit, the contracts and the
                      scaffold template exist (fail when absent);
- ``skills``          how many skills were found (warn when none);
- ``install.*``       install parity per discovery folder (warn on drift);
- ``env.*``           whether TYPESAFE_API_KEY or JEV_API_KEY, OLLAMA_API_KEY,
                      GITEA_URL and GITEA_TOKEN are set. Values are never read
                      into the report, only their presence;
- ``probe.*``         reachability with a 5 s timeout: the Jev API
                      (``/v1/models``, 200 or 401 means reachable), Ollama Cloud
                      (``/api/tags``), local Ollama (``localhost:11434``), and Gitea
                      (``$GITEA_URL/api/v1/version``) when configured.

Probes send no credentials and never fail the run: an unreachable endpoint is
a ``warn`` (this container may block the network). Exit 1 only when a check
fails. ``--offline`` skips the probes.
"""

from __future__ import annotations

import concurrent.futures
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Mapping, NamedTuple, Optional, Sequence, Tuple

from . import LAB_VERSION
from . import cli as labcli
from . import install, paths
from _skillkit import EXIT_FAIL, EXIT_OK
from _skillkit.envelope import ScriptResult, compact

OK, WARN, FAIL = "ok", "warn", "fail"
PROBE_TIMEOUT_S = 5.0
TYPESAFE_MODELS_URL = "https://api.typesafe.ai/v1/models"
OLLAMA_CLOUD_TAGS_URL = "https://ollama.com/api/tags"
OLLAMA_LOCAL_TAGS_URL = "http://localhost:11434/api/tags"
ENV_CHECKS = (
    ("env.typesafe-key", ("TYPESAFE_API_KEY", "JEV_API_KEY"), "live Jev grading"),
    ("env.ollama-key", ("OLLAMA_API_KEY",), "Ollama Cloud models"),
    ("env.gitea-url", ("GITEA_URL",), "a live Gitea; the test double needs none"),
    ("env.gitea-token", ("GITEA_TOKEN",), "Gitea writes"),
)

PAYLOAD_SCHEMA: Dict[str, Any] = {
    "description": "lab-doctor payload: one entry per check.",
    "type": "object",
    "required": ["schema_version", "ok", "checks", "summary"],
    "properties": {
        "schema_version": {"const": 1},
        "ok": {"description": "False only when a check failed.", "type": "boolean"},
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "status", "message"],
                "properties": {
                    "id": {"type": "string", "pattern": "^[a-z0-9]+([._-][a-z0-9]+)*$"},
                    "status": {"enum": [OK, WARN, FAIL]},
                    "message": {"type": "string", "maxLength": 300},
                },
                "additionalProperties": False,
            },
        },
        "summary": {
            "type": "object",
            "required": [OK, WARN, FAIL],
            "properties": {key: {"type": "integer", "minimum": 0} for key in (OK, WARN, FAIL)},
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}


class Check(NamedTuple):
    id: str
    status: str
    message: str


class ProbeResult(NamedTuple):
    """HTTP status of a GET, or None with the reason when no response arrived."""

    status: Optional[int]
    reason: Optional[str] = None


Probe = Callable[[str, float], ProbeResult]


def http_probe(url: str, timeout: float) -> ProbeResult:
    """GET ``url`` without credentials; never raises."""
    try:
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": "skill-lab-doctor/%s" % LAB_VERSION})
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https/http URLs
            return ProbeResult(response.status)
    except urllib.error.HTTPError as exc:
        return ProbeResult(exc.code)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        reason = getattr(exc, "reason", None) or exc
        return ProbeResult(None, compact(reason, 120))


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def toolchain_checks(version: Tuple[int, ...], which: Callable[[str], Optional[str]]) -> List[Check]:
    text = ".".join(str(part) for part in version[:3])
    python = (
        Check("python", OK, "Python %s (>= 3.9 required)" % text)
        if tuple(version[:2]) >= (3, 9)
        else Check("python", FAIL, "Python %s is too old; skills need >= 3.9" % text)
    )
    git = which("git")
    return [python, Check("git", OK, "git is on PATH") if git else Check("git", WARN, "git not found on PATH")]


def layout_checks(layout: paths.Layout) -> List[Check]:
    required = (
        ("layout.skills", layout.skills_dir, "skills/"),
        ("layout.skillkit", os.path.join(layout.skillkit_dir, "__init__.py"), "canonical _skillkit"),
        ("layout.contracts", os.path.join(layout.schemas_dir, "envelope.v1.schema.json"), "canonical contracts"),
        ("layout.templates", os.path.join(layout.templates_dir, "SKILL.md.tmpl"), "scaffold template"),
    )
    checks = [
        Check(check_id, OK, "%s present (%s)" % (label, layout.rel(path)))
        if os.path.exists(path)
        else Check(check_id, FAIL, "%s missing (%s)" % (label, layout.rel(path)))
        for check_id, path, label in required
    ]
    names = paths.skill_names(layout)
    checks.append(
        Check("skills", OK, "%d skill(s) under skills/" % len(names))
        if names
        else Check("skills", WARN, "no skills under skills/ yet")
    )
    checks.extend(_install_checks(layout, names))
    return checks


def _install_checks(layout: paths.Layout, names: List[str]) -> List[Check]:
    checks = []
    for target_dir, runtimes in install.runtime_targets(layout.repo_root, paths.RUNTIMES):
        check_id = "install." + os.path.basename(os.path.dirname(target_dir)).lstrip(".")
        states = [install.classify(layout, os.path.join(target_dir, name), layout.skill_dir(name)) for name in names]
        installed = sum(1 for state in states if state in install.INSTALLED)
        where = layout.rel(target_dir)
        if installed == len(names):
            checks.append(
                Check(
                    check_id,
                    OK,
                    "%s: %d/%d skills installed for %s" % (where, installed, len(names), ", ".join(runtimes)),
                )
            )
        else:
            checks.append(
                Check(
                    check_id,
                    WARN,
                    "%s: %d/%d skills installed for %s; run skill-lab install"
                    % (where, installed, len(names), ", ".join(runtimes)),
                )
            )
    return checks


def env_checks(environ: Mapping[str, str]) -> List[Check]:
    checks = []
    for check_id, names, purpose in ENV_CHECKS:
        present = [name for name in names if environ.get(name)]
        if present:
            checks.append(Check(check_id, OK, "%s is set (needed for %s)" % (present[0], purpose)))
        else:
            checks.append(Check(check_id, WARN, "%s not set (needed for %s)" % (" or ".join(names), purpose)))
    return checks


def probe_checks(environ: Mapping[str, str], probe: Probe, *, offline: bool) -> List[Check]:
    targets = [
        ("probe.typesafe", TYPESAFE_MODELS_URL, (200, 401), "Jev API"),
        ("probe.ollama-cloud", OLLAMA_CLOUD_TAGS_URL, (200, 401), "Ollama Cloud"),
        ("probe.ollama-local", OLLAMA_LOCAL_TAGS_URL, (200,), "local Ollama"),
    ]
    gitea_url = _without_userinfo(environ.get("GITEA_URL") or "").rstrip("/")
    if gitea_url:
        targets.append(("probe.gitea", gitea_url + "/api/v1/version", (200,), "Gitea at $GITEA_URL"))
    if offline:
        checks = [
            Check(check_id, WARN, "%s probe skipped (--offline)" % label) for check_id, _url, _ok, label in targets
        ]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(targets)) as pool:
            results = list(pool.map(lambda target: _safe_probe(probe, target[1]), targets))
        checks = [_probe_check(target, result) for target, result in zip(targets, results)]  # noqa: B905 (3.10+)
    if not gitea_url:
        checks.append(Check("probe.gitea", WARN, "GITEA_URL not set; Gitea probe skipped"))
    return checks


def _without_userinfo(url: str) -> str:
    """Drop ``user:password@`` from a URL: probes never send credentials."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return url
    if "@" not in parts.netloc:
        return url
    return urllib.parse.urlunsplit(parts._replace(netloc=parts.netloc.rsplit("@", 1)[1]))


def _safe_probe(probe: Probe, url: str) -> ProbeResult:
    try:
        return probe(url, PROBE_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 - a probe must never fail the doctor
        return ProbeResult(None, compact("%s: %s" % (type(exc).__name__, exc), 120))


def _probe_check(target: tuple, result: ProbeResult) -> Check:
    check_id, url, accepted, label = target
    shown = url if check_id != "probe.gitea" else "$GITEA_URL/api/v1/version"
    if result.status in accepted:
        return Check(check_id, OK, "%s reachable: GET %s returned %d" % (label, shown, result.status))
    if result.status is not None:
        return Check(check_id, WARN, "%s answered GET %s with HTTP %d" % (label, shown, result.status))
    return Check(check_id, WARN, "%s unreachable: GET %s failed (%s)" % (label, shown, result.reason or "no response"))


def collect(
    layout: paths.Layout,
    *,
    environ: Mapping[str, str],
    probe: Probe,
    offline: bool,
    version: Tuple[int, ...] = tuple(sys.version_info[:3]),
    which: Callable[[str], Optional[str]] = shutil.which,
) -> List[Check]:
    """Every check, in report order."""
    return (
        toolchain_checks(version, which)
        + layout_checks(layout)
        + env_checks(environ)
        + probe_checks(environ, probe, offline=offline)
    )


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def main(argv: Sequence[str]) -> int:
    """``skill-lab doctor [--offline]``."""
    return labcli.run_command(lambda: _run(argv), command="doctor", kind="lab-doctor", argv=argv)


def _run(argv: Sequence[str]) -> ScriptResult:
    parser = labcli.command_parser(
        "doctor", "Report the toolchain, layout, installs, env presence and endpoint reachability."
    )
    parser.add_argument("--offline", action="store_true", help="skip the network probes")
    args = parser.parse_args(list(argv))
    layout = labcli.layout_from(args)
    checks = collect(layout, environ=os.environ, probe=http_probe, offline=args.offline)
    summary = {status: sum(1 for check in checks if check.status == status) for status in (OK, WARN, FAIL)}
    payload = {
        "schema_version": 1,
        "ok": summary[FAIL] == 0,
        "checks": [{"id": c.id, "status": c.status, "message": compact(c.message)} for c in checks],
        "summary": summary,
    }
    if summary[FAIL]:
        failures = [{"code": "CHECK_FAILED", "message": c.message, "path": None} for c in checks if c.status == FAIL]
        return ScriptResult(EXIT_FAIL, payload, labcli.capped(failures))
    return ScriptResult(EXIT_OK, payload)
