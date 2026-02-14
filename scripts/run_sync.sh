#!/usr/bin/env bash
set -euo pipefail

# YouTube Organizer sync runner (cron-friendly)
# - Creates/uses .venv
# - Installs requirements
# - Runs yt_sync.py and pushes reports

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

PY="${PYTHON:-python3}"

if [[ ! -d .venv ]]; then
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

pip install --upgrade pip >/dev/null
pip install -r requirements.txt >/dev/null

# Default: push. Add --no-push to skip.
PUSH=1
ARGS=()
for a in "$@"; do
  if [[ "$a" == "--no-push" ]]; then
    PUSH=0
  else
    ARGS+=("$a")
  fi
done

if [[ "$PUSH" == "1" ]]; then
  if ((${#ARGS[@]})); then
    "$PY" scripts/yt_sync.py --push "${ARGS[@]}"
  else
    "$PY" scripts/yt_sync.py --push
  fi
else
  if ((${#ARGS[@]})); then
    "$PY" scripts/yt_sync.py "${ARGS[@]}"
  else
    "$PY" scripts/yt_sync.py
  fi
fi
