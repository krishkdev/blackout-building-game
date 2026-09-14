#!/bin/zsh

set -eu
cd "$(dirname "$0")"

cleanup() {
  if [[ -n "${blackout_pid:-}" ]]; then
    kill "$blackout_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

BLACKOUT_REMOTE_GAME_URL="${BLACKOUT_REMOTE_GAME_URL:-https://api.maritime.sh/a/1946c780-fe59-4c3b-b821-f3341bc5953c}" python3 blackout_game.py &
blackout_pid=$!
sleep 1
open http://127.0.0.1:8765/controller
wait "$blackout_pid"
