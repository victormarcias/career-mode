"""The database schema, as SQLAlchemy models.

Agencies, clients and events reference each other with real foreign keys, so
the database itself refuses a dangling reference, a duplicate company name or a
passive message with no company. Alembic reads `Base.metadata` from here; after
changing a model, run `alembic revision --autogenerate -m "what changed"` from
the server/ folder (see CLAUDE.md).
"""
from enum import Enum
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, MetaData, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Names for every constraint, so migrations can refer to them (SQLite needs that
# to alter a table) and an error message says which rule was broken.
NAMING_CONVENTION = {
    'ix': 'ix_%(column_0_label)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s',
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class EventType(str, Enum):
    """The single list of event types. public/js/events.js mirrors it for labels and colors:
    change the two together."""

    application = 'application'
    passive_message = 'passive_message'  # a recruiter reached out first: tied to an agency or a client
    note = 'note'
    tech_filter = 'tech_filter'
    hr_intro = 'hr_intro'
    tech_interview = 'tech_interview'
    culture_interview = 'culture_interview'
    on_hold = 'on_hold'
    offer = 'offer'
    rejection = 'rejection'
    red_flag = 'red_flag'
    archive = 'archive'
    pending = 'pending'  # a queued link that "Apply Bulk links" will turn into an application


EVENT_TYPES = [t.value for t in EventType]
# Events that end a process: creating one archives its agency.
CLOSING_EVENTS = (EventType.rejection, EventType.red_flag, EventType.on_hold, EventType.offer, EventType.archive)


class ApplyType(str, Enum):
    email_apply = 'email_apply'
    web_form = 'web_form'


class AgencyStatus(str, Enum):
    active = 'active'
    archived = 'archived'


def _in(column, values):
    return '%s IN (%s)' % (column, ', '.join("'%s'" % v for v in values))


class Agency(Base):
    __tablename__ = 'agencies'

    id: Mapped[str] = mapped_column(String, primary_key=True)  # slug of the name, stable once created
    name: Mapped[str] = mapped_column(String(collation='NOCASE'), unique=True)
    type: Mapped[str] = mapped_column(String, server_default='')  # what the agency does, one line
    website: Mapped[Optional[str]]
    linkedin: Mapped[Optional[str]]
    application_link: Mapped[Optional[str]]  # a URL or a bare email address
    status: Mapped[str] = mapped_column(String, server_default='active')

    recruiters: Mapped[list['AgencyRecruiter']] = relationship(
        order_by='AgencyRecruiter.position', cascade='all, delete-orphan', passive_deletes=True, lazy='selectin'
    )

    __table_args__ = (
        CheckConstraint('length(trim(name)) > 0', name='name_not_blank'),
        CheckConstraint(_in('status', [s.value for s in AgencyStatus]), name='status_valid'),
    )


class AgencyRecruiter(Base):
    __tablename__ = 'agency_recruiters'

    agency_id: Mapped[str] = mapped_column(ForeignKey('agencies.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    position: Mapped[int] = mapped_column(primary_key=True)  # keeps the order they were entered in
    url: Mapped[str]  # the recruiter's LinkedIn profile


class Client(Base):
    __tablename__ = 'clients'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(collation='NOCASE'), unique=True)
    website: Mapped[Optional[str]]
    linkedin: Mapped[Optional[str]]
    notes: Mapped[str] = mapped_column(String, server_default='')
    # NULL = applied straight to the company, no agency in between
    via_agency_id: Mapped[Optional[str]] = mapped_column(ForeignKey('agencies.id', ondelete='SET NULL', onupdate='CASCADE'))

    __table_args__ = (CheckConstraint('length(trim(name)) > 0', name='name_not_blank'),)


class Event(Base):
    __tablename__ = 'events'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    date: Mapped[str]  # 2026-10-08
    time: Mapped[Optional[str]]  # 15:30
    type: Mapped[str]
    # an event can't outlive the company it belongs to: delete or move the events first
    agency_id: Mapped[Optional[str]] = mapped_column(ForeignKey('agencies.id', ondelete='RESTRICT', onupdate='CASCADE'), index=True)
    client_id: Mapped[Optional[str]] = mapped_column(ForeignKey('clients.id', ondelete='RESTRICT', onupdate='CASCADE'), index=True)
    notes: Mapped[str] = mapped_column(String, server_default='')
    jd_url: Mapped[Optional[str]]  # the application link: a JD Post link or an email address
    apply_type: Mapped[Optional[str]]
    calendar_event_id: Mapped[Optional[str]] = mapped_column(String, unique=True)  # reserved for the Google Calendar sync
    created_at: Mapped[str] = mapped_column(String, server_default=text("(strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))"))

    agency: Mapped[Optional[Agency]] = relationship(lazy='joined')
    client: Mapped[Optional[Client]] = relationship(lazy='joined')

    __table_args__ = (
        CheckConstraint("date GLOB '[0-9][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]'", name='date_format'),
        CheckConstraint("time IS NULL OR time GLOB '[0-2][0-9]:[0-5][0-9]'", name='time_format'),
        CheckConstraint(_in('type', EVENT_TYPES), name='type_valid'),
        CheckConstraint('apply_type IS NULL OR ' + _in('apply_type', [a.value for a in ApplyType]), name='apply_type_valid'),
        # a recruiter reaching out is tied to the agency they work for, or to the client that hires directly
        CheckConstraint("type <> 'passive_message' OR agency_id IS NOT NULL OR client_id IS NOT NULL", name='passive_message_has_company'),
    )

    # What the API calls them (the front end has always said `event` and `companyLabel`).
    @property
    def event(self) -> str:
        return self.type

    @property
    def company_label(self) -> str:
        """Derived, never stored: the agency's name, else the (direct) client's, else a dash."""
        return self.agency.name if self.agency else (self.client.name if self.client else '—')
