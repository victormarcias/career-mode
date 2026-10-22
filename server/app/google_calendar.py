"""Reads a Google Calendar as iCal and logs its events as HR intro or tech interview events.

The calendar comes from the `GOOGLE_CALENDAR_ID` setting: either the calendar's ID (which has to be public, with
"See all event details") or its secret iCal address, which works for a private calendar. Each event is
stored once: its calendar id goes in `events.calendar_event_id`, so a second sync only moves the ones whose
date or time changed. Everything is read, never written, in Google.
"""
import datetime as dt
import html
import re
import ssl
from dataclasses import dataclass
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import certifi
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import crud
from .models import Company, CompanyType, Event, EventType
from .schemas import CompanyIn, CompanyPatch, EventIn

ICAL_HOST = 'calendar.google.com'


def ics_url(value: str) -> str:
    """Where to read the calendar from. Raises ValueError (a sentence to show) if `value` can't be one."""
    value = value.strip()
    if re.search(r'\s', value):
        raise ValueError('A calendar ID has no spaces')
    if value.lower().startswith(('http://', 'https://')):
        parts = urlparse(value)
        if parts.scheme != 'https' or parts.hostname != ICAL_HOST:
            raise ValueError('An iCal address has to be an https://%s link' % ICAL_HOST)
        return value
    return 'https://%s/calendar/ical/%s/public/basic.ics' % (ICAL_HOST, quote(value, safe='@'))


def fetch_ics(url: str) -> str:
    # certifi's certificates, not the system's: a Python installed from python.org on a Mac has none until
    # someone runs its "Install Certificates" command, and every https call fails with CERTIFICATE_VERIFY_FAILED.
    context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urlopen(Request(url, headers={'User-Agent': 'career-mode'}), timeout=15, context=context) as response:
            text = response.read().decode('utf-8', errors='replace')
    except HTTPError as err:
        raise crud.DomainError(502, (
            'Google did not give the calendar (HTTP %d). Check the Calendar ID in Settings: the calendar has to be '
            'public with "See all event details", or you can paste its secret iCal address instead.' % err.code
        ))
    except (URLError, TimeoutError, OSError) as err:
        raise crud.DomainError(502, 'Cannot reach Google Calendar: %s' % getattr(err, 'reason', err))
    if 'BEGIN:VCALENDAR' not in text:
        raise crud.DomainError(502, 'Google answered something that is not a calendar. Check the Calendar ID in Settings.')
    return text


# ---------- iCal ----------


@dataclass
class CalendarEvent:
    key: str  # what `calendar_event_id` stores: the event's UID, plus the occurrence when it is one
    summary: str
    description: str
    start: Optional[dt.datetime]  # None for an all-day event
    cancelled: bool
    recurrence: Optional[str]  # the RRULE of a repeating event, which is not expanded here


_LINE = re.compile(r'^([A-Za-z0-9-]+)((?:;[^:;=]+=(?:"[^"]*"|[^;:]*))*):(.*)$')
_PARAM = re.compile(r';([^:;=]+)=("[^"]*"|[^;:]*)')


def _unescape(value: str) -> str:
    return re.sub(r'\\([nN,;\\])', lambda m: '\n' if m.group(1) in 'nN' else m.group(1), value)


def _start(value: str, params: dict, tz) -> Optional[dt.datetime]:
    """The start in the local time zone, or None for an all-day event."""
    if params.get('VALUE') == 'DATE' or len(value) == 8:
        return None
    naive = dt.datetime.strptime(value.rstrip('Z'), '%Y%m%dT%H%M%S')
    if value.endswith('Z'):
        aware = naive.replace(tzinfo=dt.timezone.utc)
    elif 'TZID' in params:
        try:
            aware = naive.replace(tzinfo=ZoneInfo(params['TZID']))
        except (ZoneInfoNotFoundError, ValueError):
            aware = naive.replace(tzinfo=tz) if tz else naive.astimezone()
    else:
        aware = naive.replace(tzinfo=tz) if tz else naive.astimezone()  # a "floating" time is already local
    return aware.astimezone(tz) if tz else aware.astimezone()


def parse_ics(text: str, tz=None) -> list[CalendarEvent]:
    """Every VEVENT of the calendar. `tz` is the time zone to read times in (the computer's own by default)."""
    lines = []
    for raw in re.split(r'\r\n|\n|\r', text):
        if raw[:1] in (' ', '\t') and lines:
            lines[-1] += raw[1:]  # a long line continues on the next one
        else:
            lines.append(raw)

    events, current = [], None
    for line in lines:
        if line == 'BEGIN:VEVENT':
            current = {}
        elif line == 'END:VEVENT' and current is not None:
            if 'UID' in current and 'DTSTART' in current:
                value, params = current['DTSTART']
                try:
                    start = _start(value, params, tz)
                except ValueError:
                    current = None
                    continue
                uid = current['UID'][0]
                if 'RECURRENCE-ID' in current:
                    uid += '|' + current['RECURRENCE-ID'][0]
                events.append(CalendarEvent(
                    key=uid,
                    summary=_unescape(current.get('SUMMARY', ('', {}))[0]).strip(),
                    description=_unescape(current.get('DESCRIPTION', ('', {}))[0]),
                    start=start,
                    cancelled=current.get('STATUS', ('', {}))[0].upper() == 'CANCELLED',
                    recurrence=current['RRULE'][0] if 'RRULE' in current else None,
                ))
            current = None
        elif current is not None:
            match = _LINE.match(line)
            if match:
                params = {k.upper(): v.strip('"') for k, v in _PARAM.findall(match.group(2))}
                current.setdefault(match.group(1).upper(), (match.group(3), params))
    return events


# ---------- Sync ----------

# The types an event of the calendar can be logged as. "Tech" in its title picks the second one, "culture" the third.
SYNC_TYPES = (EventType.hr_intro, EventType.tech_interview, EventType.culture_interview)


def suggested_type(summary: str) -> EventType:
    if re.search(r'tech', summary, re.IGNORECASE):
        return EventType.tech_interview
    return EventType.culture_interview if re.search(r'cultur', summary, re.IGNORECASE) else EventType.hr_intro


def clean_description(text: str) -> str:
    """The description as plain text for the notes: Google may keep it as HTML (<br>, links), Calendly sends plain text."""
    text = re.sub(
        r'<a\s[^>]*?href="([^"]+)"[^>]*>(.*?)</a>',
        lambda m: m.group(1) if m.group(2).strip() in ('', m.group(1)) else '[%s](%s)' % (m.group(2).strip(), m.group(1)),
        text, flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r'<\s*br\s*/?>|</\s*(?:p|div|li|ul|ol)\s*>', '\n', text, flags=re.IGNORECASE)
    text = html.unescape(re.sub(r'</?[A-Za-z][^>]*>', '', text))
    return re.sub(r'\n{3,}', '\n\n', re.sub(r'[ \t]+\n', '\n', text)).strip()


def event_notes(summary: str, description: str) -> str:
    """What the event's notes hold: the Google event's title, then its description."""
    return '\n\n'.join(part for part in (summary, description) if part)


def _company_line(description: str) -> Optional[str]:
    """Calendly adds a "Company: Name" line to what it books."""
    match = re.search(r'^\s*Company:[ \t]*(.+?)\s*$', description, re.MULTILINE | re.IGNORECASE)
    return match.group(1) if match else None


def _repeats_in(event: CalendarEvent, first: dt.date, last: dt.date) -> bool:
    """Could this repeating event happen in the range? (Roughly: it has started and its UNTIL has not passed.)"""
    if event.start is None or event.start.date() > last:
        return False
    until = re.search(r'UNTIL=(\d{8})', event.recurrence or '')
    return not (until and dt.datetime.strptime(until.group(1), '%Y%m%d').date() < first)


def _suggest_company(session: Session, line: Optional[str]) -> dict:
    """The company to offer for a "Company:" line, as {company, companyType, via} (names). One the app has is used as
    it is (a client brings the agency it came through); one it doesn't is offered as a new agency, which the person can change."""
    if not line:
        return {'company': None, 'companyType': None, 'via': None}
    company = crud.find_company(session, line)
    if company is None:
        return {'company': line, 'companyType': CompanyType.agency.value, 'via': None}
    via = session.get(Company, company.via_company_id) if company.via_company_id else None
    return {'company': company.name, 'companyType': company.company_type, 'via': via.name if via else None}


def plan_range(session: Session, ics_text: str, first: dt.date, last: dt.date, tz=None) -> dict:
    """What a sync between `first` and `last` (both included) would do, without doing it.

    `events` are the ones to add (`action` "new") or to move because their day or time changed in Google
    ("moved"); the ones already logged as they are only count as `unchanged`. A repeating event is not
    expanded, so it is only counted (`recurringSkipped`); an all-day or cancelled one is ignored. A new event
    comes with the company to offer for it (`company`, `companyType`, `via`), taken from a "Company:" line of the description.
    """
    plan = {'events': [], 'unchanged': 0, 'recurringSkipped': 0}
    for event in parse_ics(ics_text, tz):
        if event.cancelled or event.start is None:
            continue
        if event.recurrence:
            plan['recurringSkipped'] += _repeats_in(event, first, last)
            continue
        if not first <= event.start.date() <= last:
            continue
        date, time = event.start.date().isoformat(), event.start.strftime('%H:%M')
        known = session.scalar(select(Event).where(Event.calendar_event_id == event.key))
        if known is not None and (known.date, known.time) == (date, time):
            plan['unchanged'] += 1
            continue
        summary = event.summary or 'Google Calendar event'
        description = clean_description(event.description)
        if known is None:
            offer = _suggest_company(session, _company_line(description))
        else:
            offer = {'company': known.company.name if known.company else None,
                     'companyType': known.company.company_type if known.company else None,
                     'via': known.via.name if known.via else None}
        plan['events'].append({
            'key': event.key,
            'summary': summary,
            'notes': event_notes(summary, description),
            'date': date,
            'time': time,
            **offer,
            'action': 'new' if known is None else 'moved',
            'type': suggested_type(event.summary).value,
        })
    return plan


@dataclass
class Choice:
    """What was picked in the popup for one event."""

    type: EventType
    company: Optional[str] = None  # a name: an existing company is reused, a new one is created
    company_type: Optional[str] = None  # agency or client; what a new company is, and what an existing one must already be
    via: Optional[str] = None  # for a client: the name of the agency it came through


def _resolve_company(session: Session, choice: Choice) -> tuple[Optional[str], Optional[str]]:
    """The ids (company, via) to link, creating what is new: the same rules as the Update form.

    A name that exists as the other type than the one chosen is refused, so a company is never made twice. A client
    given with an agency is (re)pointed to it; a known client given alone keeps the agency it came through.
    """
    if not choice.company:
        return None, None
    company = crud.find_company(session, choice.company)
    company_type = choice.company_type or (company.company_type if company else CompanyType.agency.value)
    via = None
    if choice.via:
        if company_type != CompanyType.client.value:
            raise crud.DomainError(422, 'Only a client can come through an agency: "%s" is an agency' % choice.company)
        via = crud.find_company(session, choice.via)
        if via is None:
            via = crud.create_company(session, CompanyIn(name=choice.via, company_type=CompanyType.agency))
        elif via.company_type != CompanyType.agency.value:
            raise crud.DomainError(422, '"%s" is a client, not an agency' % via.name)
    if company is None:
        company = crud.create_company(session, CompanyIn(name=choice.company, company_type=company_type, via_company_id=via.id if via else None))
    elif company.company_type != company_type:
        raise crud.DomainError(409, '"%s" is already %s: pick it as that' % (company.name, 'an agency' if company.company_type == 'agency' else 'a client'))
    elif via and company.via_company_id != via.id:
        company = crud.update_company(session, company.id, CompanyPatch(via_company_id=via.id))
    if company.company_type == CompanyType.agency.value:
        return company.id, None
    return company.id, (via.id if via else company.via_company_id)


def apply_range(session: Session, ics_text: str, first: dt.date, last: dt.date, chosen: dict, tz=None) -> dict:
    """Does what `plan_range` says, for the events whose key is in `chosen` ({key: Choice}) only.

    A new event is logged with the type and the company chosen for it, and its notes are the Google event's
    title and description. A company that does not exist yet is created first (an event can be the first one
    of its company). A moved event only gets its new date and time: its type, company and notes stay as they are.
    Every choice is checked before anything is written.
    """
    items = [item for item in plan_range(session, ics_text, first, last, tz)['events'] if item['key'] in chosen]
    for item in items:
        choice = chosen[item['key']]
        if item['action'] == 'new' and not choice.company:
            raise crud.DomainError(422, 'Pick a company for "%s"' % item['summary'])
    result = {'created': 0, 'updated': 0}
    for item in items:
        choice = chosen[item['key']]
        if item['action'] == 'moved':
            known = session.scalar(select(Event).where(Event.calendar_event_id == item['key']))
            known.date, known.time = item['date'], item['time']
            session.commit()
            result['updated'] += 1
            continue
        company_id, via_company_id = _resolve_company(session, choice)
        crud.create_event(session, EventIn(
            date=item['date'], time=item['time'], event=choice.type, notes=item['notes'],
            calendar_event_id=item['key'], company_id=company_id, via_company_id=via_company_id,
        ))
        result['created'] += 1
    return result
