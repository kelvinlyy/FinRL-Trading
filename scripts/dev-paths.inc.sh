# shellcheck shell=bash
# Source after ROOT is set:  ROOT="$(cd ...)"; source "$ROOT/scripts/dev-paths.inc.sh"
#
# Env overrides:
#   FINRL_FRONTEND_DIR   Absolute path or repo-relative (e.g. apps/frontend)
#   FINRL_PYTHON         Path to python3 that has uvicorn (optional)

resolve_frontend_dir() {
  if [[ -n "${FINRL_FRONTEND_DIR:-}" ]]; then
    local forced="$FINRL_FRONTEND_DIR"
    [[ "$forced" != /* ]] && forced="$ROOT/${forced#./}"
    if [[ -f "$forced/package.json" ]]; then
      echo "$forced"
      return 0
    fi
    echo "[dev-paths] ERROR: FINRL_FRONTEND_DIR=${FINRL_FRONTEND_DIR} has no package.json." >&2
    return 1
  fi
  # Prefer canonical app tree when present (monorepo / apps layout).
  if [[ -f "$ROOT/apps/frontend/package.json" ]]; then
    echo "$ROOT/apps/frontend"
    return 0
  fi
  if [[ -f "$ROOT/frontend/package.json" ]]; then
    echo "$ROOT/frontend"
    return 0
  fi
  echo "[dev-paths] ERROR: no frontend with package.json (expected apps/frontend or frontend)." >&2
  return 1
}

uvicorn_pythonpath() {
  if [[ -f "$ROOT/apps/backend/main.py" ]]; then
    echo "$ROOT/apps:$ROOT:$ROOT/src"
  else
    echo "$ROOT:$ROOT/src"
  fi
}

pick_python() {
  local candidates=()
  if [[ -n "${FINRL_PYTHON:-}" ]]; then
    candidates+=("$FINRL_PYTHON")
  fi
  candidates+=("$ROOT/.venv/bin/python3" "$ROOT/venv/bin/python3")
  if command -v python3 >/dev/null 2>&1; then
    candidates+=("$(command -v python3)")
  fi
  local py
  for py in "${candidates[@]}"; do
    [[ -z "$py" ]] && continue
    [[ -x "$py" ]] || continue
    if "$py" -c 'import uvicorn' 2>/dev/null; then
      echo "$py"
      return 0
    fi
  done
  echo "[dev-paths] ERROR: no usable Python with uvicorn." >&2
  echo "  Tried: ${candidates[*]}" >&2
  echo "  Fix:    cd \"$ROOT\" && python3 -m venv .venv && .venv/bin/pip install -U pip uvicorn fastapi" >&2
  return 1
}

ensure_next_installed() {
  local dir="$1"
  if [[ -x "$dir/node_modules/.bin/next" ]]; then
    return 0
  fi
  echo "[dev-paths] ERROR: Next.js is not installed under: $dir" >&2
  echo "  Fix:    cd \"$dir\" && npm install" >&2
  return 1
}

# Prints one line: PID of background dev server
launch_next_dev() {
  local dir="$1" log="$2"
  if [[ -f "$dir/package.json" ]]; then
    ensure_next_installed "$dir" || return 1
    (
      cd "$dir" || exit 1
      nohup npm run dev >"$log" 2>&1 &
      echo $!
    )
    return 0
  fi
  ensure_next_installed "$dir" || return 1
  (
    cd "$dir" || exit 1
    nohup ./node_modules/.bin/next dev --hostname 0.0.0.0 --port 3000 >"$log" 2>&1 &
    echo $!
  )
}

wait_http_200() {
  local url="$1"
  local label="$2"
  local max="${3:-25}"
  local i code
  for ((i = 1; i <= max; i++)); do
    code="$(curl -sL -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo 000)"
    if [[ "$code" == "200" ]]; then
      echo "  ${label} → 200 (${i}s)"
      return 0
    fi
    sleep 1
  done
  echo "  ${label} → FAILED (last HTTP ${code})" >&2
  return 1
}
