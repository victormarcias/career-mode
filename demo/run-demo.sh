#!/usr/bin/env bash
# Starts the demo of career-mode at http://localhost:8334 (or the PORT you export), with invented data only:
# its own database, its own profile and no .env, so nothing of yours is read, shown or sent.
#
#   ./demo/run-demo.sh          start it (the data is made again, from today, on every start)
#   ./demo/run-demo.sh stop     stop it
#
# It never touches data/, profile/ or .env. The demo's files are in demo/data/ (ignored by git).
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${PORT:-8334}"
PIDFILE="demo/data/server.pid"
VENV=".venv"
mkdir -p demo/data

if [ "${1:-}" = "stop" ]; then
  if [ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null; then
    rm -f "$PIDFILE"; echo "🛑 Demo stopped."
  else
    rm -f "$PIDFILE"; echo "The demo is not running."
  fi
  exit 0
fi

if lsof -i ":$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "⚠️  Port $PORT is already in use: assuming the demo is running at http://localhost:$PORT"
  exit 0
fi

# the same environment as the app (run ./run-local.sh once, or: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)
[ -x "$VENV/bin/python" ] || { echo "❌ No .venv yet: run ./run-local.sh once first." >&2; exit 1; }

# a fresh database every time, filled with the invented companies and events, dated around today
rm -f demo/data/demo.db demo/data/demo.db-shm demo/data/demo.db-wal
"$VENV/bin/python" demo/make_demo.py demo/data
"$VENV/bin/python" server/cli.py import demo/data --db demo/data/demo.db

nohup "$VENV/bin/python" server/run.py --port "$PORT" --db demo/data/demo.db \
  --profile-dir demo/profile --env demo/data/demo.env > demo/data/server.log 2>&1 &
echo $! > "$PIDFILE"

for _ in $(seq 1 100); do
  curl -s -o /dev/null "http://127.0.0.1:$PORT/" && {
    echo "🚀 Demo at http://localhost:$PORT (PID $(cat "$PIDFILE")). Stop it with ./demo/run-demo.sh stop"
    exit 0
  }
  sleep 0.1
done
echo "❌ The demo did not start: see demo/data/server.log" >&2
exit 1
