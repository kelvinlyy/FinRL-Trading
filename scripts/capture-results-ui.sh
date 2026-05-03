#!/usr/bin/env bash
# Headless screenshot of /results for PR / agent artifacts (requires dev servers up).
set -euo pipefail
OUT="${1:-/tmp/finrl-results-ui.png}"
URL="${2:-http://127.0.0.1:3000/results}"
mkdir -p "$(dirname "$OUT")"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
if ! google-chrome --headless=new --disable-gpu --user-data-dir="$TMPD" \
  --window-size=1400,2200 --screenshot="$OUT" --virtual-time-budget=25000 "$URL"; then
  echo "[capture-results-ui] ERROR: google-chrome failed" >&2
  exit 1
fi
if [[ ! -f "$OUT" ]]; then
  echo "[capture-results-ui] ERROR: screenshot file not created: $OUT" >&2
  exit 1
fi
echo "[capture-results-ui] wrote $OUT ($(wc -c < "$OUT") bytes)"
