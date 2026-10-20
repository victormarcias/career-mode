"""The daily post image script: what it asks Gemini for. Gemini is never called; everything here is invented text."""
import importlib.util
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
