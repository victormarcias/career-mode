"""The profile as a PDF for the backup: the markdown to HTML, finding a browser, and printing with it.

No test needs a real browser: a small shell script stands in for it (it writes a fake PDF where it is told to and
keeps what it was given), so they run the same in CI. Everything here is invented text.
"""
import html as htmllib
import stat
from pathlib import Path

import pytest

import cli
from app import profile_pdf
from app.profile_pdf import document_html, find_browser, markdown_to_html, render_pdf

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = (ROOT / 'profile' / 'profile.example.md').read_text(encoding='utf-8')


# ---------- markdown to HTML ----------


def test_headings_keep_their_level():
    """Verify Markdown heading levels and Unicode titles survive conversion."""
    html = markdown_to_html('# Title\n\n## 👤 Basics\n\n### Detail')
    assert '<h1>Title</h1>' in html and '<h2>👤 Basics</h2>' in html and '<h3>Detail</h3>' in html


def test_a_bullet_with_a_bold_label_and_a_link():
    """Verify list items retain bold labels and HTTP links."""
    html = markdown_to_html('- **Website:** [site.example](https://site.example) and more')
    assert html == '<ul><li><strong>Website:</strong> <a href="https://site.example">site.example</a> and more</li></ul>'


def test_nested_lists_and_a_paragraph_under_an_item():
    """Verify nested and ordered lists and indented paragraphs retain their structure."""
    html = markdown_to_html('- **Role, Company** — 2020–Present\n  - First bullet\n  - Second bullet\n- Next\n\n1. one\n2. two')
    assert html == (
        '<ul><li><strong>Role, Company</strong> — 2020–Present<ul><li>First bullet</li><li>Second bullet</li></ul></li><li>Next</li></ul>\n'
        '<ol><li>one</li><li>two</li></ol>'
    )
    assert '<li>Item<p>more text</p></li>' in markdown_to_html('- Item\n\n  more text')


def test_a_code_block_is_kept_as_written_and_escaped():
    """Verify fenced code preserves whitespace and literal Markdown while escaping HTML."""
    html = markdown_to_html('```\nline <one>\n  line **two**\n```')
    assert html == '<pre><code>line &lt;one&gt;\n  line **two**</code></pre>'


def test_inline_code_is_never_read_as_bold_or_a_link_and_text_is_escaped():
    """Verify inline code stays literal and surrounding HTML characters are escaped."""
    html = markdown_to_html('Run `**x** [a](https://a.example)` <script>alert(1)</script> & done')
    assert '<code>**x** [a](https://a.example)</code>' in html
    assert '<script>' not in html and '&lt;script&gt;' in html and '&amp; done' in html


def test_a_link_only_accepts_http_and_mailto():
    """Verify JavaScript links stay unlinked while mailto links are rendered."""
    assert '<a ' not in markdown_to_html('[bad](javascript:alert(1))')
    assert '<a href="mailto:a@b.example">mail</a>' in markdown_to_html('[mail](mailto:a@b.example)')


def test_lines_of_one_paragraph_are_joined():
    """Verify adjacent text lines merge into paragraphs separated by blank lines."""
    assert markdown_to_html('first line\nsecond line\n\nnext') == '<p>first line second line</p>\n<p>next</p>'


def test_the_example_profile_keeps_every_section_and_leaves_no_markdown_behind():
    """Verify the example profile retains section headings and renders supported Markdown."""
    html = markdown_to_html(EXAMPLE)
    for line in EXAMPLE.splitlines():
        if line.startswith('## '):
            assert '<h2>%s</h2>' % htmllib.escape(line[3:].strip()) in html
    assert '**' not in html and '```' not in html and '<pre>' in html


def test_the_document_has_a_title_and_a_style():
    """Verify the complete document includes an escaped title, print styles, and rendered content."""
    html = document_html('# Hi', title='Profile — Juan <Perez>')
    assert '<title>Profile — Juan &lt;Perez&gt;</title>' in html and '@page' in html and '<h1>Hi</h1>' in html


# ---------- finding a browser and printing with it ----------


@pytest.fixture
def fake_browser(tmp_path):
    """A script that behaves like `chrome --headless --print-to-pdf=FILE page.html`."""
    log = tmp_path / 'browser.log'
    script = tmp_path / 'fake-chrome'
    script.write_text(
        '#!/bin/sh\n'
        'echo "$@" >> "%(log)s"\n'
        'for arg in "$@"; do\n'
        '  case "$arg" in\n'
        '    --print-to-pdf=*) out="${arg#--print-to-pdf=}" ;;\n'
        '    file://*) cat "${arg#file://}" > "%(log)s.html" ;;\n'
        '  esac\n'
        'done\n'
        'printf "%%%%PDF-1.4 fake" > "$out"\n' % {'log': log}
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script, log


@pytest.fixture
def no_browser(monkeypatch):
    """Simulate an environment with no browser override or discoverable browser."""
    monkeypatch.delenv('CAREER_MODE_BROWSER', raising=False)
    monkeypatch.setattr(profile_pdf.shutil, 'which', lambda name: None)
    monkeypatch.setattr(profile_pdf, 'MAC_APPS', ())


def test_the_browser_can_be_named_and_a_wrong_name_finds_none(fake_browser, monkeypatch, tmp_path):
    """Verify an executable browser override is accepted and a missing path is rejected."""
    monkeypatch.setenv('CAREER_MODE_BROWSER', str(fake_browser[0]))
    assert find_browser() == str(fake_browser[0])
    monkeypatch.setenv('CAREER_MODE_BROWSER', str(tmp_path / 'missing'))
    assert find_browser() is None


def test_a_browser_on_the_path_is_found(no_browser, monkeypatch):
    """Verify browser discovery returns Chromium from the executable search path."""
    monkeypatch.setattr(profile_pdf.shutil, 'which', lambda name: '/usr/bin/chromium' if name == 'chromium' else None)
    assert find_browser() == '/usr/bin/chromium'


def test_no_browser_means_no_pdf_and_says_so(no_browser, tmp_path):
    """Verify a missing browser raises an explanatory error without creating a PDF."""
    with pytest.raises(RuntimeError, match='No Chrome or Chromium'):
        render_pdf('# Hi', tmp_path / 'out.pdf')
    assert not (tmp_path / 'out.pdf').exists()


def test_the_pdf_is_printed_without_header_and_with_a_throwaway_profile(fake_browser, tmp_path):
    """Verify printing uses a temporary browser profile, omits headers, and saves the PDF."""
    script, log = fake_browser
    out = render_pdf('# Hi\n\n- **a:** b', tmp_path / 'deep' / 'out.pdf', title='Hi', browser=str(script))
    assert out.read_bytes().startswith(b'%PDF-')
    args = log.read_text()
    assert '--headless=new' in args and '--no-pdf-header-footer' in args and '--user-data-dir=' in args
    assert '<h1>Hi</h1>' in Path(str(log) + '.html').read_text()


def test_a_browser_that_fails_or_writes_no_pdf_is_an_error(tmp_path):
    """Verify browser failure, missing output, and invalid PDF content raise errors."""
    failing = tmp_path / 'fails'
    failing.write_text('#!/bin/sh\nexit 1\n')
    failing.chmod(0o755)
    with pytest.raises(RuntimeError, match='could not print'):
        render_pdf('# Hi', tmp_path / 'a.pdf', browser=str(failing))
    silent = tmp_path / 'silent'
    silent.write_text('#!/bin/sh\nexit 0\n')
    silent.chmod(0o755)
    with pytest.raises(RuntimeError, match='did not write a PDF'):
        render_pdf('# Hi', tmp_path / 'b.pdf', browser=str(silent))
    notpdf = tmp_path / 'notpdf'
    notpdf.write_text('#!/bin/sh\nfor a in "$@"; do case "$a" in --print-to-pdf=*) echo hello > "${a#--print-to-pdf=}";; esac; done\n')
    notpdf.chmod(0o755)
    with pytest.raises(RuntimeError, match='did not write a PDF'):
        render_pdf('# Hi', tmp_path / 'c.pdf', browser=str(notpdf))


# ---------- the command the backup runs ----------


def test_the_cli_makes_the_pdf_of_the_profile(fake_browser, monkeypatch, tmp_path, capsys):
    """Verify the profile PDF command prints its output path and uses the Markdown title."""
    (tmp_path / 'profile').mkdir()
    (tmp_path / 'profile' / 'profile.md').write_text('# Profile — Ana Invented\n\n## Basics\n\n- **Name:** Ana\n')
    monkeypatch.setattr(cli, 'PROFILE_DIR', tmp_path / 'profile')
    monkeypatch.setenv('CAREER_MODE_BROWSER', str(fake_browser[0]))
    out = tmp_path / 'backup' / 'profile.pdf'
    cli.main(['profile-pdf', str(out)])
    assert capsys.readouterr().out.strip() == str(out)
    assert out.read_bytes().startswith(b'%PDF-')
    assert '<title>Profile — Ana Invented</title>' in Path(str(fake_browser[1]) + '.html').read_text()


def test_the_cli_says_what_is_missing(no_browser, monkeypatch, tmp_path):
    """Verify the profile PDF command reports a missing source file or browser."""
    monkeypatch.setattr(cli, 'PROFILE_DIR', tmp_path / 'nothing-here')
    with pytest.raises(SystemExit, match='no profile/profile.md'):
        cli.main(['profile-pdf', str(tmp_path / 'x.pdf')])
    (tmp_path / 'profile').mkdir()
    (tmp_path / 'profile' / 'profile.md').write_text('# Hi\n')
    monkeypatch.setattr(cli, 'PROFILE_DIR', tmp_path / 'profile')
    with pytest.raises(SystemExit, match='No Chrome or Chromium'):
        cli.main(['profile-pdf', str(tmp_path / 'x.pdf')])


# ---------- the messages, as a document like the profile ----------


def test_the_example_messages_come_out_as_a_readable_document():
    """Verify example outreach headings and all twelve message code blocks are rendered."""
    example = (ROOT / 'profile' / 'outreach.example.md').read_text(encoding='utf-8')
    html = markdown_to_html(example)
    for line in example.splitlines():
        if line.startswith('## ') or line.startswith('### '):
            level = 2 if line.startswith('## ') else 3
            assert '<h%d>%s</h%d>' % (level, htmllib.escape(line[level + 1:].strip()), level) in html
    assert html.count('<pre>') == 12 and '```' not in html  # six messages, two languages each


def test_the_cli_makes_the_messages_pdf_and_the_profile_pdf_by_default_in_the_profile_folder_of_the_backup(fake_browser, monkeypatch, tmp_path):
    """Verify both PDF commands default to the backup profile folder and use their own source."""
    (tmp_path / 'profile').mkdir()
    (tmp_path / 'profile' / 'outreach.md').write_text('# Outreach — Ana Invented\n\n## 📝 A Message\n')
    (tmp_path / 'profile' / 'profile.md').write_text('# Profile — Ana Invented\n')
    monkeypatch.setattr(cli, 'PROFILE_DIR', tmp_path / 'profile')
    monkeypatch.setattr(cli, 'backup_dir', lambda: str(tmp_path / 'backup'))
    monkeypatch.setenv('CAREER_MODE_BROWSER', str(fake_browser[0]))
    html_log = Path(str(fake_browser[1]) + '.html')
    cli.main(['outreach-pdf'])
    assert (tmp_path / 'backup' / 'profile' / 'outreach.pdf').read_bytes().startswith(b'%PDF-')
    assert '<h2>📝 A Message</h2>' in html_log.read_text() and 'Exact text' not in html_log.read_text()
    cli.main(['profile-pdf'])
    assert (tmp_path / 'backup' / 'profile' / 'profile.pdf').is_file()
    assert '<h1>Profile — Ana Invented</h1>' in html_log.read_text()


def test_the_cli_says_when_there_are_no_messages(no_browser, monkeypatch, tmp_path):
    """Verify the outreach PDF command reports a missing messages file."""
    monkeypatch.setattr(cli, 'PROFILE_DIR', tmp_path / 'nothing-here')
    with pytest.raises(SystemExit, match='no profile/outreach.md'):
        cli.main(['outreach-pdf', str(tmp_path / 'x.pdf')])
