"""A PDF of one of the user's markdown files (the profile), laid out like a document.

Meant for the backup: the PDF opens in Google Docs (upload it to Drive and "Open with Google Docs") with its
headings, bullets, bold labels and links kept, which a pasted markdown file does not give. It needs no package:
the markdown is turned into HTML here (the same small subset the My Profile page reads, see public/js/markdown.js:
headings, paragraphs, nested lists, code blocks, and `code`, **bold**, *italic* and [text](link) in a line) and
Chrome or Chromium prints it, headless. With none of them installed there is no PDF, and the caller
says so.
"""
import html
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

MARKER = re.compile(r'^(\s*)([-*]|\d+\.)\s+(.*)$')
HEADING = re.compile(r'^(#{1,6})\s+(.*)$')

BROWSER_NAMES = ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome')
MAC_APPS = (
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
)

STYLE = """
@page { size: A4; margin: 2.2cm 2.3cm; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 11pt; line-height: 1.5; color: #000; }
h1 { font-size: 26pt; line-height: 1.2; margin: 0 0 14pt; }
h2 { font-size: 18pt; line-height: 1.25; margin: 22pt 0 8pt; break-after: avoid; }
h3 { font-size: 14pt; margin: 16pt 0 6pt; break-after: avoid; }
h4, h5, h6 { font-size: 12pt; margin: 12pt 0 4pt; break-after: avoid; }
p { margin: 0 0 10pt; }
ul, ol { margin: 0 0 10pt; padding-left: 28pt; }
li { margin: 0 0 3pt; }
li > p { margin: 4pt 0 0; }
a { color: #1155cc; }
code { font-family: Menlo, Consolas, 'Courier New', monospace; font-size: 10pt; color: #38761d; }
pre { margin: 0 0 12pt; padding: 8pt 10pt; border: 1px solid #ccc; background: #f6f6f6; white-space: pre-wrap; break-inside: avoid; }
pre code { color: #000; }
"""


def _inline(text: str) -> str:
    spans = []

    def hold(match):
        spans.append('<code>%s</code>' % match.group(1))
        return '\u0000%d\u0000' % (len(spans) - 1)

    held = re.sub(r'`([^`]+)`', hold, html.escape(text))  # `code` is set aside first: no bold, italic or link inside it
    held = re.sub(r'\[([^\]]+)\]\(((?:https?://|mailto:)[^)\s"]+)\)', r'<a href="\2">\1</a>', held)
    held = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', held)
    held = re.sub(r'(^|[\s(])\*([^*\s][^*]*?)\*(?=$|[\s).,;:!?])', r'\1<em>\2</em>', held)
    return re.sub('\u0000(\\d+)\u0000', lambda m: spans[int(m.group(1))], held)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(' '))


def _list(lines: list, start: int):
    """The list that starts at lines[start] (its items are at that line's indent): (html, next line)."""
    base = _indent(lines[start])
    ordered = bool(re.fullmatch(r'\d+\.', MARKER.match(lines[start]).group(2)))
    items = []
    i = start
    while i < len(lines):
        marker = MARKER.match(lines[i])
        if not marker or _indent(lines[i]) != base:
            break
        text, children = marker.group(3), []
        i += 1
        while i < len(lines):  # what is indented under the item belongs to it
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines) or _indent(lines[j]) < base + 2:
                break
            if MARKER.match(lines[j]):
                nested, i = _list(lines, j)
                children.append(nested)
            else:
                paragraph = []
                while j < len(lines) and lines[j].strip() and not MARKER.match(lines[j]) and _indent(lines[j]) >= base + 2:
                    paragraph.append(lines[j].strip())
                    j += 1
                children.append('<p>%s</p>' % _inline(' '.join(paragraph)))
                i = j
        items.append('<li>%s%s</li>' % (_inline(text), ''.join(children)))
    tag = 'ol' if ordered else 'ul'
    return '<%s>%s</%s>' % (tag, ''.join(items), tag), i


def markdown_to_html(markdown: str) -> str:
    lines = markdown.replace('\r\n', '\n').split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.strip().startswith('```'):
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code.append(lines[i])
                i += 1
            i += 1
            out.append('<pre><code>%s</code></pre>' % html.escape('\n'.join(code)))
        elif HEADING.match(line):
            hashes, title = HEADING.match(line).groups()
            out.append('<h%d>%s</h%d>' % (len(hashes), _inline(title.strip()), len(hashes)))
            i += 1
        elif MARKER.match(line):
            block, i = _list(lines, i)
            out.append(block)
        else:
            paragraph = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('```') and not HEADING.match(lines[i]) and not MARKER.match(lines[i]):
                paragraph.append(lines[i].strip())
                i += 1
            out.append('<p>%s</p>' % _inline(' '.join(paragraph)))
    return '\n'.join(out)


def document_html(markdown: str, title: str = 'Profile') -> str:
    return '<!doctype html><html><head><meta charset="utf-8"><title>%s</title><style>%s</style></head><body>%s</body></html>' % (
        html.escape(title), STYLE, markdown_to_html(markdown))


def find_browser() -> Optional[str]:
    """Chrome or Chromium, or None. CAREER_MODE_BROWSER names another Chromium-based browser (Edge, Brave...) by its path."""
    chosen = os.environ.get('CAREER_MODE_BROWSER')
    if chosen:
        return chosen if os.access(chosen, os.X_OK) else None
    for name in BROWSER_NAMES:
        path = shutil.which(name)
        if path:
            return path
    return next((p for p in MAC_APPS if os.access(p, os.X_OK)), None)


def render_pdf(markdown: str, out_path, title: str = 'Profile', browser: Optional[str] = None) -> Path:
    """Writes the PDF of `markdown` to out_path. Raises RuntimeError, saying why, when it can't."""
    browser = browser or find_browser()
    if not browser:
        raise RuntimeError('No Chrome or Chromium found to print the PDF with (CAREER_MODE_BROWSER can name another Chromium-based browser by its path)')
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:  # a throwaway profile, so a Chrome you have open is left alone
        page = Path(work) / 'profile.html'
        page.write_text(document_html(markdown, title), encoding='utf-8')
        target = Path(work) / 'profile.pdf'
        command = [browser, '--headless=new', '--disable-gpu', '--no-pdf-header-footer', '--no-first-run',
                   '--user-data-dir=%s' % (Path(work) / 'chrome'), '--print-to-pdf=%s' % target, page.as_uri()]
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=90)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as err:
            raise RuntimeError('The browser could not print the PDF: %s' % err)
        if not target.is_file() or not target.read_bytes().startswith(b'%PDF-'):
            raise RuntimeError('The browser did not write a PDF')
        shutil.move(str(target), out_path)
    return out_path
