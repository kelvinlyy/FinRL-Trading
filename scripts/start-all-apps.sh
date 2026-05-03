#!/usr/bin/env bash
# Start FastAPI (8000) + Next.js dev (3000). Optional Streamlit (8501).
# Usage: ./scripts/start-all-apps.sh [--with-streamlit] [--force]
# Optional env:
#   FINRL_FRONTEND_DIR=apps/frontend
#   FINRL_PYTHON=/path/to/python3
# Flags:
#   --with-streamlit  Also start Streamlit dashboard on :8501
#   --force           Run stop-all-apps.sh first (add --with-streamlit to stop 8501 too)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=dev-paths.inc.sh
source "$ROOT/scripts/dev-paths.inc.sh"

WITH_STREAMLIT=false
FORCE=false
for arg in "$@"; do
  case "$arg" in
    --with-streamlit) WITH_STREAMLIT=true ;;
    --force) FORCE=true ;;
  esac
done

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    if lsof -ti:"$port" >/dev/null 2>&1; then
      return 0
    fi
    return 1
  fi
  if command -v fuser >/dev/null 2>&1; then
    if fuser "${port}/tcp" >/dev/null 2>&1; then
      return 0
    fi
    return 1
  fi
  echo "[start-all-apps] WARN: neither lsof nor fuser; skipping port check for ${port}" >&2
  return 1
}

if "$FORCE"; then
  if "$WITH_STREAMLIT"; then
    "$ROOT/scripts/stop-all-apps.sh" --with-streamlit
  else
    "$ROOT/scripts/stop-all-apps.sh"
  fi
  sleep 1
fi

for port in 8000 3000; do
  if port_in_use "$port"; then
    echo "[start-all-apps] Port ${port} is already in use. Run ./scripts/stop-all-apps.sh first or use --force." >&2
    exit 1
  fi
done
if "$WITH_STREAMLIT" && port_in_use 8501; then
  echo "[start-all-apps] Port 8501 is already in use. Run ./scripts/stop-all-apps.sh --with-streamlit first or use --force." >&2
  exit 1
fi

PY="$(pick_python)" || exit 1
FRONTEND_DIR="$(resolve_frontend_dir)" || exit 1
ensure_next_installed "$FRONTEND_DIR" || exit 1

echo "[start-all-apps] Using Python: $PY"
echo "[start-all-apps] Using frontend: $FRONTEND_DIR"

echo "[start-all-apps] Starting uvicorn on :8000 ..."
UVICORN_RELOAD=()
if [[ -d "$ROOT/apps/backend" ]]; then
  UVICORN_RELOAD+=(--reload-dir "$ROOT/apps/backend")
fi
PYTHONPATH="$(uvicorn_pythonpath)" nohup "$PY" -m uvicorn backend.main:app \
  --host 0.0.0.0 --port 8000 --reload \
  "${UVICORN_RELOAD[@]}" \
  > /tmp/finrl-uvicorn.log 2>&1 &
echo "  pid $!  log /tmp/finrl-uvicorn.log"

echo "[start-all-apps] Starting Next.js dev on :3000 ..."
NEXT_PID=$(launch_next_dev "$FRONTEND_DIR" /tmp/finrl-next.log) || exit 1
echo "  pid ${NEXT_PID}  log /tmp/finrl-next.log"

if "$WITH_STREAMLIT"; then
  echo "[start-all-apps] Starting Streamlit on :8501 ..."
  cd "$ROOT"
  PYTHONPATH="$(uvicorn_pythonpath)" nohup "$PY" -m streamlit run src/web/app.py \
    --server.port 8501 --server.headless true \
    > /tmp/finrl-streamlit.log 2>&1 &
  echo "  pid $!  log /tmp/finrl-streamlit.log"
fi

echo "[start-all-apps] Waiting for HTTP 200 (up to ~25s each)..."
SMOKE_FAILED=false
wait_http_200 "http://127.0.0.1:8000/docs" "GET /docs" || SMOKE_FAILED=true
wait_http_200 "http://127.0.0.1:3000/" "GET /" || SMOKE_FAILED=true
if "$WITH_STREAMLIT"; then
  wait_http_200 "http://127.0.0.1:8501/" "GET Streamlit :8501" || SMOKE_FAILED=true
fi

if "$SMOKE_FAILED"; then
  echo "[start-all-apps] Smoke checks failed. Last log lines:" >&2
  echo "--- /tmp/finrl-uvicorn.log ---" >&2
  tail -n 40 /tmp/finrl-uvicorn.log >&2 || true
  echo "--- /tmp/finrl-next.log ---" >&2
  tail -n 40 /tmp/finrl-next.log >&2 || true
  if "$WITH_STREAMLIT"; then
    echo "--- /tmp/finrl-streamlit.log ---" >&2
    tail -n 40 /tmp/finrl-streamlit.log >&2 || true
  fi
  exit 1
fi

echo "[start-all-apps] Done. API http://127.0.0.1:8000/docs  App http://localhost:3000"
if "$WITH_STREAMLIT"; then
  echo "  Streamlit http://localhost:8501"
fi
echo "[start-all-apps] Hard-refresh the browser (empty cache) after restarts."
