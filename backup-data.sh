#!/usr/bin/env bash
# Backs up what is yours, to the backup/ folder:
#   calendar.csv, companies.csv   the database: the events, the agencies and the clients
#   profile/                      profile.md, outreach.md (your messages), cv.pdf, photo.* and daily-posts/
#   profile/profile.pdf           the profile laid out as a document (Drive: upload it, then Open
#                                 with Google Docs)
#   profile/outreach.pdf          your messages as a document, ending with their exact text for /setup
#                                 Both PDFs are made with Chrome or Chromium and skipped, with a warning,
#                                 if there is neither. They are rebuilt every time and left out of history/
# and keeps a dated copy of all of it in history/ (skipped when nothing changed since the
# last copy). Your .env (the keys and passwords of Settings) goes to <backup folder>/env/env, readable only by
# you: one copy, replaced every time and not part of history/, so old passwords don't pile up. Bring a copy back with
#   ./restore-backup.sh <backup folder>/history/<date>
# When it is run from a terminal it opens the backup folder at the end (`open` on macOS,
# `xdg-open` on Linux), so you can see what was written.
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

# the posts of the daily post skill: the texts, their images and the log of what was posted
rm -rf -- "${BACKUP:?}/profile/daily-posts"
if [ -d profile/daily-posts ]; then
  cp -R profile/daily-posts "$BACKUP/profile/daily-posts"
  echo "${GREEN}📄 Copied profile/daily-posts/${RESET}"
fi

# profile.pdf and outreach.pdf, in the backup's profile/ folder: the profile and your messages as documents, to read or
# to open in Google Docs. Rebuilt every time, and left out of the comparison and of history/ below: a PDF carries its
# creation time, so it would always look changed.
# restore-backup.sh only restores the files it knows, so these are never loaded back. A failure here never stops the backup.
for doc in profile outreach; do
  rm -f "$BACKUP/$doc.pdf" "$BACKUP/profile/$doc.pdf"  # the first is where an older backup kept it
  if [ -f "profile/$doc.md" ]; then
    if .venv/bin/python server/cli.py "$doc-pdf" "$BACKUP/profile/$doc.pdf" >/dev/null; then
      chmod 600 "$BACKUP/profile/$doc.pdf"
      echo "${GREEN}📑 Made $BACKUP/profile/$doc.pdf${RESET}"
    else
      echo "${YELLOW}⚠️  No $doc.pdf this time (see the message above); everything else was backed up.${RESET}"
    fi
  fi
done

# env/env: the latest copy of your .env, with its keys and passwords, so a new computer or a lost file doesn't mean making
# them all again. One file, replaced every time, outside history/ and outside the comparison below. backup/ is ignored by
# git and only as private as your computer.
rm -f "$BACKUP/env/env"
if [ -f .env ]; then
  mkdir -p "$BACKUP/env"
  chmod 700 "$BACKUP/env"
  cp .env "$BACKUP/env/env"
  chmod 600 "$BACKUP/env/env"
  echo "${GREEN}🔑 Copied .env to $BACKUP/env/env${RESET}"
fi

# the newest copy (the names sort by date)
LAST="$(ls -1d "$BACKUP"/history/*/ 2>/dev/null | sort | tail -n 1 || true)"
unchanged() {  # $1: a copy in history/ (with its trailing slash)
  diff -q "$BACKUP/calendar.csv" "$1calendar.csv" >/dev/null \
    && diff -q "$BACKUP/companies.csv" "$1companies.csv" >/dev/null \
    && diff -rq -x profile.pdf -x outreach.pdf "$BACKUP/profile" "$1profile" >/dev/null 2>&1
}
if [ -n "$LAST" ] && unchanged "$LAST"; then
  echo "${YELLOW}😌 No changes since ${LAST%/}: no new copy.${RESET}"
else
  DEST="$BACKUP/history/$(date +%Y-%m-%d_%H%M%S)"
  mkdir -p "$DEST"
  cp "$BACKUP/calendar.csv" "$BACKUP/companies.csv" "$DEST/"
  cp -R "$BACKUP/profile" "$DEST/profile"
  rm -f "$DEST/profile/profile.pdf" "$DEST/profile/outreach.pdf"
  echo "${GREEN}✅ Kept a copy in $DEST${RESET}"
fi

# show the folder, but only when someone is looking: not from cron or a pipe
if [ -t 1 ]; then
  if command -v open >/dev/null 2>&1; then open "$BACKUP"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$BACKUP" >/dev/null 2>&1 || true
  fi
fi
