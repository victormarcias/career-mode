#!/usr/bin/env bash
# Starts career-mode in the background at http://localhost:8333 (or the PORT in .env).
# Use stop.sh to stop it. The first run also creates the virtual environment
# (.venv), installs the packages in requirements.txt and creates the database.
set -euo pipefail
cd "$(dirname "$0")"

# Colour only when writing to a terminal (and NO_COLOR is not set), so logs and pipes stay plain.
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  GREEN=$'\033[32m'; YELLOW=$'\033[33m'; BLUE=$'\033[34m'; BOLD=$'\033[1m'; RESET=$'\033[0m'
else
  GREEN=''; YELLOW=''; BLUE=''; BOLD=''; RESET=''
fi
if [ -t 2 ] && [ -z "${NO_COLOR:-}" ]; then RED=$'\033[31m'; else RED=''; fi

# This script (and stop.sh, backup-data.sh...) is bash with lsof, so it needs macOS, Linux or WSL.
case "$(uname -s)" in
  Darwin|Linux) ;;
  *) echo "${RED}❌ This needs macOS, Linux or WSL (Windows Subsystem for Linux).${RESET}" >&2; exit 1 ;;
esac

# The first time there is no .env: start it from .env.example (minus the placeholder
# API key, so nothing looks set when it isn't). .env is the source of truth after that.
if [ ! -f .env ] && [ -f .env.example ]; then
  grep -v '^GEMINI_API_KEY=' .env.example > .env
  chmod 600 .env
fi

# Same for the user's own data in profile/: each file starts as a copy of its example (an invented person) and is
# gitignored from then on. Fill profile/profile.md as profile/README.md says, and edit the messages.
for file in profile.md outreach.md; do
  example="profile/${file%.*}.example.${file##*.}"
  if [ ! -f "profile/$file" ] && [ -f "$example" ]; then
    cp "$example" "profile/$file"
    echo "${YELLOW}📝 Created profile/$file from its example: make it yours (see profile/README.md).${RESET}"
  fi
done

# The port saved in Settings (.env) is needed here to check it and to wait for the
# server; a PORT already exported in the shell wins. The server itself reads the
# rest of .env (the database path, for one).
if [ -z "${PORT:-}" ] && [ -f .env ]; then
  PORT="$(grep -E '^PORT=[0-9]+$' .env | tail -n 1 | cut -d= -f2 || true)"
fi

PORT="${PORT:-8333}"  # only if .env has no PORT either
PIDFILE=".server.pid"
VENV=".venv"

# Check the port itself, not just our own pidfile: something else (e.g. a
# manually-started server) may already be listening on it.
if lsof -i ":$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "${YELLOW}⚠️  Port $PORT is already in use — assuming the server is already running at ${BOLD}http://localhost:$PORT${RESET}"
  exit 0
fi

if [ ! -x "$VENV/bin/python" ]; then
  command -v python3 >/dev/null 2>&1 || { echo "${RED}❌ python3 not found: install Python 3.10 or newer.${RESET}" >&2; exit 1; }
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
    || { echo "${RED}❌ Python 3.10 or newer is needed (this is $(python3 --version 2>&1)).${RESET}" >&2; exit 1; }
  python3 -m venv "$VENV"
fi
# Reinstall only when requirements.txt changed since the last time.
WANTED="$(shasum requirements.txt | cut -d' ' -f1)"
if [ ! -f "$VENV/.requirements.sha" ] || [ "$(cat "$VENV/.requirements.sha")" != "$WANTED" ]; then
  echo "${BLUE}📦 Installing packages (first run, or requirements.txt changed)…${RESET}"
  "$VENV/bin/pip" install -q -r requirements.txt
  echo "$WANTED" > "$VENV/.requirements.sha"
fi

nohup "$VENV/bin/python" server/run.py --port "$PORT" > .server.log 2>&1 &
echo $! > "$PIDFILE"

# Give it a moment to come up, and say so plainly if it didn't.
for _ in $(seq 1 100); do
  curl -s -o /dev/null "http://127.0.0.1:$PORT/" && {
    echo "${GREEN}🚀 Started at ${BOLD}http://localhost:$PORT${RESET}${GREEN} (PID $(cat "$PIDFILE")). 📚 API docs: http://localhost:$PORT/docs${RESET}"
    # still the example: say what comes next (the setup is a skill, so it needs Claude Code)
    if cmp -s profile/profile.md profile/profile.example.md 2>/dev/null; then
      echo "${YELLOW}👋 Your profile is still the example: open Claude Code in this folder and run ${BOLD}/setup${RESET}${YELLOW}.${RESET}"
    fi
    exit 0
  }
  kill -0 "$(cat "$PIDFILE")" 2>/dev/null || break
  sleep 0.1
done
echo "${RED}💥 The server did not start. Last lines of .server.log:${RESET}" >&2
tail -n 15 .server.log >&2
rm -f "$PIDFILE"
exit 1
