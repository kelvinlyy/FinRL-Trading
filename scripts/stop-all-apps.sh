#!/usr/bin/env bash
# Stop FastAPI (8000), Next.js dev (3000), and optional Streamlit (8501).
# Usage: ./scripts/stop-all-apps.sh [--with-streamlit]
#   --with-streamlit  Also free port 8501 and kill Streamlit for this repo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

WITH_STREAMLIT=false
for arg in "$@"; do
  case "$arg" in
    --with-streamlit) WITH_STREAMLIT=true ;;
  esac
done

kill_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -ti:"$port" 2>/dev/null || true)"
    if [[ -n "${pids}" ]]; then
      # shellcheck disable=SC2086
      kill -9 ${pids} 2>/dev/null || true
    fi
  else
    fuser -k "${port}/tcp" 2>/dev/null || true
  fi
}

echo "[stop-all-apps] Stopping listeners on 8000 and 3000..."
kill_port 8000
kill_port 3000
if "$WITH_STREAMLIT"; then
  echo "[stop-all-apps] Stopping listener on 8501 (Streamlit)..."
  kill_port 8501
fi

# fuser/lsof can miss child processes; ensure Next is gone
pkill -f '[n]ode .*next dev' 2>/dev/null || true
pkill -f '[n]ext-server' 2>/dev/null || true
pkill -f '[u]vicorn backend.main:app' 2>/dev/null || true

if "$WITH_STREAMLIT"; then
  pkill -f '[s]treamlit run .*src/web/app.py' 2>/dev/null || true
fi

sleep 1
echo "[stop-all-apps] Done."
