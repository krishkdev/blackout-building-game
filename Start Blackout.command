#!/bin/zsh

set -eu
cd "$(dirname "$0")"

cleanup() {
  if [[ -n "${blackout_pid:-}" ]]; then
    kill "$blackout_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

python3 blackout_game.py &
blackout_pid=$!
sleep 1
open http://127.0.0.1:8765
wait "$blackout_pid"
