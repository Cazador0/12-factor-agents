"""Security screen for catalog skills: unaudited third-party instructions.

A skill may describe how to do a task, but it cannot widen the project's tiers or permissions.
Any bundled script that installs, deletes or reaches the network is a tier 3 step, which needs the
person's OK before it runs. Instructions that try to steer the agent are flagged as injection.
"""

from __future__ import annotations

import re
from pathlib import Path

SCRIPT_EXT = {".py", ".sh", ".bash", ".js", ".mjs", ".ts", ".rb", ".ps1"}
PATTERNS: dict[str, re.Pattern[str]] = {
    "installs": re.compile(
        r"\b(pip3? install|uv (add|pip install)|npm (i|install)\b|pnpm add|yarn add|apt(-get)? install|brew install|"
        r"cargo install|go install|gem install|curl[^|\n]*\|\s*(ba)?sh|wget[^|\n]*\|\s*(ba)?sh)",
        re.I,
    ),
    "deletes": re.compile(
        r"\b(rm\s+-[rf]{1,2}\b|shutil\.rmtree|os\.remove|os\.unlink|Path\([^)]*\)\.unlink|\.rmdir\(|"
        r"git push\s+(-f|--force)|git reset --hard|DROP TABLE|truncate table)",
        re.I,
    ),
    "network": re.compile(
        r"\b(requests\.(get|post|put|delete)|urllib\.request|httpx\.|aiohttp|fetch\(|axios|socket\.|"
        r"curl\s+-|curl\s+https?://|wget\s+|http\.client)",
        re.I,
    ),
}
INJECTION = re.compile(
    r"(ignore (all |any )?(previous|prior|above) instructions|disregard (the )?(system|previous)|"
    r"you are now|exfiltrat|send (the )?(token|secret|credential)s? to|bypass (the )?(permission|approval)s?|"
    r"do not tell the user|without asking the user)",
    re.I,
)


def screen_skill(skill_dir: Path, body: str) -> tuple[int, list[str], list[str]]:
    """Return (tier, findings, scripts). Tier 3 = needs the person's OK before any script runs."""
    findings: list[str] = []
    scripts: list[str] = []
    tier = 1
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.suffix not in SCRIPT_EXT:
            continue
        if any(p in {"node_modules", ".venv", "__pycache__"} for p in path.parts):
            continue
        rel = str(path.relative_to(skill_dir))
        scripts.append(rel)
        tier = max(tier, 2)
        try:
            lines = path.read_text("utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for kind, rx in PATTERNS.items():
            hit = next((i for i, ln in enumerate(lines, 1) if rx.search(ln)), None)
            if hit:
                findings.append(f"{kind}: {rel}:{hit}")
                tier = 3
    for i, ln in enumerate(body.splitlines(), 1):
        if INJECTION.search(ln):
            findings.append(f"injection-like instruction: SKILL.md body line {i}")
            tier = 3
    return tier, findings, scripts
