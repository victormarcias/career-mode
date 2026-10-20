#!/usr/bin/env bash
# Loads a backup into the database, and its profile files back into profile/.
#
#   ./restore-backup.sh                          load the backup folder (what backup-data.sh wrote last)
#   ./restore-backup.sh <folder>/history/<date>  load one of the dated copies
#   ./restore-backup.sh DIR --replace            empty the database and overwrite the profile files
#                                                first (asks to confirm; -y skips)
#
# The backup folder is BACKUP_DIR (Settings or .env; `backup` by default). DIR has
# calendar.csv and companies.csv (the older JSON backups work too) and, from the newer
# backups, a profile/ folder (profile.md, outreach.md, cv.pdf, photo.*, daily-posts/). Without --replace
# nothing is overwritten: what is already in the database or in profile/ is skipped and
# reported. With --replace the current data and profile files are first copied to
# <backup folder>/history/<date>_before-restore/, so they can be loaded back.
# The backup folder's own env/env (the latest copy of your .env) comes back the same way:
# only if there is none here, or with --replace; restart the app after it so it reads it.
set -euo pipefail
cd "$(dirname "$0")"

# Colour only when writing to a terminal (and NO_COLOR is not set), so logs and pipes stay plain.
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  GREEN=$'\033[32m'; YELLOW=$'\033[33m'; BLUE=$'\033[34m'; BOLD=$'\033[1m'; RESET=$'\033[0m'
else
  GREEN=''; YELLOW=''; BLUE=''; BOLD=''; RESET=''
fi
if [ -t 2 ] && [ -z "${NO_COLOR:-}" ]; then RED=$'\033[31m'; else RED=''; fi

[ -x .venv/bin/python ] || { echo "${RED}❌ No .venv yet: run ./run-local.sh once first.${RESET}" >&2; exit 1; }
BACKUP="$(.venv/bin/python server/cli.py backup-dir)"
DIR="$BACKUP"
PROFILE_FILES="profile.md outreach.md cv.pdf photo.png photo.jpg"
REPLACE=0
YES=0
for arg in "$@"; do
  case "$arg" in
    --replace) REPLACE=1 ;;
    -y|--yes) YES=1 ;;
    -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "${RED}❌ Unknown option $arg (see --help)${RESET}" >&2; exit 2 ;;
    *) DIR="$arg" ;;
  esac
done

[ -d "$DIR" ] || { echo "${RED}❌ No such folder: $DIR${RESET}" >&2; exit 1; }

# the profile files of a backup (DIR/profile/): without --replace only the ones this copy does not
# have yet come back; with it they overwrite
restore_profile() {
  [ -d "$DIR/profile" ] || return 0
  mkdir -p profile
  for f in $PROFILE_FILES; do
    [ -f "$DIR/profile/$f" ] || continue
    if [ -f "profile/$f" ] && [ "$REPLACE" = 0 ]; then
      echo "${YELLOW}⏭️  Skipped profile/$f: it is already there (--replace overwrites it)${RESET}"
    else
      cp "$DIR/profile/$f" "profile/$f"
      case "$f" in *.md) chmod 600 "profile/$f" ;; esac
      echo "${GREEN}📄 Restored profile/$f${RESET}"
    fi
  done
}

# the .env of a backup folder (DIR/env/env; the dated copies in history/ don't have one)
restore_env() {
  [ -f "$DIR/env/env" ] || return 0
  if [ -f .env ] && [ "$REPLACE" = 0 ]; then
    echo "${YELLOW}⏭️  Skipped .env: it is already there (--replace overwrites it)${RESET}"
  else
    cp "$DIR/env/env" .env
    chmod 600 .env
    echo "${GREEN}🔑 Restored .env: restart the app (./stop.sh, ./run-local.sh) so it reads it${RESET}"
  fi
}

# the posts of the daily post skill (DIR/profile/daily-posts/): same rule, file by file
restore_daily_posts() {
  [ -d "$DIR/profile/daily-posts" ] || return 0
  mkdir -p profile/daily-posts
  restored=0; skipped=0
  for src in "$DIR"/profile/daily-posts/*; do
    [ -f "$src" ] || continue
    f="$(basename "$src")"
    if [ -f "profile/daily-posts/$f" ] && [ "$REPLACE" = 0 ]; then
      skipped=$((skipped + 1))
    else
      cp "$src" "profile/daily-posts/$f"
      restored=$((restored + 1))
    fi
  done
  echo "${GREEN}📄 Restored $restored file(s) of profile/daily-posts/${RESET}"
  if [ "$skipped" -gt 0 ]; then
    echo "${YELLOW}⏭️  Skipped $skipped file(s) of profile/daily-posts/ that are already there (--replace overwrites them)${RESET}"
  fi
}

if [ "$REPLACE" = 1 ]; then
  if [ "$YES" = 0 ]; then
    read -r -p "${YELLOW}⚠️  This empties the database, overwrites your profile files and loads $DIR. Continue? [y/N] ${RESET}" answer
    [ "$answer" = "y" ] || [ "$answer" = "Y" ] || { echo "${YELLOW}🚫 Cancelled.${RESET}"; exit 1; }
  fi
  SAFETY="$BACKUP/history/$(date +%Y-%m-%d_%H%M%S)_before-restore"
  .venv/bin/python server/cli.py export "$SAFETY"
  mkdir -p "$SAFETY/profile"
  for f in $PROFILE_FILES; do
    [ -f "profile/$f" ] && cp "profile/$f" "$SAFETY/profile/$f"
  done
  if [ -d profile/daily-posts ]; then cp -R profile/daily-posts "$SAFETY/profile/daily-posts"; fi
  if [ -f .env ]; then mkdir -p "$SAFETY/env"; chmod 700 "$SAFETY/env"; cp .env "$SAFETY/env/env"; chmod 600 "$SAFETY/env/env"; fi
  .venv/bin/python server/cli.py import "$DIR" --replace
  restore_profile
  restore_daily_posts
  restore_env
  echo "${BLUE}🗂️  What it replaced is in $SAFETY${RESET}"
else
  .venv/bin/python server/cli.py import "$DIR"
  restore_profile
  restore_daily_posts
  restore_env
fi
echo "${GREEN}✅ Restore finished.${RESET}"
