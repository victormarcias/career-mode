"""The user's own data lives in profile/ (gitignored); nothing of it may end up in a tracked file.

The check reads the real profile.md, when there is one, and looks for its contact details, name and birthdate in
every tracked text file. The values come from the profile itself, never from this test, so the test holds none.
Without a real profile (a fresh clone, CI) there is nothing to compare and it is skipped.
"""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / 'profile' / 'profile.md'
EXAMPLE = ROOT / 'profile' / 'profile.example.md'


def personal_values(text: str) -> set:
    """What would identify the person: emails, phone numbers, social handles, name, birthdate."""
    values = set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text))
    values |= set(re.findall(r'(?:linkedin\.com/in|github\.com|calendly\.com)/[\w.%-]+', text))
    for phone in re.findall(r'\+\d[\d ()-]{7,}\d', text):
        values |= {phone, re.sub(r'\D', '', phone)}
    values |= set(re.findall(r'\b\d{2}/\d{2}/\d{4}\b', text))
    name = re.search(r'\*\*Full name:\*\*\s*(.+)', text)
    if name:
        values.add(name.group(1).strip())
    return {v for v in values if len(v) >= 6}


def tracked_text_files():
    names = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True).stdout.decode().split('\0')
    for name in filter(None, names):
        path = ROOT / name
        if not path.is_file():
            continue  # deleted in the working tree
        try:
            yield name, path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue  # an image


def real_profile():
    if not PROFILE.is_file() or PROFILE.read_text() == EXAMPLE.read_text():
        pytest.skip('there is no real profile/profile.md to compare against')
    return PROFILE.read_text()


def test_the_values_of_a_profile_are_found_by_the_check():
    text = '- **Full name:** Jane Doe\n- Email: jane.doe@example.org\n- Phone: +1 555 010 0100\n- Born 02/03/1990\nlinkedin.com/in/jane-doe'
    found = personal_values(text)
    assert {'Jane Doe', 'jane.doe@example.org', '+1 555 010 0100', '15550100100', '02/03/1990', 'linkedin.com/in/jane-doe'} <= found


def test_no_tracked_file_holds_the_users_personal_data():
    values = personal_values(real_profile()) - personal_values(EXAMPLE.read_text())
    assert values, 'the profile has no contact details to look for'
    leaks = [(name, value) for name, text in tracked_text_files() for value in values if value.lower() in text.lower()]
    assert not leaks, 'personal data in a tracked file (file, value): %s' % [(n, v[:3] + '…') for n, v in leaks]
