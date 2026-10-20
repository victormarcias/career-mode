"""Settings: the local environment variables kept in .env."""
import os
import stat

import pytest

from app import settings
from app.database import DEFAULT_DB_PATH, ROOT, alembic_config

SECRET = 'AIzaSyD-this-is-a-fake-key-0123456789'
VARIABLES = {
    'APP_LANGUAGE', 'CV_PDF_PATH', 'EMAIL_ADDRESS', 'EMAIL_PASSWORD',
    'EMAIL_SMTP_HOST', 'EMAIL_SMTP_PORT', 'GEMINI_API_KEY', 'GOOGLE_CALENDAR_ID',
}
SECRETS = {'EMAIL_PASSWORD', 'GEMINI_API_KEY', 'GOOGLE_CALENDAR_ID'}


def by_name(rows):
    return {r['name']: r for r in rows}


def test_lists_every_known_variable_with_nothing_set(client):
    rows = by_name(client.get('/api/settings/env').json())
    assert set(rows) == VARIABLES
    assert list(rows) == sorted(rows)  # Settings lists them A-Z
    assert all(not r['isSet'] and r['value'] is None and r['length'] is None for r in rows.values())
    assert {name for name, r in rows.items() if r['secret']} == SECRETS
    assert all(r['restartRequired'] is False for r in rows.values())
    assert {n: rows[n]['default'] for n in ('APP_LANGUAGE', 'EMAIL_SMTP_HOST', 'EMAIL_SMTP_PORT')} == {
        'APP_LANGUAGE': 'en', 'EMAIL_SMTP_HOST': 'smtp.gmail.com', 'EMAIL_SMTP_PORT': '465',
    }
    assert rows['APP_LANGUAGE']['choices'] == ['en', 'es'] and rows['EMAIL_SMTP_HOST']['choices'] is None


def test_a_secret_is_never_sent_back_in_full(client, env_path):
    r = client.put('/api/settings/env', json={'values': {'GEMINI_API_KEY': SECRET}})
    assert r.status_code == 200
    key = by_name(r.json())['GEMINI_API_KEY']
    assert (key['isSet'], key['value'], key['length']) == (True, None, len(SECRET))  # its size, never its content
    assert SECRET not in r.text and SECRET not in client.get('/api/settings/env').text
    assert 'GEMINI_API_KEY=%s' % SECRET in env_path.read_text()  # but it is in the file, where it belongs


def test_the_length_is_the_real_one_whatever_it_is(client):
    for secret in ('short', 'x' * 120):
        r = client.put('/api/settings/env', json={'values': {'GEMINI_API_KEY': secret}})
        assert by_name(r.json())['GEMINI_API_KEY']['length'] == len(secret)
    client.put('/api/settings/env', json={'values': {'GEMINI_API_KEY': None}})
    assert by_name(client.get('/api/settings/env').json())['GEMINI_API_KEY']['length'] is None


def test_plain_values_come_back_as_they_are(client):
    r = client.put('/api/settings/env', json={'values': {'EMAIL_SMTP_PORT': ' 587 ', 'EMAIL_SMTP_HOST': 'smtp.example.org'}})
    rows = by_name(r.json())
    assert (rows['EMAIL_SMTP_PORT']['value'], rows['EMAIL_SMTP_HOST']['value']) == ('587', 'smtp.example.org')


def test_the_file_is_private(client, env_path):
    client.put('/api/settings/env', json={'values': {'EMAIL_SMTP_PORT': '587'}})
    assert stat.S_IMODE(os.stat(env_path).st_mode) == 0o600


def test_everything_else_in_the_file_is_left_alone(client, env_path):
    env_path.write_text('# my notes\nSOMETHING_ELSE=keep me\n\nEMAIL_SMTP_PORT=465\nexport OTHER="x y"\n')
    client.put('/api/settings/env', json={'values': {'EMAIL_SMTP_PORT': '587', 'GEMINI_API_KEY': SECRET}})
    assert env_path.read_text() == '# my notes\nSOMETHING_ELSE=keep me\n\nEMAIL_SMTP_PORT=587\nexport OTHER="x y"\nGEMINI_API_KEY=%s\n' % SECRET


def test_null_or_blank_removes_a_variable_and_only_that_one(client, env_path):
    env_path.write_text('EMAIL_SMTP_PORT=587\nEMAIL_SMTP_HOST=smtp.example.org\n# keep\n')
    client.put('/api/settings/env', json={'values': {'EMAIL_SMTP_PORT': None}})
    assert env_path.read_text() == 'EMAIL_SMTP_HOST=smtp.example.org\n# keep\n'
    client.put('/api/settings/env', json={'values': {'EMAIL_SMTP_HOST': '  '}})
    assert env_path.read_text() == '# keep\n'


def test_variables_not_mentioned_are_not_touched(client, env_path):
    env_path.write_text('EMAIL_SMTP_PORT=587\n')
    client.put('/api/settings/env', json={'values': {'GEMINI_API_KEY': SECRET}})
    assert by_name(client.get('/api/settings/env').json())['EMAIL_SMTP_PORT']['value'] == '587'


def test_a_file_that_does_not_exist_is_created(client, env_path):
    assert not env_path.exists()
    client.put('/api/settings/env', json={'values': {'EMAIL_SMTP_PORT': '587'}})
    assert env_path.read_text() == 'EMAIL_SMTP_PORT=587\n'


@pytest.mark.parametrize('values', [
    {'EMAIL_SMTP_PORT': 'eight'}, {'EMAIL_SMTP_PORT': '25'}, {'EMAIL_SMTP_PORT': '465\n587'},
    {'EMAIL_ADDRESS': 'not an address'}, {'EMAIL_ADDRESS': 'a@b'}, {'EMAIL_SMTP_HOST': 'not a host'},
    {'APP_LANGUAGE': 'fr'}, {'CV_PDF_PATH': '/does/not/exist.pdf'},
    {'GEMINI_API_KEY': 'has a space'}, {'PATH': '/usr/bin'}, {'HOME': 'x'},
])
def test_what_does_not_validate_is_refused_and_nothing_is_written(client, env_path, values):
    r = client.put('/api/settings/env', json={'values': values})
    assert r.status_code == 422 and r.json()['detail']
    assert not env_path.exists()


def test_one_bad_value_stops_the_whole_update(client, env_path):
    r = client.put('/api/settings/env', json={'values': {'GEMINI_API_KEY': SECRET, 'EMAIL_SMTP_PORT': 'eight'}})
    assert r.status_code == 422
    assert not env_path.exists()


def test_the_language_is_a_choice_and_english_is_the_default(client, env_path):
    assert by_name(client.get('/api/settings/env').json())['APP_LANGUAGE']['value'] is None  # not set: the page uses `en`
    r = client.put('/api/settings/env', json={'values': {'APP_LANGUAGE': 'es'}})
    assert by_name(r.json())['APP_LANGUAGE']['value'] == 'es'
    assert client.put('/api/settings/env', json={'values': {'APP_LANGUAGE': 'Spanish'}}).json()['detail'] == 'Choose one of: en, es'
    assert settings.read_env_file(env_path)['APP_LANGUAGE'] == 'es'


def test_the_email_settings_are_checked(client):
    ok = {'EMAIL_ADDRESS': 'jane@example.org', 'EMAIL_SMTP_HOST': 'smtp.example.org', 'EMAIL_SMTP_PORT': '587', 'EMAIL_PASSWORD': 'abcd efgh'}
    rows = by_name(client.put('/api/settings/env', json={'values': ok}).json())
    assert rows['EMAIL_ADDRESS']['value'] == 'jane@example.org' and rows['EMAIL_PASSWORD']['value'] is None
    assert rows['EMAIL_PASSWORD']['isSet'] and rows['EMAIL_PASSWORD']['length'] == len('abcd efgh')


def test_a_cv_must_be_a_small_pdf(client, tmp_path):
    pdf = tmp_path / 'cv.pdf'
    pdf.write_bytes(b'%PDF-1.4 fake')
    assert client.put('/api/settings/env', json={'values': {'CV_PDF_PATH': str(pdf)}}).status_code == 200
    text = tmp_path / 'cv.txt'
    text.write_text('not a pdf')
    assert client.put('/api/settings/env', json={'values': {'CV_PDF_PATH': str(text)}}).status_code == 422
    big = tmp_path / 'big.pdf'
    big.write_bytes(b'%PDF-' + b'0' * settings.MAX_CV_BYTES)
    assert client.put('/api/settings/env', json={'values': {'CV_PDF_PATH': str(big)}}).status_code == 422


def test_the_old_calendar_name_still_works_until_the_new_one_is_saved(client, env_path):
    env_path.write_text('CALENDAR_ID=me@example.com\nKEEP=1\n')
    row = by_name(client.get('/api/settings/env').json())['GOOGLE_CALENDAR_ID']
    assert row['isSet'] and row['length'] == len('me@example.com')
    client.put('/api/settings/env', json={'values': {'GOOGLE_CALENDAR_ID': 'you@example.com'}})
    assert settings.read_env_file(env_path) == {'KEEP': '1', 'GOOGLE_CALENDAR_ID': 'you@example.com'}


def test_values_with_spaces_and_quotes_survive_a_round_trip(client, env_path, tmp_path):
    cv = tmp_path / 'my "best" CV #1.pdf'
    cv.write_bytes(b'%PDF-1.4\n')
    tricky = str(cv)
    client.put('/api/settings/env', json={'values': {'CV_PDF_PATH': tricky}})
    assert settings.read_env_file(env_path)['CV_PDF_PATH'] == tricky
    assert by_name(client.get('/api/settings/env').json())['CV_PDF_PATH']['value'] == tricky


def test_reading_the_file(tmp_path):
    path = tmp_path / 'env'
    path.write_text('# comment\n\nA=1\nexport B="two words"\nC=\'three words\'\nD=four # a comment\nE=\n  F = 6\n#G=7\nnot a line\n')
    assert settings.read_env_file(path) == {'A': '1', 'B': 'two words', 'C': 'three words', 'D': 'four', 'E': '', 'F': '6'}
    assert settings.read_env_file(tmp_path / 'missing') == {}


def test_the_file_never_overrides_what_is_already_exported(tmp_path, monkeypatch):
    path = tmp_path / 'env'
    path.write_text('EMAIL_SMTP_PORT=587\nSOME_OTHER_SETTING=from-file\n')
    monkeypatch.setenv('EMAIL_SMTP_PORT', '465')
    monkeypatch.delenv('SOME_OTHER_SETTING', raising=False)
    settings.load_env_file(path)
    assert os.environ['EMAIL_SMTP_PORT'] == '465' and os.environ['SOME_OTHER_SETTING'] == 'from-file'
    monkeypatch.delenv('SOME_OTHER_SETTING')


def test_the_database_and_the_backups_have_fixed_places_that_no_variable_moves(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('CAREER_MODE_DB', str(tmp_path / 'elsewhere.db'))
    monkeypatch.setenv('BACKUP_DIR', str(tmp_path / 'elsewhere'))
    assert DEFAULT_DB_PATH == ROOT / 'data' / 'career-mode.db'
    assert alembic_config().get_main_option('sqlalchemy.url') == 'sqlite:///%s' % DEFAULT_DB_PATH
    import cli
    cli.main(['backup-dir'])
    assert capsys.readouterr().out.strip() == 'backup'
    assert not {'BACKUP_DIR', 'CAREER_MODE_DB'} & set(settings.BY_NAME)
