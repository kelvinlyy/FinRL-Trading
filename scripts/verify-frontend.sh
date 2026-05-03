#!/usr/bin/env bash
# Run before reporting frontend work complete. Fails on first error.
# Cleans .next first — intermittent Next PageNotFoundError during collect happens with stale cache.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps/frontend"
echo "[verify-frontend] npm run clean && npm run build"
npm run clean
npm run build
echo "[verify-frontend] ok"
