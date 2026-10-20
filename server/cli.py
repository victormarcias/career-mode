#!/usr/bin/env python3
"""Command line for the career-mode database.

    python server/cli.py export [DIR]            write DIR/calendar.csv and DIR/companies.csv (default: BACKUP_DIR, or backup)
    python server/cli.py import DIR [--replace]  load those files; also reads the old JSON backups (agencies.json,
                                                 clients.json, events.json, and the Firestore applications.json).
                                                 --replace empties the database first
    python server/cli.py stats                   how many rows each table has
    python server/cli.py backup-dir              print the backup folder (BACKUP_DIR in .env or the shell, else backup)
    python server/cli.py profile-pdf [FILE]      a PDF of profile/profile.md to open in Google Docs (default: BACKUP_DIR/profile/profile.pdf);
                                                 needs Chrome or Chromium to print it
    python server/cli.py outreach-pdf [FILE]     the same for profile/outreach.md, your messages (default: BACKUP_DIR/profile/outreach.pdf)

Add `--db FILE` to use another database than data/career-mode.db. The CSV files are the
exchange format: a snapshot to keep, move to another computer or seed a new install.
"""
import argparse
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy import func, select  # noqa: E402

from app import models, snapshot  # noqa: E402
from app.database import ROOT, db_path_from_env, make_engine, migrate, session_factory  # noqa: E402
from app.profile_pdf import render_pdf  # noqa: E402
from app.settings import backup_dir  # noqa: E402

FILES = ('agencies', 'clients', 'events')
PROFILE_DIR = ROOT / 'profile'


def read_snapshot(directory):
    """(snapshot, warnings) from DIR/calendar.csv + companies.csv, or from the older JSON files."""
    texts = {}
    for key, filename in snapshot.CSV_FILES.items():
        path = os.path.join(directory, filename)
        if os.path.exists(path):
            with open(path, encoding='utf-8', newline='') as f:
                texts[key] = f.read()
    if texts:
        try:
            return snapshot.parse_csv(**texts)
        except ValueError as err:
            sys.exit(str(err))
    data = {}
    for name in FILES + ('applications',):  # "applications" is what the Firestore backups called events
        path = os.path.join(directory, name + '.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                data[name] = json.load(f)
    if not any(data.get(k) for k in FILES + ('applications',)):
        sys.exit('No calendar.csv or companies.csv (nor the older JSON files) found in %s' % directory)
    return data, []


def markdown_pdf(name, out):
    """Writes the PDF of profile/<name>.md to `out`, or exits saying what is missing."""
    source = PROFILE_DIR / (name + '.md')
    if not source.is_file():
        sys.exit('There is no profile/%s.md to make a PDF of' % name)
    text = source.read_text(encoding='utf-8')
    title = next((line.lstrip('# ').strip() for line in text.splitlines() if line.startswith('# ')), name.capitalize())
    try:
        return render_pdf(text, out, title=title)
    except RuntimeError as err:
        sys.exit(str(err))


def main(argv=None):
    """Parse argv and run a database, backup-directory, or Markdown PDF command."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('export', 'import', 'stats', 'backup-dir', 'profile-pdf', 'outreach-pdf'))
    parser.add_argument('directory', nargs='?')
    parser.add_argument('--db', default=str(db_path_from_env()))
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args(argv)

    if args.command == 'backup-dir':  # for the scripts: no database involved
        print(backup_dir())
        return
    if args.command in ('profile-pdf', 'outreach-pdf'):  # no database involved either
        name = args.command.split('-')[0]
        print(markdown_pdf(name, args.directory or os.path.join(backup_dir(), 'profile', name + '.pdf')))
        return
    migrate(args.db)
    engine = make_engine(args.db)
    with session_factory(engine)() as session:
        if args.command == 'stats':
            for model in (models.Agency, models.AgencyRecruiter, models.Client, models.Event):
                print('%-18s %d' % (model.__tablename__, session.scalar(select(func.count()).select_from(model))))
        elif args.command == 'export':
            directory = args.directory or backup_dir()
            os.makedirs(directory, exist_ok=True)
            for name, text in snapshot.export_csv(session).items():
                path = os.path.join(directory, snapshot.CSV_FILES[name])
                with open(path, 'w', encoding='utf-8', newline='') as f:
                    f.write(text)
                print('Wrote %d rows to %s' % (len(list(csv.reader(io.StringIO(text, newline='')))) - 1, path))
        else:
            if not args.directory:
                sys.exit('import needs a directory')
            data, read_warnings = read_snapshot(args.directory)
            report = snapshot.import_snapshot(session, data, replace=args.replace)
            report['warnings'] = read_warnings + report['warnings']
            print('Imported %(agencies)d agencies, %(clients)d clients, %(events)d events.' % report)
            for line in report['warnings']:
                print('  warning:', line)
            for line in report['skipped']:
                print('  skipped:', line)
    engine.dispose()


if __name__ == '__main__':
    main()
