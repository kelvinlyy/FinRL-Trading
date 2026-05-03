#!/usr/bin/env bash
# Restart FastAPI (8000) + Next.js dev (3000) after apps/backend or apps/frontend changes.
# Usage: ./scripts/restart-dev-stack.sh [--clean-next]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=dev-paths.inc.sh
source "$ROOT/scripts/dev-paths.inc.sh"

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

echo "[restart-dev-stack] Stopping dev listeners (8000, 3000)..."
"$ROOT/scripts/stop-all-apps.sh"
sleep 2

FRONTEND_DIR="$(resolve_frontend_dir)" || exit 1
if "$CLEAN_NEXT"; then
  echo "[restart-dev-stack] Removing ${FRONTEND_DIR}/.next ..."
  rm -rf "${FRONTEND_DIR}/.next"
fi

PY="$(pick_python)" || exit 1
ensure_next_installed "$FRONTEND_DIR" || exit 1

if [[ "$FRONTEND_DIR" == "$ROOT/apps/frontend" ]] && [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "[restart-dev-stack] ERROR: apps/frontend/node_modules missing. From the repo root run:" >&2
  echo "  cd apps/frontend && npm ci" >&2
  exit 1
fi

echo "[restart-dev-stack] Using Python: $PY"
echo "[restart-dev-stack] Using frontend: $FRONTEND_DIR"

echo "[restart-dev-stack] Starting uvicorn on :8000 ..."
UVICORN_RELOAD=()
if [[ -d "$ROOT/apps/backend" ]]; then
  # Only watch apps/backend — strategy backtests write under src/ and data/; watching the
  # whole repo would reload the API mid-job and drop in-memory backtest job state.
  UVICORN_RELOAD+=(--reload-dir "$ROOT/apps/backend")
fi
PYTHONPATH="$(uvicorn_pythonpath)" nohup "$PY" -m uvicorn backend.main:app \
  --host 0.0.0.0 --port 8000 --reload \
  "${UVICORN_RELOAD[@]}" \
  > /tmp/finrl-uvicorn.log 2>&1 &
echo "  pid $!  log /tmp/finrl-uvicorn.log"

echo "[restart-dev-stack] Starting Next.js dev on :3000 ..."
NEXT_PID=$(launch_next_dev "$FRONTEND_DIR" /tmp/finrl-next.log) || exit 1
echo "  pid ${NEXT_PID}  log /tmp/finrl-next.log"

echo "[restart-dev-stack] Waiting for HTTP 200 (up to ~25s each)..."
SMOKE_FAILED=false
wait_http_200 "http://127.0.0.1:8000/docs" "GET /docs" || SMOKE_FAILED=true
wait_http_200 "http://127.0.0.1:3000/" "GET /" || SMOKE_FAILED=true

if "$SMOKE_FAILED"; then
  echo "[restart-dev-stack] Smoke checks failed. Last log lines:" >&2
  echo "--- /tmp/finrl-uvicorn.log ---" >&2
  tail -n 40 /tmp/finrl-uvicorn.log >&2 || true
  echo "--- /tmp/finrl-next.log ---" >&2
  tail -n 40 /tmp/finrl-next.log >&2 || true
  exit 1
fi

echo "[restart-dev-stack] Done. Hard-refresh the browser (empty cache) on http://localhost:3000"
