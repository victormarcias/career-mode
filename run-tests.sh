#!/usr/bin/env bash
# Runs every test: pytest for the server, then the front end (a syntax check of
# each public/js/ file and node --test). The first run creates .venv and installs
# requirements-dev.txt. Extra arguments go to pytest, e.g. ./run-tests.sh -k passive
# Exits non-zero if anything failed, but always runs both halves.
set -uo pipefail
cd "$(dirname "$0")"

# Colour only when writing to a terminal (and NO_COLOR is not set), so logs and pipes stay plain.
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  GREEN=$'\033[32m'; YELLOW=$'\033[33m'; BLUE=$'\033[34m'; BOLD=$'\033[1m'; RESET=$'\033[0m'
else
  GREEN=''; YELLOW=''; BLUE=''; BOLD=''; RESET=''
fi
if [ -t 2 ] && [ -z "${NO_COLOR:-}" ]; then RED=$'\033[31m'; else RED=''; fi

VENV=".venv"
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV" || exit 1
# Reinstall only when the requirements changed since the last time.
WANTED="$(cat requirements.txt requirements-dev.txt | shasum | cut -d' ' -f1)"
if [ ! -f "$VENV/.requirements-dev.sha" ] || [ "$(cat "$VENV/.requirements-dev.sha")" != "$WANTED" ]; then
  echo "${BLUE}📦 Installing packages (first run, or the requirements changed)…${RESET}"
  "$VENV/bin/pip" install -q -r requirements-dev.txt || exit 1
  echo "$WANTED" > "$VENV/.requirements-dev.sha"
fi

status=0

echo "${BOLD}🐍 Server (pytest)${RESET}"
"$VENV/bin/python" -m pytest "$@" || status=1

echo
if command -v node >/dev/null 2>&1; then
  echo "${BOLD}🎨 Front end (syntax + node --test)${RESET}"
  for file in public/js/*.js; do
    node --input-type=module --check < "$file" || { echo "${RED}❌ Syntax error in $file${RESET}" >&2; status=1; }
  done
  node --import ./tests/js/setup.mjs --test tests/js/*.test.mjs 2>&1 | grep -E "^(✖|ℹ (tests|pass|fail))|not ok" ; [ "${PIPESTATUS[0]}" -eq 0 ] || status=1
else
  echo "${YELLOW}⏭️  Front end: skipped (Node isn't installed)${RESET}"
fi

echo
[ "$status" -eq 0 ] && echo "${GREEN}✅ All tests passed.${RESET}" || echo "${RED}❌ Some tests failed.${RESET}" >&2
exit "$status"
