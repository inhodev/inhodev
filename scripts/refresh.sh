#!/usr/bin/env bash
# Rescan this machine's agent stores and rebuild every asset.
# Run this locally — CI runners can't see ~/.codex.
set -euo pipefail

cd "$(dirname "$0")/.."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> scanning primary agent stores"
bunx tokscale@latest graph --no-spinner --output "$TMP/main.json"

# tokscale reads one sessions dir per run. Codex keeps a second pile in
# ~/.codex/archived_sessions, so point a throwaway HOME at it and scan again.
ARCHIVED="$HOME/.codex/archived_sessions"
SCANS=("$TMP/main.json")
if [ -e "$ARCHIVED" ]; then
  echo "==> scanning archived codex sessions"
  mkdir -p "$TMP/home/.codex"
  ln -sfn "$(readlink "$ARCHIVED" || echo "$ARCHIVED")" "$TMP/home/.codex/sessions"
  if bunx tokscale@latest graph --no-spinner --home "$TMP/home" \
       --output "$TMP/archived.json" 2>/dev/null; then
    SCANS+=("$TMP/archived.json")
  else
    echo "    (archived scan failed — continuing with primary only)"
  fi
fi

echo "==> merging"
python3 scripts/merge_scans.py data/graph.json "${SCANS[@]}"

echo "==> rebuilding assets"
python3 scripts/build_assets.py

echo
echo "==> done. review, then:"
echo "    git add -A && git commit -m 'chore: refresh usage data' && git push"
