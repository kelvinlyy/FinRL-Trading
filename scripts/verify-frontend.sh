#!/usr/bin/env bash
# Run before reporting frontend work complete. Fails on first error.
# Cleans .next first — intermittent Next PageNotFoundError during collect happens with stale cache.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=dev-paths.inc.sh
source "$ROOT/scripts/dev-paths.inc.sh"
FRONTEND_DIR="$(resolve_frontend_dir)" || exit 1
cd "$FRONTEND_DIR"
echo "[verify-frontend] npm run clean && npm run build"
npm run clean
npm run build
echo "[verify-frontend] ok"
