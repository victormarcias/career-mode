"""public/js/events.js and the server must agree on the event types and on which ones close a process."""
import json
import re
from pathlib import Path

from app.models import CLOSING_EVENTS, EVENT_TYPES

PUBLIC = Path(__file__).resolve().parent.parent / 'public'
LOCALES = PUBLIC / 'locales'
EVENTS_JS = (PUBLIC / 'js' / 'events.js').read_text()


def js_list(name):
    body = re.search(r'%s\s*=\s*\[(.*?)\]' % name, EVENTS_JS, re.S).group(1)
    return re.findall(r"'([a-z_]+)'", body)


def test_selectable_event_types_match_the_server():
    # `pending` is a queued link, created by the "Apply to job" form, never picked by hand
    assert js_list('EVENT_TYPES') == [t for t in EVENT_TYPES if t != 'pending']


def test_every_type_has_an_emoji_and_colors():
    for table in ('EVENT_EMOJIS', 'EVENT_COLORS'):
        body = re.search(r'%s\s*=\s*\{(.*?)\n\}' % table, EVENTS_JS, re.S).group(1)
        assert set(re.findall(r'^\s{2}([a-z_]+):', body, re.M)) == set(EVENT_TYPES), table


def test_every_type_has_a_label_in_both_languages():
    for language in ('en', 'es'):
        texts = json.loads((LOCALES / ('%s.json' % language)).read_text(encoding='utf-8'))
        assert {k for k in texts if k.startswith('events.') and k[7:] in EVENT_TYPES} == {'events.%s' % t for t in EVENT_TYPES}, language


def test_closing_events_match_the_server():
    assert js_list('CLOSING_EVENTS') == [e.value for e in CLOSING_EVENTS]
