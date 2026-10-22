"""Business rules and queries. The API routes and the importer both go through here."""
import re
import unicodedata
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .models import CLOSING_EVENTS, Company, CompanyRecruiter, CompanyStatus, CompanyType, Event, EventType
from .schemas import CompanyIn, CompanyPatch, EventIn, EventPatch


class DomainError(Exception):
    """A refusal that maps to an HTTP status and a message the UI can show."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def slugify(text: str) -> str:
    """Same rule as public/js/dom-utils.js: lowercase, no accents, dashes between words."""
    text = unicodedata.normalize('NFD', text.lower().strip())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'(^-|-$)', '', re.sub(r'[^a-z0-9]+', '-', text))


def _unique_id(session: Session, model, base: str) -> str:
    candidate, n = base, 2
    while session.get(model, candidate) is not None:
        candidate = '%s-%d' % (base, n)
        n += 1
    return candidate


def _check_id(value: str) -> str:
    if not value or '/' in value or len(value) > 200:
        raise DomainError(400, 'Invalid id')
    return value


def _get(session: Session, model, record_id: str, label: str):
    record = session.get(model, record_id)
    if record is None:
        raise DomainError(404, '%s not found' % label)
    return record


def _name_owner(session: Session, name: str):
    """The id of the company that already has this name (the column compares ignoring case)."""
    return session.scalar(select(Company.id).where(Company.name == name))


def find_company(session: Session, name: str):
    """The company with this name (ignoring case), or whose id is its slug, like the front end finds it."""
    owner = _name_owner(session, name.strip()) or slugify(name)
    return session.get(Company, owner) if owner else None


# ---------- Companies ----------


def _involving(company_id):
    """The events a company is in: its own, and those of the clients that came through it."""
    return or_(Event.company_id == company_id, Event.via_company_id == company_id)


def company_status(events) -> CompanyStatus:
    """Archived when the latest event closes the process. The latest is the one on the latest day; a closing event wins a
    tie on the day whatever its time, and among the rest the later time wins. No events: active."""
    if not events:
        return CompanyStatus.active
    closing = {e.value for e in CLOSING_EVENTS}
    latest = max(events, key=lambda e: (e.date, e.type in closing, e.time or '00:00'))
    return CompanyStatus.archived if latest.type in closing else CompanyStatus.active


def list_companies(session: Session, company_type: str = None) -> list[Company]:
    query = select(Company).order_by(Company.name)
    if company_type is not None:
        query = query.where(Company.company_type == company_type)
    companies = list(session.scalars(query))
    events: dict[str, list] = {}
    for event in session.execute(select(Event.company_id, Event.via_company_id, Event.date, Event.time, Event.type)):
        for company_id in {event.company_id, event.via_company_id} - {None}:
            events.setdefault(company_id, []).append(event)
    for company in companies:
        company.status = company_status(events.get(company.id, [])).value
    return companies


def get_company(session: Session, company_id: str) -> Company:
    company = _get(session, Company, company_id, 'Company')
    company.status = company_status(list(session.scalars(select(Event).where(_involving(company_id))).unique())).value
    return company


def _set_recruiters(session: Session, company: Company, urls: list[str]):
    company.recruiters.clear()
    session.flush()  # the old rows go first, or the new ones would clash on (company, position)
    company.recruiters.extend(CompanyRecruiter(position=i, url=url) for i, url in enumerate(urls))


def _check_via(session: Session, company_type: str, via_company_id, own_id=None):
    """Only a client has a via, and it is an agency (not the company itself)."""
    if via_company_id is None:
        return
    if company_type != CompanyType.client.value:
        raise DomainError(422, 'Only a client can come through an agency: viaCompanyId is for a client')
    via = session.get(Company, via_company_id)
    if via is None:
        raise DomainError(422, 'viaCompanyId "%s" does not exist' % via_company_id)
    if via.company_type != CompanyType.agency.value or via_company_id == own_id:
        raise DomainError(422, 'viaCompanyId "%s" is not an agency' % via_company_id)


def _fields(data: CompanyIn) -> dict:
    fields = data.model_dump(exclude={'recruiters'})
    fields['company_type'] = fields['company_type'].value if hasattr(fields['company_type'], 'value') else fields['company_type']
    return fields


def create_company(session: Session, data: CompanyIn) -> Company:
    if _name_owner(session, data.name):
        raise DomainError(409, 'A company named "%s" already exists' % data.name)
    slug = slugify(data.name)
    if not slug:
        raise DomainError(422, 'The name needs at least one letter or digit')
    fields = _fields(data)
    _check_via(session, fields['company_type'], fields['via_company_id'])
    company = Company(id=_unique_id(session, Company, slug), **fields)
    session.add(company)
    session.flush()
    _set_recruiters(session, company, data.recruiters)
    session.commit()
    return get_company(session, company.id)


def _still_an_agency_of(session: Session, company_id: str):
    """Why a company can't stop being an agency: it is the agency of clients or events."""
    clients = session.scalar(select(func.count()).select_from(Company).where(Company.via_company_id == company_id))
    events = session.scalar(select(func.count()).select_from(Event).where(Event.via_company_id == company_id))
    if clients or events:
        raise DomainError(409, 'It is the agency of %d client%s and %d event%s: they have to change first'
                          % (clients, '' if clients == 1 else 's', events, '' if events == 1 else 's'))


def update_company(session: Session, company_id: str, patch: CompanyPatch) -> Company:
    company = _get(session, Company, company_id, 'Company')
    changes = patch.model_dump(exclude_unset=True)
    recruiters = changes.pop('recruiters', None)
    if 'company_type' in changes and changes['company_type'] is not None:
        changes['company_type'] = changes['company_type'].value
    for key in ('name', 'notes', 'company_type'):  # these columns can't be NULL
        if key in changes and changes[key] is None:
            raise DomainError(422, '"%s" cannot be empty' % key)
    owner = _name_owner(session, changes['name']) if 'name' in changes else None
    if owner and owner != company_id:
        raise DomainError(409, 'Another company is already named "%s"' % changes['name'])
    new_type = changes.get('company_type', company.company_type)
    if new_type == CompanyType.client.value and company.company_type == CompanyType.agency.value:
        _still_an_agency_of(session, company_id)
    if new_type == CompanyType.agency.value and 'via_company_id' not in changes:
        changes['via_company_id'] = None  # an agency has none: becoming one drops it
    _check_via(session, new_type, changes.get('via_company_id', company.via_company_id), company_id)
    for key, value in changes.items():
        setattr(company, key, value)
    if recruiters is not None:
        _set_recruiters(session, company, recruiters)
    session.commit()
    return get_company(session, company_id)


def replace_company(session: Session, company_id: str, data: CompanyIn) -> Company:
    """PUT: the record becomes exactly what was sent (and is created if it didn't exist)."""
    _check_id(company_id)
    owner = _name_owner(session, data.name)
    if owner and owner != company_id:
        raise DomainError(409, 'Another company is already named "%s"' % data.name)
    fields = _fields(data)
    company = session.get(Company, company_id)
    if company is not None and company.company_type == CompanyType.agency.value and fields['company_type'] == CompanyType.client.value:
        _still_an_agency_of(session, company_id)
    _check_via(session, fields['company_type'], fields['via_company_id'], company_id)
    if company is None:
        company = Company(id=company_id)
        session.add(company)
    for key, value in fields.items():
        setattr(company, key, value)
    session.flush()
    _set_recruiters(session, company, data.recruiters)
    session.commit()
    return get_company(session, company_id)


def delete_company(session: Session, company_id: str):
    company = _get(session, Company, company_id, 'Company')
    count = session.scalar(select(func.count()).select_from(Event).where(_involving(company_id)))
    if count:
        raise DomainError(409, 'This company still has %d event%s. Delete or move them first.' % (count, '' if count == 1 else 's'))
    session.delete(company)  # its recruiters go with it, and its clients become direct
    session.commit()


# ---------- Events ----------


def list_events(session: Session, *, jd_url=None, company_id=None, event=None) -> list[Event]:
    query = select(Event)
    for column, value in ((Event.jd_url, jd_url), (Event.type, event)):
        if value is not None:
            query = query.where(column == value)
    if company_id is not None:
        query = query.where(_involving(company_id))
    query = query.order_by(Event.date.desc(), func.coalesce(Event.time, '').desc(), Event.created_at.desc(), Event.id)
    return list(session.scalars(query).unique())


def get_event(session: Session, event_id: str) -> Event:
    return _get(session, Event, event_id, 'Event')


def _check_event_companies(session: Session, company_id, via_company_id):
    """What an event points to exists; a via is an agency, and only a client's event has one."""
    company = None
    if company_id is not None:
        company = session.get(Company, company_id)
        if company is None:
            raise DomainError(422, 'companyId "%s" does not exist' % company_id)
    if via_company_id is not None:
        via = session.get(Company, via_company_id)
        if via is None:
            raise DomainError(422, 'viaCompanyId "%s" does not exist' % via_company_id)
        if via.company_type != CompanyType.agency.value:
            raise DomainError(422, 'viaCompanyId "%s" is not an agency' % via_company_id)
        if company is None or company.company_type != CompanyType.client.value:
            raise DomainError(422, 'Only an event of a client has a viaCompanyId: the company has to be a client')


def _event_columns(session: Session, fields: dict) -> dict:
    """API field names -> columns, checking that what the event points to exists."""
    columns = {}
    for key, value in fields.items():
        columns['type' if key == 'event' else key] = value.value if hasattr(value, 'value') else value
    if 'company_id' in columns or 'via_company_id' in columns:
        _check_event_companies(session, columns.get('company_id'), columns.get('via_company_id'))
    return columns


def _insert_event(session: Session, event_id: str, columns: dict) -> Event:
    event = Event(id=event_id, **columns)
    session.add(event)
    session.flush()
    return event


def create_event(session: Session, data: EventIn) -> Event:
    event = _insert_event(session, uuid.uuid4().hex[:20], _event_columns(session, data.model_dump()))
    session.commit()
    return event


def _check_passive_message(event_type, company_id):
    if event_type == EventType.passive_message.value and not company_id:
        raise DomainError(422, 'A passive message needs a company: say which one the recruiter works for')


def update_event(session: Session, event_id: str, patch: EventPatch) -> Event:
    event = get_event(session, event_id)
    columns = _event_columns(session, patch.model_dump(exclude_unset=True))
    for key in ('date', 'type'):
        if key in columns and columns[key] is None:
            raise DomainError(422, '"%s" cannot be empty' % ('event' if key == 'type' else key))
    if 'notes' in columns and columns['notes'] is None:
        columns['notes'] = ''
    company_id = columns['company_id'] if 'company_id' in columns else event.company_id
    via_company_id = columns['via_company_id'] if 'via_company_id' in columns else event.via_company_id
    if via_company_id is not None and company_id is None:
        via_company_id = columns['via_company_id'] = None  # no company, no agency in between
    _check_event_companies(session, company_id, via_company_id)
    _check_passive_message(columns.get('type', event.type), company_id)
    for key, value in columns.items():
        setattr(event, key, value)
    session.commit()
    return event


def replace_event(session: Session, event_id: str, data: EventIn) -> Event:
    _check_id(event_id)
    columns = _event_columns(session, data.model_dump())
    event = session.get(Event, event_id)
    if event is None:
        event = _insert_event(session, event_id, columns)
    else:
        for key, value in columns.items():
            setattr(event, key, value)
    session.commit()
    return event


def delete_event(session: Session, event_id: str):
    session.delete(get_event(session, event_id))
    session.commit()
