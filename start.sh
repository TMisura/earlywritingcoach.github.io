#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [ ! -f "$ROOT/data/standards/by_state.json" ]; then
  python3 "$ROOT/tools/build_standards.py"
fi
export PYTHONPATH="$ROOT/backend"
exec python3 -m uvicorn server:app --app-dir "$ROOT/backend" --host 0.0.0.0 --port "${PORT:-8000}"
