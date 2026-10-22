#!/bin/bash
# SessionStart hook for Claude Code cloud sessions: makes the Spec-Driven Development workstation
# ready before the first turn (Spec Kit CLI, the sdd-harness engines, the existing TS package).
# Idempotent and non-interactive; the container is cached after it finishes.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
SPECKIT_VERSION="v1.2.2"
export PATH="$HOME/.local/bin:$PATH"

log() { echo "[session-start] $*" >&2; }

# uv: Python toolchain for Spec Kit and packages/sdd-harness.
if ! command -v uv >/dev/null 2>&1; then
  log "installing uv"
  python3 -m pip install --quiet --user uv
fi

# Spec Kit CLI (specify), pinned to the version .specify/ was initialized with.
if ! specify version 2>/dev/null | grep -q "${SPECKIT_VERSION#v}"; then
  log "installing specify-cli $SPECKIT_VERSION"
  uv tool install --quiet --force specify-cli --from "git+https://github.com/github/spec-kit.git@${SPECKIT_VERSION}"
fi

# The engines behind the sdd-intake-engine, sdd-skill-router and sdd-decision-ledger skills.
log "syncing packages/sdd-harness"
uv sync --quiet --project "$ROOT/packages/sdd-harness"

# Existing TypeScript package (jest tests).
if [ -f "$ROOT/packages/walkthroughgen/package.json" ]; then
  log "installing packages/walkthroughgen"
  (cd "$ROOT/packages/walkthroughgen" && npm install --silent --no-audit --no-fund >/dev/null)
fi

# Warm the derived indexes (gitignored) so the first route/refine call is fast.
"$ROOT/bin/intakespec" build >/dev/null 2>&1 || log "skills graph build skipped"
"$ROOT/bin/sdd" index build >/dev/null 2>&1 || log "retrieval index build skipped"

# Make bin/sdd, bin/intakespec and uv tools available on PATH for the session.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export PATH=\"$ROOT/bin:\$HOME/.local/bin:\$PATH\""
  } >> "$CLAUDE_ENV_FILE"
fi
log "ready"
