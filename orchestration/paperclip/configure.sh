#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "$ROOT/orchestration/paperclip/configure.py" "$@"
