#!/usr/bin/env bash
# Run before reporting frontend work complete. Fails on first error.
# Cleans .next first — intermittent Next PageNotFoundError during collect happens with stale cache.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps/frontend"
if ! command -v npm >/dev/null 2>&1; then
  echo "[verify-frontend] ERROR: npm not found. Install Node.js 18+ first." >&2
  exit 1
fi
if [[ ! -d node_modules ]]; then
  echo "[verify-frontend] ERROR: node_modules missing. Run: cd apps/frontend && npm ci" >&2
  exit 1
fi
echo "[verify-frontend] npm run clean && npm run build"
npm run clean
npm run build
echo "[verify-frontend] ok"
