"""Backup and restore: two CSV files (calendar and companies), and the JSON of the older backups."""
import csv
import io
import re

from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.orm import Session

from . import crud
from .models import Company, CompanyRecruiter, CompanyType, Event
from .schemas import CompanyIn, CompanyOut, EventIn, EventOut


def export_snapshot(session: Session) -> dict:
    """What the JSON holds, in the API's own camelCase shape."""
    return {
        'companies': [CompanyOut.model_validate(c).model_dump(by_alias=True, mode='json') for c in crud.list_companies(session)],
        'events': [EventOut.model_validate(e).model_dump(by_alias=True, mode='json') for e in crud.list_events(session)],
    }


# ---------- CSV: calendar.csv and companies.csv ----------
#
# Two flat files you can open in a spreadsheet: the events, and the companies (agencies and clients, told apart by
# the `company_type` column). The older backups, with `agency_id` and `client_id` and a `kind` column, are read too.

# Columns run roughly from shortest to longest, free text last, so the short ones stay in view in a spreadsheet.
CALENDAR_COLUMNS = [
    'id', 'date', 'time', 'event', 'company', 'apply_type', 'calendar_event_id',
    'company_id', 'via_company_id', 'jd_url', 'notes',
]
COMPANIES_COLUMNS = [
    'company_type', 'id', 'name', 'status', 'via_company_id', 'website', 'linkedin', 'recruiters',
    'application_link', 'notes',
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
            'company_id': e['companyId'], 'via_company_id': e['viaCompanyId'],
        }
        for e in data['events']
    ]
    companies = [
        {
            'company_type': c['companyType'], 'id': c['id'], 'name': c['name'], 'status': c['status'], 'via_company_id': c['viaCompanyId'],
            'website': c['website'], 'linkedin': c['linkedin'], 'application_link': c['applicationLink'], 'notes': c['notes'],
            'recruiters': RECRUITER_SEPARATOR.join(c['recruiters']),
        }
        for c in data['companies']
    ]
    return {'calendar': _write_csv(CALENDAR_COLUMNS, calendar), 'companies': _write_csv(COMPANIES_COLUMNS, companies)}


def _read_csv(text: str, required, name: str):
    reader = csv.DictReader(io.StringIO((text or '').lstrip('\ufeff'), newline=''))
    if not reader.fieldnames or not set(required) <= set(reader.fieldnames):
        raise ValueError('%s is not a career-mode CSV: it needs the columns %s' % (name, ', '.join(required)))
    for number, raw in enumerate(reader, start=2):  # the header is line 1
        yield number, {k: _unescape_cell(v) for k, v in raw.items() if k}


def parse_csv(calendar: str = None, companies: str = None):
    """Reads what export_csv() writes, and the older files (either file may be missing). Returns (snapshot, warnings),
    ready for import_snapshot(); a row that can't be read is left out and reported."""
    data = {'companies': [], 'events': []}
    warnings = []
    for number, row in _read_csv(companies, ('id', 'name'), 'companies.csv') if companies else ():
        company_type = (row.get('company_type') or row.get('kind') or '').lower()  # `kind` is what the older files call it
        if company_type not in ('agency', 'client'):
            warnings.append('companies.csv line %d: company_type must be agency or client, not %r; row left out' % (number, company_type))
            continue
        data['companies'].append({
            'id': row['id'], 'name': row['name'], 'companyType': company_type,
            'notes': row.get('notes') or row.get('type'),  # an older agency kept what it does in `type`
            'website': row.get('website'), 'linkedin': row.get('linkedin'), 'applicationLink': row.get('application_link'),
            'viaCompanyId': row.get('via_company_id') or row.get('via_agency_id'),
            'recruiters': [u.strip() for u in (row.get('recruiters') or '').split(RECRUITER_SEPARATOR.strip()) if u.strip()],
        })
    for number, row in _read_csv(calendar, ('id', 'date', 'event'), 'calendar.csv') if calendar else ():
        data['events'].append({
            'id': row['id'], 'date': row['date'], 'time': row.get('time'), 'event': row['event'], 'notes': row.get('notes'),
            'jdUrl': row.get('jd_url'), 'applyType': row.get('apply_type'), 'calendarEventId': row.get('calendar_event_id'),
            'companyId': row.get('company_id'), 'viaCompanyId': row.get('via_company_id'),
            'agencyId': row.get('agency_id'), 'clientId': row.get('client_id'),  # the older files; see _from_older
        })  # `company` is only there to read: the server derives it
    return data, warnings


def _reason(err: Exception) -> str:
    if isinstance(err, ValidationError):
        first = err.errors()[0]
        return '%s: %s' % ('.'.join(str(p) for p in first['loc']), first['msg'])
    return getattr(err, 'message', str(err))


def _from_older(snapshot: dict) -> dict:
    """The older shape (agencies, clients, and events with agencyId and clientId) as companies and events.

    An agency and a client could share an id there: the client gets a new one (-2) and its events follow. A client's
    name that an agency already has gets " (client)" after it, so no name is twice. An event of a client keeps its
    agency as the via."""
    companies = [dict(c) for c in snapshot.get('companies') or []]
    ids = {c.get('id') for c in companies}
    names = {(c.get('name') or '').strip().lower() for c in companies}
    client_ids = {}
    for a in snapshot.get('agencies') or []:
        companies.append({**a, 'companyType': 'agency', 'notes': a.get('notes') or a.get('type')})
        ids.add(a.get('id'))
        names.add((a.get('name') or '').strip().lower())
    for c in snapshot.get('clients') or []:
        new_id, n = c.get('id'), 2
        while new_id in ids:
            new_id, n = '%s-%d' % (c.get('id'), n), n + 1
        name = c.get('name') or ''
        while name.strip().lower() in names:
            name = '%s (client)' % name
        ids.add(new_id)
        names.add(name.strip().lower())
        client_ids[c.get('id')] = new_id
        companies.append({**c, 'id': new_id, 'name': name, 'companyType': 'client', 'viaCompanyId': c.get('viaAgencyId') or c.get('viaCompanyId')})
    events = []
    for e in snapshot.get('events', snapshot.get('applications')) or []:
        e = dict(e)
        if e.get('clientId') or e.get('agencyId'):
            if e.get('clientId'):
                e['viaCompanyId'] = e.get('agencyId') or e.get('viaCompanyId')
                e['companyId'] = client_ids.get(e['clientId'], e['clientId'])
            else:
                e['companyId'] = e['agencyId']
        e.pop('agencyId', None)
        e.pop('clientId', None)
        events.append(e)
    return {'companies': companies, 'events': events}


def import_snapshot(session: Session, snapshot: dict, replace: bool = False) -> dict:
    """Loads companies and events, keeping their ids.

    Accepts what export_snapshot() writes and the older backups (agencies and clients, `applications` instead of
    `events`, a stored `companyLabel` and `status` that are now ignored: both are derived). Nothing aborts the
    whole import: a record that can't be loaded is skipped and reported, and a dangling reference is cut (the
    event or client is kept, unlinked) and reported.
    """
    report = {'companies': 0, 'events': 0, 'warnings': [], 'skipped': []}
    snapshot = _from_older(snapshot)
    companies = snapshot['companies']
    events = snapshot['events']

    if replace:
        for model in (Event, CompanyRecruiter, Company):
            session.execute(delete(model))
        session.flush()

    def attempt(kind, record, load):
        label = record.get('id') or record.get('name')
        try:
            if record.get('id') and session.get({'companies': Company, 'events': Event}[kind], record['id']):
                raise crud.DomainError(409, 'already there')
            with session.begin_nested():  # a failure undoes only this record
                load()
            report[kind] += 1
        except (crud.DomainError, ValidationError) as err:
            report['skipped'].append('%s %s: %s' % (kind[:-1] if kind == 'events' else 'company', label, _reason(err)))
        except Exception as err:  # a database rule (a duplicate name, say)
            report['skipped'].append('%s %s: %s' % (kind[:-1] if kind == 'events' else 'company', label, str(err).splitlines()[0]))

    # agencies first: a client's via has to be there when the client is loaded
    for c in sorted(companies, key=lambda c: c.get('companyType') != CompanyType.agency.value):
        known = {x.get('id') for x in companies if x.get('companyType') == CompanyType.agency.value}
        if c.get('viaCompanyId') and c['viaCompanyId'] not in known and session.get(Company, c['viaCompanyId']) is None:
            report['warnings'].append('company %s pointed to a missing agency "%s": now direct' % (c.get('id'), c['viaCompanyId']))
            c = {**c, 'viaCompanyId': None}

        def load_company(c=c):
            data = CompanyIn.model_validate(c)
            if crud._name_owner(session, data.name):
                raise crud.DomainError(409, 'a company named "%s" is already there' % data.name)
            fields = crud._fields(data)
            crud._check_via(session, fields['company_type'], fields['via_company_id'], c.get('id'))
            company = Company(id=crud._check_id(c.get('id')), **fields)
            session.add(company)
            session.flush()
            crud._set_recruiters(session, company, data.recruiters)
        attempt('companies', c, load_company)

    for e in events:
        e = dict(e)
        for key in ('companyId', 'viaCompanyId'):
            if e.get(key) and session.get(Company, e[key]) is None:
                report['warnings'].append('event %s pointed to a missing company "%s": left unlinked' % (e.get('id'), e[key]))
                e[key] = None

        def load_event(e=e):
            data = EventIn.model_validate(e)
            columns = crud._event_columns(session, data.model_dump())
            session.add(Event(id=crud._check_id(e.get('id') or crud.uuid.uuid4().hex[:20]), **columns))
            session.flush()
        attempt('events', e, load_event)

    session.commit()
    return report
