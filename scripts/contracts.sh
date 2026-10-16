#!/usr/bin/env bash
# Generates the TypeScript types and Pydantic models from contracts/*.schema.json.
# With --check, regenerates into a temporary directory and exits 1 naming each stale file.
set -euo pipefail
cd "$(dirname "$0")/.."

mode=generate
case "${1:-}" in
  "") ;;
  --check) mode=check ;;
  *) echo "usage: $0 [--check]" >&2; exit 2 ;;
esac

ts_dest=worker/src/contracts
py_dest=node/src/yt_digest_node/contracts

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

uv run --locked --project node python scripts/generate_contracts.py "$tmp/ts" "$tmp/py"
uv run --locked --project node ruff format --quiet --config node/pyproject.toml "$tmp/py"

stale=0
compare() {
  local gen=$1 dest=$2 rel
  while IFS= read -r rel; do
    if ! cmp -s "$gen/$rel" "$dest/$rel"; then
      echo "stale generated file: $dest/${rel#./}" >&2
      stale=1
    fi
  done < <({
    (cd "$gen" && find . -type f)
    if [[ -d "$dest" ]]; then (cd "$dest" && find . -type f -not -path '*/__pycache__/*'); fi
  } | sort -u)
}

if [[ $mode == check ]]; then
  compare "$tmp/ts" "$ts_dest"
  compare "$tmp/py" "$py_dest"
  if [[ $stale -ne 0 ]]; then
    echo "run ./scripts/contracts.sh to regenerate" >&2
    exit 1
  fi
  echo "generated contracts are up to date"
else
  for pair in "$tmp/ts:$ts_dest" "$tmp/py:$py_dest"; do
    rm -rf "${pair#*:}"
    mkdir -p "${pair#*:}"
    cp -R "${pair%%:*}/." "${pair#*:}/"
  done
fi
