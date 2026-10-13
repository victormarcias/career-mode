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
# backups, a profile/ folder (profile.md, outreach.md, cv.pdf, photo.*). Without --replace
# nothing is overwritten: what is already in the database or in profile/ is skipped and
# reported. With --replace the current data and profile files are first copied to
# <backup folder>/history/<date>_before-restore/, so they can be loaded back.
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || { echo "No .venv yet: run ./run-local.sh once first." >&2; exit 1; }
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
    -*) echo "Unknown option $arg (see --help)" >&2; exit 2 ;;
    *) DIR="$arg" ;;
  esac
done

[ -d "$DIR" ] || { echo "No such folder: $DIR" >&2; exit 1; }

# the profile files of a backup (DIR/profile/): without --replace only the ones this copy does not
# have yet come back; with it they overwrite
restore_profile() {
  [ -d "$DIR/profile" ] || return 0
  mkdir -p profile
  for f in $PROFILE_FILES; do
    [ -f "$DIR/profile/$f" ] || continue
    if [ -f "profile/$f" ] && [ "$REPLACE" = 0 ]; then
      echo "  skipped profile/$f: it is already there (--replace overwrites it)"
    else
      cp "$DIR/profile/$f" "profile/$f"
      case "$f" in *.md) chmod 600 "profile/$f" ;; esac
      echo "Restored profile/$f"
    fi
  done
}

if [ "$REPLACE" = 1 ]; then
  if [ "$YES" = 0 ]; then
    read -r -p "This empties the database, overwrites your profile files and loads $DIR. Continue? [y/N] " answer
    [ "$answer" = "y" ] || [ "$answer" = "Y" ] || { echo "Cancelled."; exit 1; }
  fi
  SAFETY="$BACKUP/history/$(date +%Y-%m-%d_%H%M%S)_before-restore"
  .venv/bin/python server/cli.py export "$SAFETY"
  mkdir -p "$SAFETY/profile"
  for f in $PROFILE_FILES; do
    [ -f "profile/$f" ] && cp "profile/$f" "$SAFETY/profile/$f"
  done
  .venv/bin/python server/cli.py import "$DIR" --replace
  restore_profile
  echo "What it replaced is in $SAFETY"
else
  .venv/bin/python server/cli.py import "$DIR"
  restore_profile
fi
