#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PAPERCLIP_URL="${PAPERCLIP_API_URL:-http://localhost:3100}"

usage() { echo "Usage: $0 --check | --onboard | --run"; }
check() {
  command -v python3 >/dev/null || { echo "Missing python3"; return 2; }
  command -v git >/dev/null || { echo "Missing git"; return 2; }
  command -v codex >/dev/null || echo "WARN: codex CLI is not on PATH"
  command -v npx >/dev/null || echo "WARN: npx is not on PATH; install Paperclip separately"
  test -f "${CODEX_HOME:-$HOME/.codex}/auth.json" && test -s "${CODEX_HOME:-$HOME/.codex}/auth.json" && echo "Codex host login: present (contents withheld)" || echo "WARN: Codex host login not found at ${CODEX_HOME:-$HOME/.codex}/auth.json"
  test -f "$ROOT/third_party/career-ops/scan.mjs" && echo "Career-Ops: available" || echo "WARN: Career-Ops submodule is unavailable"
  if command -v curl >/dev/null && curl -fsS --max-time 3 "$PAPERCLIP_URL/api/health" >/dev/null 2>&1; then echo "Paperclip server: reachable at $PAPERCLIP_URL"; else echo "Paperclip server: not reachable at $PAPERCLIP_URL"; fi
}
case "${1:-}" in
  --check) check ;;
  --onboard)
    check
    command -v npx >/dev/null || { echo "Install Node.js/npm, then rerun."; exit 2; }
    export PAPERCLIP_TELEMETRY_DISABLED="${PAPERCLIP_TELEMETRY_DISABLED:-1}"
    export PAPERCLIP_OPEN_ON_LISTEN="${PAPERCLIP_OPEN_ON_LISTEN:-false}"
    exec npx --yes paperclipai onboard --yes
    ;;
  --run)
    check
    command -v npx >/dev/null || { echo "Install Node.js/npm, then rerun."; exit 2; }
    export PAPERCLIP_TELEMETRY_DISABLED="${PAPERCLIP_TELEMETRY_DISABLED:-1}"
    export PAPERCLIP_OPEN_ON_LISTEN="${PAPERCLIP_OPEN_ON_LISTEN:-false}"
    exec npx --yes paperclipai run
    ;;
  *) usage; exit 2 ;;
esac
