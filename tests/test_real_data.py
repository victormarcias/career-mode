"""The user's own database holds its recruiters the way the app reads them.

The Recruiters field of the event form shows the leading `Recruiter:` lines of an event's notes: each holds one
recruiter, as a LinkedIn profile, an email or just a name (the rule of isRecruiter in public/js/application-form.js).
A company's `recruiters` list holds LinkedIn profiles only. A note written there shows in the wrong field. This
reads a copy of the real database (data/career-mode.db) through the API, so the real file is never touched, and
lists every event or company that breaks it. Without a real database
(a fresh clone, CI) there is nothing to check and it is skipped. It holds no personal data: what it reports comes
from the database at run time.
"""
import re
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.database import DEFAULT_DB_PATH
from app.main import LOCAL_HOSTS, create_app

# The same rules as public/js/application-form.js: a LinkedIn /in/ profile, an email, or a bare name.
PROFILE = re.compile(r'^(https?://)?([a-z]{2,3}\.)?linkedin\.com/in/[^/\s]+/?\S*$', re.I)
EMAIL = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
NAME = re.compile(r"^[^\W\d_](?:[^\W\d_]|[ .'’-]){0,59}$")  # a letter, then letters, spaces, . ' ’ -


def is_recruiter(value):
    return bool(PROFILE.match(value) or EMAIL.match(value) or NAME.match(value))


pytestmark = pytest.mark.skipif(not DEFAULT_DB_PATH.exists(), reason='no real database to check')


@pytest.fixture(scope='module')
def real(tmp_path_factory):
    """The app on a consistent copy of the real database (SQLite's backup, so a running server is no problem)."""
    folder = tmp_path_factory.mktemp('real')
    copy = folder / 'copy.db'
    source, target = sqlite3.connect(f'file:{DEFAULT_DB_PATH}?mode=ro', uri=True), sqlite3.connect(copy)
    source.backup(target)
    source.close()
    target.close()
    with TestClient(create_app(copy, allowed_hosts=LOCAL_HOSTS + ('testserver',), env_path=folder / '.env')) as c:
        yield c


def leading_recruiters(notes):
    lines = (notes or '').split('\n')
    values = []
    while lines and lines[0].startswith('Recruiter:'):
        values.append(lines.pop(0)[len('Recruiter:'):].strip())
    return values


def test_event_recruiter_lines_hold_one_recruiter(real):
    bad = [f"{e['id']} ({e.get('companyLabel')}): {value[:80]}"
           for e in real.get('/api/events').json()
           for value in leading_recruiters(e.get('notes'))
           if value and not is_recruiter(value)]
    assert not bad, f'{len(bad)} Recruiter: lines are not a profile, an email or a name:\n' + '\n'.join(bad)


def test_company_recruiters_are_profile_links(real):
    bad = [f"{c['id']}: {value[:80]}"
           for c in real.get('/api/companies').json()
           for value in c.get('recruiters') or []
           if not PROFILE.match(value)]
    assert not bad, f'{len(bad)} company recruiters are not a LinkedIn profile:\n' + '\n'.join(bad)
