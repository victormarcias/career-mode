#!/usr/bin/env bash
# Backs up what is yours, to the backup folder (BACKUP_DIR in Settings or .env; `backup`
# by default):
#   calendar.csv, companies.csv   the database: the events, the agencies and the clients
#   profile/                      profile.md, outreach.md (your messages), cv.pdf and photo.*
# and keeps a dated copy of all of it in history/ (skipped when nothing changed since the
# last copy). .env is left out on purpose: it holds keys. Bring a copy back with
#   ./restore-backup.sh <backup folder>/history/<date>
set -euo pipefail
cd "$(dirname "$0")"

# Colour only when writing to a terminal (and NO_COLOR is not set), so logs and pipes stay plain.
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  GREEN=$'\033[32m'; YELLOW=$'\033[33m'; BLUE=$'\033[34m'; BOLD=$'\033[1m'; RESET=$'\033[0m'
else
  GREEN=''; YELLOW=''; BLUE=''; BOLD=''; RESET=''
fi
if [ -t 2 ] && [ -z "${NO_COLOR:-}" ]; then RED=$'\033[31m'; else RED=''; fi

# the files of profile/ that are yours (its README and the examples ship with the repo)
PROFILE_FILES="profile.md outreach.md cv.pdf photo.png photo.jpg"

BACKUP="$(.venv/bin/python server/cli.py backup-dir)"
echo "${BLUE}💾 Backing up to ${BOLD}$BACKUP${RESET}${BLUE}…${RESET}"
.venv/bin/python server/cli.py export "$BACKUP"

# profile/: replace the copies of the files we manage, so one you removed is not kept
mkdir -p "$BACKUP/profile"
for f in $PROFILE_FILES; do
  rm -f "$BACKUP/profile/$f"
  if [ -f "profile/$f" ]; then
    cp "profile/$f" "$BACKUP/profile/$f"
    case "$f" in *.md) chmod 600 "$BACKUP/profile/$f" ;; esac
    echo "${GREEN}📄 Copied profile/$f${RESET}"
  fi
done

# the newest copy (the names sort by date)
LAST="$(ls -1d "$BACKUP"/history/*/ 2>/dev/null | sort | tail -n 1 || true)"
unchanged() {  # $1: a copy in history/ (with its trailing slash)
  diff -q "$BACKUP/calendar.csv" "$1calendar.csv" >/dev/null \
    && diff -q "$BACKUP/companies.csv" "$1companies.csv" >/dev/null \
    && diff -rq "$BACKUP/profile" "$1profile" >/dev/null 2>&1
}
if [ -n "$LAST" ] && unchanged "$LAST"; then
  echo "${YELLOW}😌 No changes since ${LAST%/}: no new copy.${RESET}"
else
  DEST="$BACKUP/history/$(date +%Y-%m-%d_%H%M%S)"
  mkdir -p "$DEST"
  cp "$BACKUP/calendar.csv" "$BACKUP/companies.csv" "$DEST/"
  cp -R "$BACKUP/profile" "$DEST/profile"
  echo "${GREEN}✅ Kept a copy in $DEST${RESET}"
fi
