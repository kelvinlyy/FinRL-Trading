#!/usr/bin/env bash
# Run before reporting frontend work complete. Fails on first error.
# Cleans .next first — intermittent Next PageNotFoundError during collect happens with stale cache.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=dev-paths.inc.sh
source "$ROOT/scripts/dev-paths.inc.sh"
FRONTEND_DIR="$(resolve_frontend_dir)" || exit 1

if ! command -v npm >/dev/null 2>&1; then
  echo "[verify-frontend] ERROR: npm not found. Install Node.js 18+ first." >&2
  exit 1
fi
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  if [[ "$FRONTEND_DIR" == "$ROOT/apps/frontend" ]]; then
    echo "[verify-frontend] ERROR: node_modules missing. Run: cd apps/frontend && npm ci" >&2
  else
    echo "[verify-frontend] ERROR: node_modules missing. Run: cd \"$FRONTEND_DIR\" && npm install" >&2
  fi
  exit 1
fi

cd "$FRONTEND_DIR"
echo "[verify-frontend] npm run clean && npm run build"
npm run clean
npm run build
echo "[verify-frontend] ok"
