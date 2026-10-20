"""Exercise the backup shell scripts in disposable checkouts with a synthetic CLI.

The CLI stub supplies only export/import and backup-dir; database round trips are
covered in test_snapshot.py. These tests check actual shell filesystem behavior.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def checkout(tmp_path):
    repo = tmp_path / 'checkout'
    repo.mkdir()
    for script in ('backup-data.sh', 'restore-backup.sh'):
        shutil.copy2(ROOT / script, repo / script)
    (repo / '.venv/bin').mkdir(parents=True)
    cli = repo / '.venv/bin/python'
    cli.write_text(f'#!{sys.executable}\n' + '''import os, sys
from pathlib import Path
command = sys.argv[2]
if command == 'backup-dir':
    print(os.environ['TEST_BACKUP_ROOT'])
elif command == 'export':
    dest = Path(sys.argv[3])
    dest.mkdir(parents=True, exist_ok=True)
    (dest / 'calendar.csv').write_text('date,event\\n')
    (dest / 'companies.csv').write_text('name\\n')
elif command != 'import':
    raise SystemExit(1)
''')
    cli.chmod(0o700)
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    return repo


def run_script(repo, script, *args):
    return subprocess.run(
        ['bash', str(repo / script), *map(str, args)],
        env={**os.environ, 'TEST_BACKUP_ROOT': str(repo.parent / 'configured backup')},
        capture_output=True, text=True, check=True,
    )


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.mark.parametrize('source_exists', [False, True])
def test_backup_preserves_env_until_source_is_available(checkout, source_exists):
    saved = checkout.parent / 'configured backup/env/env'
    write(saved, 'SYNTHETIC=old\n')
    if source_exists:
        write(checkout / '.env', 'SYNTHETIC=new\n')
    run_script(checkout, 'backup-data.sh')
    assert saved.read_text() == ('SYNTHETIC=new\n' if source_exists else 'SYNTHETIC=old\n')


@pytest.mark.parametrize('kind', ['history', 'entry_override', 'direct'])
@pytest.mark.parametrize('existing_env', [False, True])
def test_restore_env_uses_selected_backup_root_and_preserves_existing(checkout, kind, existing_env):
    root = checkout.parent / 'imported backup'
    write(root / 'env/env', 'SYNTHETIC=root\n')
    entry = root if kind == 'direct' else root / 'history/2026-10-20_120000'
    entry.mkdir(parents=True, exist_ok=True)
    if kind == 'entry_override':
        write(entry / 'env/env', 'SYNTHETIC=entry\n')
    if existing_env:
        write(checkout / '.env', 'SYNTHETIC=local\n')
    run_script(checkout, 'restore-backup.sh', str(entry) + '/')
    expected = 'local' if existing_env else ('entry' if kind == 'entry_override' else 'root')
    assert (checkout / '.env').read_text() == f'SYNTHETIC={expected}\n'
    if not existing_env:
        assert (checkout / '.env').stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('replace', [False, True])
@pytest.mark.parametrize('has_posts', [False, True])
def test_daily_posts_restore_and_safety_copy(checkout, replace, has_posts):
    entry = checkout.parent / 'selected backup'
    entry.mkdir()
    posts = checkout / 'profile/daily-posts'
    write(posts / 'stale.png', 'old image')
    write(posts / 'shared.txt', 'old text')
    write(posts / 'log.csv', 'old log')
    write(checkout / '.env', 'SYNTHETIC=local\n')
    write(entry / 'env/env', 'SYNTHETIC=restored\n')
    if has_posts:
        write(entry / 'profile/daily-posts/shared.txt', 'restored text')
        write(entry / 'profile/daily-posts/new.png', 'restored image')
        write(entry / 'profile/daily-posts/log.csv', 'restored log')
    run_script(checkout, 'restore-backup.sh', entry, *(['--replace', '-y'] if replace else []))
    assert posts.is_dir()
    if replace:
        assert not (posts / 'stale.png').exists()
        safety, = (checkout.parent / 'configured backup/history').glob('*_before-restore')
        assert (safety / 'profile/daily-posts/stale.png').read_text() == 'old image'
        assert (safety / 'profile/daily-posts/shared.txt').read_text() == 'old text'
        assert (safety / 'env/env').read_text() == 'SYNTHETIC=local\n'
        assert (checkout / '.env').read_text() == 'SYNTHETIC=restored\n'
        if not has_posts:
            assert list(posts.iterdir()) == []
    else:
        assert (posts / 'stale.png').read_text() == 'old image'
        assert (checkout / '.env').read_text() == 'SYNTHETIC=local\n'
    if has_posts:
        assert (posts / 'new.png').read_text() == 'restored image'
        assert (posts / 'shared.txt').read_text() == ('restored text' if replace else 'old text')
        assert (posts / 'log.csv').read_text() == ('restored log' if replace else 'old log')
