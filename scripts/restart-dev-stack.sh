#!/usr/bin/env bash
# Restart FastAPI (8000) + Next.js dev (3000) after apps/backend or apps/frontend changes.
# Usage: ./scripts/restart-dev-stack.sh [--clean-next]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v npm >/dev/null 2>&1; then
  echo "[restart-dev-stack] ERROR: npm not found. Install Node.js 18+ (https://nodejs.org/) so Next.js can start." >&2
  echo "  Debian/Ubuntu: sudo apt install nodejs npm" >&2
  exit 1
fi

CLEAN_NEXT=false
for arg in "$@"; do
  case "$arg" in
    --clean-next) CLEAN_NEXT=true ;;
  esac
done

echo "[restart-dev-stack] Stopping listeners on 8000 and 3000..."
for port in 8000 3000; do
  fuser -k "${port}/tcp" 2>/dev/null || true
done
# fuser can miss child processes; ensure Next is gone
pkill -f '[n]ode .*next dev' 2>/dev/null || true
pkill -f '[n]ext-server' 2>/dev/null || true
sleep 2

if "$CLEAN_NEXT"; then
  echo "[restart-dev-stack] Removing apps/frontend/.next ..."
  rm -rf "$ROOT/apps/frontend/.next"
fi

PY="${ROOT}/.venv/bin/python3"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi

echo "[restart-dev-stack] Starting uvicorn on :8000 (python: $PY) ..."
# Only watch apps/backend — strategy backtests write under src/ and data/; watching the
# whole repo would reload the API mid-job and drop in-memory backtest job state.
PYTHONPATH="$ROOT/apps:$ROOT:$ROOT/src" nohup "$PY" -m uvicorn backend.main:app \
  --host 0.0.0.0 --port 8000 --reload \
  --reload-dir "$ROOT/apps/backend" \
  > /tmp/finrl-uvicorn.log 2>&1 &
echo "  pid $!  log /tmp/finrl-uvicorn.log"

echo "[restart-dev-stack] Starting Next.js dev on :3000 ..."
cd "$ROOT/apps/frontend"
if [[ ! -d node_modules ]]; then
  echo "[restart-dev-stack] ERROR: apps/frontend/node_modules missing. From the repo root run:" >&2
  echo "  cd apps/frontend && npm ci" >&2
  exit 1
fi
nohup npm run dev > /tmp/finrl-next.log 2>&1 &
echo "  pid $!  log /tmp/finrl-next.log"

sleep 4
echo "[restart-dev-stack] Smoke checks..."
curl -s -o /dev/null -w "  GET /docs → %{http_code}\n" http://127.0.0.1:8000/docs || echo "  backend not ready yet"
fe_code="$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/ || true)"
echo "  GET / → ${fe_code}"
if [[ "${fe_code}" != "200" ]]; then
  echo "[restart-dev-stack] Frontend did not respond with 200. Last lines of /tmp/finrl-next.log:" >&2
  tail -n 30 /tmp/finrl-next.log >&2 || true
fi
echo "[restart-dev-stack] Done. Hard-refresh the browser (empty cache) on http://localhost:3000"
