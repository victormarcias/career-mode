"""The database schema, as SQLAlchemy models.

Companies (agencies and clients, in one table) and events reference each other with real foreign keys, so
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
    passive_message = 'passive_message'  # a recruiter reached out first: tied to the company they work for
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
# Events that end a process: when it is the latest of a company, the company is archived.
CLOSING_EVENTS = (EventType.rejection, EventType.red_flag, EventType.on_hold, EventType.offer, EventType.archive)


class ApplyType(str, Enum):
    email_apply = 'email_apply'
    web_form = 'web_form'


class CompanyType(str, Enum):
    """What a company is for the person looking for work. A company is one or the other, never both."""

    agency = 'agency'  # a staffing, recruiting or consulting company that places people with other companies
    client = 'client'  # the employer: a company that hires for itself, whether it came through an agency or not


class CompanyStatus(str, Enum):
    """Not stored: derived from a company's events (see crud.company_status)."""

    active = 'active'
    archived = 'archived'


def _in(column, values):
    return '%s IN (%s)' % (column, ', '.join("'%s'" % v for v in values))


class Company(Base):
    """An agency or a client, in one table: its name is unique whichever it is. Its status (active or archived)
    is not stored: it is derived from its events (see crud.company_status)."""

    __tablename__ = 'companies'

    id: Mapped[str] = mapped_column(String, primary_key=True)  # slug of the name, stable once created
    name: Mapped[str] = mapped_column(String(collation='NOCASE'), unique=True)
    company_type: Mapped[str] = mapped_column(String)
    notes: Mapped[str] = mapped_column(String, server_default='')  # what the company does, in a line, and anything useful
    website: Mapped[Optional[str]]
    linkedin: Mapped[Optional[str]]
    application_link: Mapped[Optional[str]]  # a URL or a bare email address
    # A client that came through an agency says which; NULL = applied straight to the company
    via_company_id: Mapped[Optional[str]] = mapped_column(ForeignKey('companies.id', ondelete='SET NULL', onupdate='CASCADE'))

    recruiters: Mapped[list['CompanyRecruiter']] = relationship(
        order_by='CompanyRecruiter.position', cascade='all, delete-orphan', passive_deletes=True, lazy='selectin'
    )

    __table_args__ = (
        CheckConstraint('length(trim(name)) > 0', name='name_not_blank'),
        CheckConstraint(_in('company_type', [t.value for t in CompanyType]), name='company_type_valid'),
        CheckConstraint("via_company_id IS NULL OR company_type = 'client'", name='only_a_client_has_a_via'),
    )


class CompanyRecruiter(Base):
    __tablename__ = 'company_recruiters'

    company_id: Mapped[str] = mapped_column(ForeignKey('companies.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    position: Mapped[int] = mapped_column(primary_key=True)  # keeps the order they were entered in
    url: Mapped[str]  # the recruiter's LinkedIn profile


class Event(Base):
    __tablename__ = 'events'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    date: Mapped[str]  # 2026-10-08
    time: Mapped[Optional[str]]  # 15:30
    type: Mapped[str]
    # an event can't outlive the company it belongs to: delete or move the events first
    company_id: Mapped[Optional[str]] = mapped_column(ForeignKey('companies.id', ondelete='RESTRICT', onupdate='CASCADE'), index=True)
    # the agency a client's application came through, when the event has one
    via_company_id: Mapped[Optional[str]] = mapped_column(ForeignKey('companies.id', ondelete='RESTRICT', onupdate='CASCADE'), index=True)
    notes: Mapped[str] = mapped_column(String, server_default='')
    jd_url: Mapped[Optional[str]]  # the application link: a JD Post link or an email address
    apply_type: Mapped[Optional[str]]
    calendar_event_id: Mapped[Optional[str]] = mapped_column(String, unique=True)  # reserved for the Google Calendar sync
    created_at: Mapped[str] = mapped_column(String, server_default=text("(strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))"))

    company: Mapped[Optional[Company]] = relationship(foreign_keys=[company_id], lazy='joined')
    via: Mapped[Optional[Company]] = relationship(foreign_keys=[via_company_id], lazy='joined')

    __table_args__ = (
        CheckConstraint("date GLOB '[0-9][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]'", name='date_format'),
        CheckConstraint("time IS NULL OR time GLOB '[0-2][0-9]:[0-5][0-9]'", name='time_format'),
        CheckConstraint(_in('type', EVENT_TYPES), name='type_valid'),
        CheckConstraint('apply_type IS NULL OR ' + _in('apply_type', [a.value for a in ApplyType]), name='apply_type_valid'),
        # a recruiter reaching out is tied to the company they work for
        CheckConstraint("type <> 'passive_message' OR company_id IS NOT NULL", name='passive_message_has_company'),
        CheckConstraint('via_company_id IS NULL OR company_id IS NOT NULL', name='via_needs_a_company'),
    )

    # What the API calls them (the front end has always said `event` and `companyLabel`).
    @property
    def event(self) -> str:
        return self.type

    @property
    def company_label(self) -> str:
        """Derived, never stored: "Agency → Client" when the event came through an agency, else the company's name, else a dash."""
        if self.company is None:
            return '—'
        return '%s → %s' % (self.via.name, self.company.name) if self.via else self.company.name
