#!/usr/bin/env bash
# Stops the dev server started by run-local.sh.
set -euo pipefail
cd "$(dirname "$0")"

# Same lookup as run-local.sh: a PORT exported in the shell wins, then the one in .env.
if [ -z "${PORT:-}" ] && [ -f .env ]; then
  PORT="$(grep -E '^PORT=[0-9]+$' .env | tail -n 1 | cut -d= -f2 || true)"
fi
PORT="${PORT:-8333}"
PIDFILE=".server.pid"

if [ -f "$PIDFILE" ]; then
  PID="$(cat "$PIDFILE")"
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    # Wait until it is really gone, so ./stop.sh && ./run-local.sh can't race.
    for _ in $(seq 1 50); do kill -0 "$PID" 2>/dev/null || break; sleep 0.1; done
    echo "Stopped (PID $PID)."
  else
    echo "Stale PID $PID in $PIDFILE (already dead)."
  fi
  rm -f "$PIDFILE"
  exit 0
fi

# No pidfile (e.g. the server was started manually, not via run-local.sh) —
# fall back to whatever is actually listening on the port.
PORT_PID="$(lsof -i ":$PORT" -sTCP:LISTEN -t 2>/dev/null || true)"
if [ -n "$PORT_PID" ]; then
  kill "$PORT_PID"
  for _ in $(seq 1 50); do kill -0 "$PORT_PID" 2>/dev/null || break; sleep 0.1; done
  echo "Stopped process on port $PORT (PID $PORT_PID)."
else
  echo "Not running (nothing on port $PORT)."
fi
