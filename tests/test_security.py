"""What the server will and won't hand out, and to whom."""
import socket

import pytest

SERVED = ['/', '/index.html', '/style.css', '/js/main.js', '/js/i18n.js', '/navigation/favicon.png', '/locales/en.json', '/locales/es.json']
NOT_SERVED = [
    '/data/career-mode.db', '/.env', '/server/app/main.py', '/server/alembic.ini', '/backup/agencies.json',
    '/scripts/generate_daily_image.py', '/.git/config', '/README.md', '/requirements.txt', '/.venv/pyvenv.cfg',
    '/.claude/settings.local.json', '/.claude/skills/apply-email/SKILL.md', '/.claude/skills/apply-email/../../settings.local.json',
    '/js/../.env', '/%2e%2e/.env', '/js/%2e%2e/%2e%2e/.env', '/public/../data/career-mode.db',
    '/public/index.html', '/public/js/main.js',  # public/ is the root now, not a folder to ask for
    '/profile/profile.md', '/profile/profile.example.md', '/profile/outreach.md', '/profile/cv.pdf', '/profile/photo.png',
    '/profile-files/cv.pdf', '/profile-files/profile.md',  # the profile folder is never served as a folder: only the routes below
]


@pytest.mark.parametrize('path', SERVED)
def test_the_apps_own_files_are_served(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize('path', NOT_SERVED)
def test_nothing_else_is_served(client, path):
    assert client.get(path).status_code in (404, 400)


@pytest.mark.parametrize('path', NOT_SERVED)
def test_nothing_else_is_served_even_with_the_raw_path_untouched(live_server, path):
    """The test client tidies "../" before sending; a browser-less socket doesn't."""
    port, _ = live_server
    with socket.create_connection(('127.0.0.1', port), timeout=5) as sock:
        sock.sendall(('GET %s HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' % path).encode())
        reply = b''
        while chunk := sock.recv(65536):
            reply += chunk
    assert reply.split(b' ', 2)[1] in (b'404', b'400'), reply[:200]
    assert b'GEMINI' not in reply and b'SQLite format' not in reply


def test_static_files_have_the_right_type_and_are_never_cached(client):
    r = client.get('/js/main.js')
    assert 'javascript' in r.headers['content-type']
    assert r.headers['cache-control'] == 'no-store'
    assert client.get('/api/events').headers['cache-control'] == 'no-store'


def test_a_foreign_host_name_is_refused(client):  # DNS rebinding
    assert client.get('/api/events', headers={'Host': 'evil.example'}).status_code == 403
    assert client.get('/', headers={'Host': 'evil.example'}).status_code == 403
    assert client.get('/api/events', headers={'Host': 'localhost:1234'}).status_code == 200
    assert client.get('/api/events', headers={'Host': '[::1]:8333'}).status_code == 200
    assert client.get('/api/events', headers={'Host': '127.0.0.1.evil.example'}).status_code == 403


def test_writes_from_another_site_are_refused(client):
    body = {'name': 'Hacked'}
    assert client.post('/api/agencies', json=body, headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.post('/api/agencies', json=body, headers={'Origin': 'http://testserver'}).status_code == 201
    assert client.get('/api/events', headers={'Origin': 'https://evil.example'}).status_code == 200  # reading is the browser's own job to block


def test_a_write_must_be_json(client):
    assert client.post('/api/agencies', content=b'name=x', headers={'Content-Type': 'application/x-www-form-urlencoded'}).status_code == 422
    assert client.post('/api/agencies', content=b'{broken', headers={'Content-Type': 'application/json'}).status_code == 422
    assert client.post('/api/agencies', content=b'[1]', headers={'Content-Type': 'application/json'}).status_code == 422


def test_unknown_routes_and_methods(client):
    assert client.get('/api/nothing').status_code == 404
    assert client.post('/api/events/some-id', json={}).status_code == 405
    assert client.delete('/api/events').status_code == 405
    assert client.post('/index.html', json={}).status_code == 405


def make_client(tmp_path, profile=None):
    from fastapi.testclient import TestClient

    from app.main import LOCAL_HOSTS, create_app

    return TestClient(create_app(
        tmp_path / 'test.db', allowed_hosts=LOCAL_HOSTS + ('testserver',), env_path=tmp_path / '.env', profile_dir=profile,
    ))


def write(folder, **files):
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (folder / name).write_text(text)
    return folder


@pytest.mark.parametrize('stem', ['outreach', 'profile'])
def test_the_profile_and_the_messages_are_the_users_own_file(tmp_path, stem):
    folder = write(tmp_path / 'profile', **{'%s.md' % stem: 'MINE', '%s.example.md' % stem: 'EXAMPLE'})
    with make_client(tmp_path, folder) as client:
        r = client.get('/%s.md' % stem)
        assert (r.status_code, r.text) == (200, 'MINE')
        assert r.headers['content-type'].startswith('text/markdown') and r.headers['cache-control'] == 'no-store'
        assert r.headers['x-profile-example'] == 'false'


@pytest.mark.parametrize('stem', ['outreach', 'profile'])
def test_until_there_is_one_the_example_is_served_and_says_so(tmp_path, stem):
    folder = write(tmp_path / 'profile', **{'%s.example.md' % stem: 'EXAMPLE'})
    with make_client(tmp_path, folder) as client:
        r = client.get('/%s.md' % stem)
        assert (r.text, r.headers['x-profile-example']) == ('EXAMPLE', 'true')


def test_an_untouched_copy_of_the_example_still_counts_as_the_example(tmp_path):
    folder = write(tmp_path / 'profile', **{'profile.md': 'SAME', 'profile.example.md': 'SAME'})
    with make_client(tmp_path, folder) as client:
        assert client.get('/profile.md').headers['x-profile-example'] == 'true'
    (folder / 'profile.md').write_text('EDITED')
    with make_client(tmp_path, folder) as client:
        assert client.get('/profile.md').headers['x-profile-example'] == 'false'


def test_with_neither_there_is_nothing_to_serve(tmp_path):
    with make_client(tmp_path, tmp_path / 'nothing-here') as client:
        assert client.get('/profile.md').status_code == 404 and client.get('/outreach.md').status_code == 404


def test_only_those_two_files_and_the_photo_leave_the_profile_folder(tmp_path):
    folder = write(tmp_path / 'profile', **{'profile.md': 'P', 'outreach.md': 'O', 'notes.md': 'SECRET'})
    (folder / 'cv.pdf').write_bytes(b'%PDF-1.4 SECRET')
    (folder / 'photo.png').write_bytes(b'\x89PNG\r\n\x1a\nSECRET')
    with make_client(tmp_path, folder) as client:
        for path in ('/notes.md', '/cv.pdf', '/profile/notes.md', '/profile/cv.pdf', '/profile-files/cv.pdf', '/profile-files/notes.md'):
            r = client.get(path)
            assert r.status_code == 404 and 'SECRET' not in r.text, path
        photo = client.get('/profile-files/photo')
        assert photo.status_code == 200 and photo.headers['content-type'] == 'image/png'


def test_without_a_photo_there_is_no_photo_route(tmp_path):
    with make_client(tmp_path, write(tmp_path / 'profile')) as client:
        assert client.get('/profile-files/photo').status_code == 404


def test_the_examples_are_a_complete_invented_person():
    """profile/*.example.md ship with the repo: they hold the pieces the skills need (and, by design, only invented data)."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / 'profile'
    profile = (root / 'profile.example.md').read_text(encoding='utf-8')
    for field in ('Full name', 'Email', 'Phone', 'Birthdate', 'Google account operated by Claude', 'Chat language',
                  'Expected salary range', 'Website', 'Notes folder'):
        assert field in profile, field
    for heading in ('## 👤 Basics', '## 🎯 Roles', '## 🛠️ Tech stack', '## 🌍 Work preferences', '## 🎓 Self-assessment', '## 📝 Short bio', '## 📏 Rules'):
        assert heading in profile, heading
    messages = (root / 'outreach.example.md').read_text(encoding='utf-8')
    assert [line for line in messages.splitlines() if line.startswith('## ')] == [
        '## 📝 Platform Reachout Message', '## 📝 Proposal Reply Message', '## 📝 Application by Email Message',
        '## 📝 Application Follow-up Message', '## 📝 Application Rejected Message', '## 📝 Cover Letter Message',
    ]
    assert messages.count('### 🇪🇸 Spanish') == messages.count('### 🇬🇧 English') == 6  # one text per language, every message
    assert 'Juan Perez' in profile  # that they hold no real data is tests/test_no_personal_data.py's job
