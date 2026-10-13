"""Backup and restore: two CSV files (calendar and companies), and the JSON the old Firestore backups used."""
import csv
import io
import re

from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.orm import Session

from . import crud
from .models import Agency, AgencyRecruiter, Client, Event
from .schemas import AgencyIn, AgencyOut, ClientIn, ClientOut, EventIn, EventOut


def export_snapshot(session: Session) -> dict:
    """What the JSON files hold, in the API's own camelCase shape."""
    return {
        'agencies': [AgencyOut.model_validate(a).model_dump(by_alias=True, mode='json') for a in crud.list_agencies(session)],
        'clients': [ClientOut.model_validate(c).model_dump(by_alias=True, mode='json') for c in crud.list_clients(session)],
        'events': [EventOut.model_validate(e).model_dump(by_alias=True, mode='json') for e in crud.list_events(session)],
    }


# ---------- CSV: calendar.csv and companies.csv ----------
#
# Two flat files you can open in a spreadsheet: the events, and the agencies and clients in
# one list (the `kind` column tells them apart, and an agency and a client may share an id).

# Columns run roughly from shortest to longest, free text last, so the short ones stay in view in a spreadsheet.
CALENDAR_COLUMNS = [
    'id', 'date', 'time', 'event', 'company', 'apply_type', 'calendar_event_id',
    'agency_id', 'client_id', 'jd_url', 'notes',
]
COMPANIES_COLUMNS = [
    'kind', 'id', 'name', 'status', 'via_agency_id', 'website', 'linkedin', 'recruiters',
    'application_link', 'type', 'notes',
]
CSV_FILES = {'calendar': 'calendar.csv', 'companies': 'companies.csv'}
RECRUITER_SEPARATOR = ' | '  # LinkedIn links have no spaces, so this can't appear inside one
_FORMULA = re.compile(r"^'*[=+\-@\t\r]")


def _escape_cell(value):
    """A spreadsheet runs a cell that starts with = + - @ as a formula, so those get a leading '.
    Reversible: a value that already starts with ' before such a character gets one more."""
    value = '' if value is None else str(value)
    return "'" + value if _FORMULA.match(value) else value


def _unescape_cell(value):
    value = value or ''
    if value.startswith("'") and _FORMULA.match(value[1:]):
        value = value[1:]
    return value or None


def _write_csv(columns, rows) -> str:
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=columns, lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({column: _escape_cell(row.get(column)) for column in columns})
    return out.getvalue()


def export_csv(session: Session) -> dict:
    """{'calendar': text, 'companies': text}: everything in the database as two CSV files."""
    data = export_snapshot(session)
    calendar = [
        {
            'id': e['id'], 'date': e['date'], 'time': e['time'], 'event': e['event'], 'company': e['companyLabel'],
            'notes': e['notes'], 'jd_url': e['jdUrl'], 'apply_type': e['applyType'], 'calendar_event_id': e['calendarEventId'],
            'agency_id': e['agencyId'], 'client_id': e['clientId'],
        }
        for e in data['events']
    ]
    companies = [
        {
            'kind': 'agency', 'id': a['id'], 'name': a['name'], 'type': a['type'], 'website': a['website'], 'linkedin': a['linkedin'],
            'application_link': a['applicationLink'], 'status': a['status'], 'recruiters': RECRUITER_SEPARATOR.join(a['recruiters']),
        }
        for a in data['agencies']
    ] + [
        {
            'kind': 'client', 'id': c['id'], 'name': c['name'], 'website': c['website'], 'linkedin': c['linkedin'],
            'notes': c['notes'], 'via_agency_id': c['viaAgencyId'],
        }
        for c in data['clients']
    ]
    return {'calendar': _write_csv(CALENDAR_COLUMNS, calendar), 'companies': _write_csv(COMPANIES_COLUMNS, companies)}


def _read_csv(text: str, required, name: str):
    reader = csv.DictReader(io.StringIO((text or '').lstrip('\ufeff'), newline=''))
    if not reader.fieldnames or not set(required) <= set(reader.fieldnames):
        raise ValueError('%s is not a career-mode CSV: it needs the columns %s' % (name, ', '.join(required)))
    for number, raw in enumerate(reader, start=2):  # the header is line 1
        yield number, {k: _unescape_cell(v) for k, v in raw.items() if k}


def parse_csv(calendar: str = None, companies: str = None):
    """Reads what export_csv() writes (either file may be missing). Returns (snapshot, warnings),
    ready for import_snapshot(); a row that can't be read is left out and reported."""
    data = {'agencies': [], 'clients': [], 'events': []}
    warnings = []
    for number, row in _read_csv(companies, ('kind', 'id', 'name'), 'companies.csv') if companies else ():
        kind = (row.get('kind') or '').lower()
        if kind == 'agency':
            data['agencies'].append({
                'id': row['id'], 'name': row['name'], 'type': row.get('type'), 'website': row.get('website'),
                'linkedin': row.get('linkedin'), 'applicationLink': row.get('application_link'), 'status': row.get('status'),
                'recruiters': [u.strip() for u in (row.get('recruiters') or '').split(RECRUITER_SEPARATOR.strip()) if u.strip()],
            })
        elif kind == 'client':
            data['clients'].append({
                'id': row['id'], 'name': row['name'], 'website': row.get('website'), 'linkedin': row.get('linkedin'),
                'notes': row.get('notes'), 'viaAgencyId': row.get('via_agency_id'),
            })
        else:
            warnings.append('companies.csv line %d: kind must be agency or client, not %r; row left out' % (number, row.get('kind')))
    for number, row in _read_csv(calendar, ('id', 'date', 'event'), 'calendar.csv') if calendar else ():
        data['events'].append({
            'id': row['id'], 'date': row['date'], 'time': row.get('time'), 'event': row['event'], 'notes': row.get('notes'),
            'jdUrl': row.get('jd_url'), 'applyType': row.get('apply_type'), 'calendarEventId': row.get('calendar_event_id'),
            'agencyId': row.get('agency_id'), 'clientId': row.get('client_id'),
        })  # `company` is only there to read: the server derives it
    return data, warnings


def _reason(err: Exception) -> str:
    if isinstance(err, ValidationError):
        first = err.errors()[0]
        return '%s: %s' % ('.'.join(str(p) for p in first['loc']), first['msg'])
    return getattr(err, 'message', str(err))


def import_snapshot(session: Session, snapshot: dict, replace: bool = False) -> dict:
    """Loads agencies, clients and events, keeping their ids.

    Accepts what export_snapshot() writes and the old Firestore backups
    (`applications` instead of `events`, `status: null`, a stored `companyLabel`
    that is now ignored). Nothing aborts the whole import: a record that can't
    be loaded is skipped and reported, and a dangling reference is cut (the
    event or client is kept, unlinked) and reported. Stored statuses are kept as
    they are: the "a new event changes the agency's status" rule is for live
    use, not for loading history.
    """
    report = {'agencies': 0, 'clients': 0, 'events': 0, 'warnings': [], 'skipped': []}
    agencies = snapshot.get('agencies') or []
    clients = snapshot.get('clients') or []
    events = snapshot.get('events', snapshot.get('applications')) or []

    if replace:
        for model in (Event, Client, AgencyRecruiter, Agency):
            session.execute(delete(model))
        session.flush()

    def attempt(kind, record, load):
        label = record.get('id') or record.get('name')
        try:
            if record.get('id') and session.get({'agencies': Agency, 'clients': Client, 'events': Event}[kind], record['id']):
                raise crud.DomainError(409, 'already there')
            with session.begin_nested():  # a failure undoes only this record
                load()
            report[kind] += 1
        except (crud.DomainError, ValidationError) as err:
            report['skipped'].append('%s %s: %s' % (kind[:-1], label, _reason(err)))
        except Exception as err:  # a database rule (a duplicate name, say)
            report['skipped'].append('%s %s: %s' % (kind[:-1], label, str(err).splitlines()[0]))

    for a in agencies:
        def load_agency(a=a):
            data = AgencyIn.model_validate(a)
            if crud._name_owner(session, Agency, data.name):
                raise crud.DomainError(409, 'an agency named "%s" is already there' % data.name)
            agency = Agency(id=crud._check_id(a.get('id')), **data.model_dump(exclude={'recruiters'}))
            session.add(agency)
            session.flush()
            crud._set_recruiters(session, agency, data.recruiters)
        attempt('agencies', a, load_agency)

    for c in clients:
        if c.get('viaAgencyId') and session.get(Agency, c['viaAgencyId']) is None:
            report['warnings'].append('client %s pointed to a missing agency "%s": now direct' % (c.get('id'), c['viaAgencyId']))
            c = {**c, 'viaAgencyId': None}

        def load_client(c=c):
            data = ClientIn.model_validate(c)
            if crud._name_owner(session, Client, data.name):
                raise crud.DomainError(409, 'a client named "%s" is already there' % data.name)
            session.add(Client(id=crud._check_id(c.get('id')), **data.model_dump()))
            session.flush()
        attempt('clients', c, load_client)

    for e in events:
        e = dict(e)
        for key, model, kind in (('agencyId', Agency, 'agency'), ('clientId', Client, 'client')):
            if e.get(key) and session.get(model, e[key]) is None:
                report['warnings'].append('event %s pointed to a missing %s "%s": left unlinked' % (e.get('id'), kind, e[key]))
                e[key] = None

        def load_event(e=e):
            data = EventIn.model_validate(e)
            columns = crud._event_columns(session, data.model_dump())
            session.add(Event(id=crud._check_id(e.get('id') or crud.uuid.uuid4().hex[:20]), **columns))
            session.flush()
        attempt('events', e, load_event)

    session.commit()
    return report
