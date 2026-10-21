"""Business rules and queries. The API routes and the importer both go through here."""
import re
import unicodedata
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import CLOSING_EVENTS, Agency, AgencyRecruiter, AgencyStatus, Client, Event, EventType
from .schemas import AgencyIn, AgencyPatch, ClientIn, ClientPatch, EventIn, EventPatch


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


def _name_owner(session: Session, model, name: str):
    """The id of whoever already has this name (the column compares ignoring case)."""
    return session.scalar(select(model.id).where(model.name == name))


def find_company(session: Session, model, name: str):
    """The agency or client with this name (ignoring case), or whose id is its slug, like the front end finds it."""
    owner = _name_owner(session, model, name.strip()) or slugify(name)
    return session.get(model, owner) if owner else None


# ---------- Agencies ----------


def list_agencies(session: Session) -> list[Agency]:
    return list(session.scalars(select(Agency).order_by(Agency.name)))


def get_agency(session: Session, agency_id: str) -> Agency:
    return _get(session, Agency, agency_id, 'Agency')


def _set_recruiters(session: Session, agency: Agency, urls: list[str]):
    agency.recruiters.clear()
    session.flush()  # the old rows go first, or the new ones would clash on (agency, position)
    agency.recruiters.extend(AgencyRecruiter(position=i, url=url) for i, url in enumerate(urls))


def create_agency(session: Session, data: AgencyIn) -> Agency:
    if _name_owner(session, Agency, data.name):
        raise DomainError(409, 'An agency named "%s" already exists' % data.name)
    slug = slugify(data.name)
    if not slug:
        raise DomainError(422, 'The name needs at least one letter or digit')
    agency = Agency(id=_unique_id(session, Agency, slug), **data.model_dump(exclude={'recruiters'}))
    session.add(agency)
    session.flush()
    _set_recruiters(session, agency, data.recruiters)
    session.commit()
    return agency


def update_agency(session: Session, agency_id: str, patch: AgencyPatch) -> Agency:
    agency = get_agency(session, agency_id)
    changes = patch.model_dump(exclude_unset=True)
    recruiters = changes.pop('recruiters', None)
    for key in ('name', 'type', 'status'):  # these columns can't be NULL
        if key in changes and changes[key] is None:
            raise DomainError(422, '"%s" cannot be empty' % key)
    owner = _name_owner(session, Agency, changes['name']) if 'name' in changes else None
    if owner and owner != agency_id:
        raise DomainError(409, 'Another agency is already named "%s"' % changes['name'])
    for key, value in changes.items():
        setattr(agency, key, value)
    if recruiters is not None:
        _set_recruiters(session, agency, recruiters)
    session.commit()
    return agency


def replace_agency(session: Session, agency_id: str, data: AgencyIn) -> Agency:
    """PUT: the record becomes exactly what was sent (and is created if it didn't exist)."""
    _check_id(agency_id)
    owner = _name_owner(session, Agency, data.name)
    if owner and owner != agency_id:
        raise DomainError(409, 'Another agency is already named "%s"' % data.name)
    agency = session.get(Agency, agency_id)
    if agency is None:
        agency = Agency(id=agency_id)
        session.add(agency)
    for key, value in data.model_dump(exclude={'recruiters'}).items():
        setattr(agency, key, value)
    session.flush()
    _set_recruiters(session, agency, data.recruiters)
    session.commit()
    return agency


def delete_agency(session: Session, agency_id: str):
    agency = get_agency(session, agency_id)
    count = session.scalar(select(func.count()).select_from(Event).where(Event.agency_id == agency_id))
    if count:
        raise DomainError(409, 'This agency still has %d event%s. Delete or move them first.' % (count, '' if count == 1 else 's'))
    session.delete(agency)  # its recruiters go with it, and its clients become direct
    session.commit()


# ---------- Clients ----------


def list_clients(session: Session) -> list[Client]:
    return list(session.scalars(select(Client).order_by(Client.name)))


def get_client(session: Session, client_id: str) -> Client:
    return _get(session, Client, client_id, 'Client')


def _require_agency(session: Session, agency_id, field='agencyId'):
    if agency_id is not None and session.get(Agency, agency_id) is None:
        raise DomainError(422, '%s "%s" does not exist' % (field, agency_id))


def create_client(session: Session, data: ClientIn) -> Client:
    if _name_owner(session, Client, data.name):
        raise DomainError(409, 'A client named "%s" already exists' % data.name)
    slug = slugify(data.name)
    if not slug:
        raise DomainError(422, 'The name needs at least one letter or digit')
    _require_agency(session, data.via_agency_id, 'viaAgencyId')
    client = Client(id=_unique_id(session, Client, slug), **data.model_dump())
    session.add(client)
    session.commit()
    return client


def update_client(session: Session, client_id: str, patch: ClientPatch) -> Client:
    client = get_client(session, client_id)
    changes = patch.model_dump(exclude_unset=True)
    for key in ('name', 'notes'):
        if key in changes and changes[key] is None:
            raise DomainError(422, '"%s" cannot be empty' % key)
    owner = _name_owner(session, Client, changes['name']) if 'name' in changes else None
    if owner and owner != client_id:
        raise DomainError(409, 'Another client is already named "%s"' % changes['name'])
    if 'via_agency_id' in changes:
        _require_agency(session, changes['via_agency_id'], 'viaAgencyId')
    for key, value in changes.items():
        setattr(client, key, value)
    session.commit()
    return client


def replace_client(session: Session, client_id: str, data: ClientIn) -> Client:
    _check_id(client_id)
    owner = _name_owner(session, Client, data.name)
    if owner and owner != client_id:
        raise DomainError(409, 'Another client is already named "%s"' % data.name)
    _require_agency(session, data.via_agency_id, 'viaAgencyId')
    client = session.get(Client, client_id)
    if client is None:
        client = Client(id=client_id)
        session.add(client)
    for key, value in data.model_dump().items():
        setattr(client, key, value)
    session.commit()
    return client


def delete_client(session: Session, client_id: str):
    client = get_client(session, client_id)
    count = session.scalar(select(func.count()).select_from(Event).where(Event.client_id == client_id))
    if count:
        raise DomainError(409, 'This client still has %d event%s. Delete or move them first.' % (count, '' if count == 1 else 's'))
    session.delete(client)
    session.commit()


# ---------- Events ----------


def list_events(session: Session, *, jd_url=None, agency_id=None, client_id=None, event=None) -> list[Event]:
    query = select(Event)
    for column, value in ((Event.jd_url, jd_url), (Event.agency_id, agency_id), (Event.client_id, client_id), (Event.type, event)):
        if value is not None:
            query = query.where(column == value)
    query = query.order_by(Event.date.desc(), func.coalesce(Event.time, '').desc(), Event.created_at.desc(), Event.id)
    return list(session.scalars(query).unique())


def get_event(session: Session, event_id: str) -> Event:
    return _get(session, Event, event_id, 'Event')


def _event_columns(session: Session, fields: dict) -> dict:
    """API field names -> columns, checking that what the event points to exists."""
    columns = {}
    for key, value in fields.items():
        columns['type' if key == 'event' else key] = value.value if hasattr(value, 'value') else value
    _require_agency(session, columns.get('agency_id'), 'agencyId')
    if columns.get('client_id') is not None and session.get(Client, columns['client_id']) is None:
        raise DomainError(422, 'clientId "%s" does not exist' % columns['client_id'])
    return columns


def _apply_status_rule(session: Session, agency_id, event_type):
    """A new event reactivates its agency, unless it closes the process, which archives it."""
    if agency_id:
        agency = session.get(Agency, agency_id)
        agency.status = (AgencyStatus.archived if EventType(event_type) in CLOSING_EVENTS else AgencyStatus.active).value


def _insert_event(session: Session, event_id: str, columns: dict) -> Event:
    event = Event(id=event_id, **columns)
    session.add(event)
    session.flush()
    _apply_status_rule(session, columns.get('agency_id'), columns['type'])
    return event


def create_event(session: Session, data: EventIn) -> Event:
    event = _insert_event(session, uuid.uuid4().hex[:20], _event_columns(session, data.model_dump()))
    session.commit()
    return event


def _check_passive_message(event_type, agency_id, client_id):
    if event_type == EventType.passive_message.value and not (agency_id or client_id):
        raise DomainError(422, 'A passive message needs an agency or a client: say which company the recruiter works for')


def update_event(session: Session, event_id: str, patch: EventPatch) -> Event:
    event = get_event(session, event_id)
    columns = _event_columns(session, patch.model_dump(exclude_unset=True))
    for key in ('date', 'type'):
        if key in columns and columns[key] is None:
            raise DomainError(422, '"%s" cannot be empty' % ('event' if key == 'type' else key))
    if 'notes' in columns and columns['notes'] is None:
        columns['notes'] = ''
    _check_passive_message(columns.get('type', event.type), columns['agency_id'] if 'agency_id' in columns else event.agency_id,
                           columns['client_id'] if 'client_id' in columns else event.client_id)
    # Editing an event never flips its agency's status: the edited one isn't
    # necessarily the agency's latest, so the status could end up wrong.
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
