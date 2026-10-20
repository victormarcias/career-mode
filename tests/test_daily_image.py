"""The daily post image script: what it asks Gemini for. Gemini is never called; everything here is invented text."""
import base64
import importlib.util
import json
import stat
import subprocess

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('generate_daily_image', ROOT / 'scripts' / 'generate_daily_image.py')
image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image)


def test_the_prompt_asks_for_correct_spelling_and_little_text():
    """Verify image instructions request checked spelling, minimal text, and no code."""
    assert 'check spelling errors' in image.PROMPT_PREFIX
    assert 'Minimal text' in image.PROMPT_PREFIX
    assert 'Do not write function names or code' in image.PROMPT_PREFIX


def test_the_env_file_is_read_without_comments_or_blank_lines(tmp_path):
    """Verify environment parsing ignores comments and blanks and tolerates a missing file."""
    env = tmp_path / '.env'
    env.write_text('# a comment\n\nGEMINI_API_KEY=test-key\nOTHER=1\n')
    assert image.load_env(str(env)) == {'GEMINI_API_KEY': 'test-key', 'OTHER': '1'}
    assert image.load_env(str(tmp_path / 'missing')) == {}


@pytest.mark.parametrize('outcome', ['success', 'curl_timeout', 'process_timeout', 'api_error', 'launch_error'])
def test_request_is_bounded_and_secret_header_is_always_removed(tmp_path, monkeypatch, capsys, outcome):
    post = tmp_path / 'post.txt'
    post.write_text('An invented reflection.')
    output = tmp_path / 'post.png'
    key = 'synthetic-gemini-key'
    monkeypatch.setattr(image, 'load_env', lambda path: {'GEMINI_API_KEY': key})
    monkeypatch.setattr(image.sys, 'argv', ['generate_daily_image.py', str(post), str(output)])
    header_paths = []

    def run(args, **kwargs):
        assert key not in ' '.join(args)
        assert 0 < float(args[args.index('--max-time') + 1]) < kwargs['timeout'] <= 180
        headers = Path(next(arg[1:] for arg in args if arg.startswith('@/')))
        header_paths.append(headers)
        assert stat.S_IMODE(headers.stat().st_mode) == 0o600
        assert headers.read_text() == f'x-goog-api-key: {key}\n'
        assert 'An invented reflection.' in json.loads(kwargs['input'])['contents'][0]['parts'][0]['text']
        if outcome == 'process_timeout':
            raise subprocess.TimeoutExpired(args, kwargs['timeout'])
        if outcome == 'launch_error':
            raise OSError('curl unavailable')
        if outcome == 'curl_timeout':
            return subprocess.CompletedProcess(args, 28, '', 'Operation timed out')
        data = {'candidates': [{'content': {'parts': [{'inlineData': {'data': base64.b64encode(b'image bytes').decode()}}]}}]}
        if outcome == 'api_error':
            data = {'error': {'message': 'Synthetic provider error'}}
        return subprocess.CompletedProcess(args, 0, json.dumps(data), '')

    monkeypatch.setattr(image.subprocess, 'run', run)
    if outcome == 'success':
        image.main()
        assert output.read_bytes() == b'image bytes'
    elif outcome == 'launch_error':
        with pytest.raises(OSError):
            image.main()
    else:
        with pytest.raises(SystemExit) as exc:
            image.main()
        assert exc.value.code == 1
    assert len(header_paths) == 1  # no automatic retry
    assert not header_paths[0].exists()
    assert post.read_text() == 'An invented reflection.'
    if outcome != 'success':
        assert not output.exists()
    captured = capsys.readouterr()
    assert key not in captured.out + captured.err
