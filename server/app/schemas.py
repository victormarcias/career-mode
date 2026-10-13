"""Request and response shapes (Pydantic).

The JSON uses the camelCase names the front end has always used (`agencyId`,
`jdUrl`, ...); the Python side uses snake_case. FastAPI turns these models into
the interactive docs at /docs.
"""
import datetime
import re
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, field_validator, model_validator
from pydantic.alias_generators import to_camel

from .models import AgencyStatus, ApplyType, EventType


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        extra='ignore',  # the old front end also sent `id` and `companyLabel`: both are derived now
    )


def _blank_to_none(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


# Text that may be left empty: blank means "not set", and it is stored as NULL.
OptionalText = Annotated[Optional[str], BeforeValidator(_blank_to_none)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


# ---------- Agencies ----------


class AgencyFields(CamelModel):
    type: Annotated[str, BeforeValidator(lambda v: (v or '').strip() if isinstance(v, str) or v is None else v)] = ''
    website: OptionalText = None
    linkedin: OptionalText = None
    application_link: OptionalText = None
    recruiters: list[str] = Field(default_factory=list, description="LinkedIn profile links, in the order entered")

    @field_validator('recruiters', mode='before')
    @classmethod
    def _recruiters(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return [u.strip() for u in value if isinstance(u, str) and u.strip()]
        return value


class AgencyIn(AgencyFields):
    """Create (POST) or replace (PUT)."""

    name: Name
    # The old Firestore data stored "no status" as null: that means active.
    status: Annotated[AgencyStatus, BeforeValidator(lambda v: v or 'active')] = AgencyStatus.active


class AgencyPatch(CamelModel):
    """Update (PATCH): only the fields sent are changed."""

    name: Optional[Name] = None
    type: Optional[str] = None
    website: OptionalText = None
    linkedin: OptionalText = None
    application_link: OptionalText = None
    recruiters: Optional[list[str]] = None
    status: Optional[AgencyStatus] = None

    @field_validator('recruiters', mode='before')
    @classmethod
    def _recruiters(cls, value):
        if isinstance(value, list):
            return [u.strip() for u in value if isinstance(u, str) and u.strip()]
        return value


class AgencyOut(CamelModel):
    id: str
    name: str
    type: str
    website: Optional[str]
    linkedin: Optional[str]
    application_link: Optional[str]
    recruiters: list[str]
    status: AgencyStatus

    @field_validator('recruiters', mode='before')
    @classmethod
    def _urls(cls, value):
        return [r.url if hasattr(r, 'url') else r for r in value]


# ---------- Clients ----------


class ClientIn(CamelModel):
    """Create (POST) or replace (PUT)."""

    name: Name
    website: OptionalText = None
    linkedin: OptionalText = None
    notes: Annotated[str, BeforeValidator(lambda v: (v or '').strip() if isinstance(v, str) or v is None else v)] = ''
    via_agency_id: OptionalText = Field(default=None, description='The agency this client came through; empty = applied directly')


class ClientPatch(CamelModel):
    name: Optional[Name] = None
    website: OptionalText = None
    linkedin: OptionalText = None
    notes: Optional[str] = None
    via_agency_id: OptionalText = None


class ClientOut(CamelModel):
    id: str
    name: str
    website: Optional[str]
    linkedin: Optional[str]
    notes: str
    via_agency_id: Optional[str]


# ---------- Events ----------

_DATE = 'a real date like 2026-10-08'


def _check_date(value):
    try:
        datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError('must be %s' % _DATE)
    return value


def _check_time(value):
    if value is not None and not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', value):
        raise ValueError('must look like 15:30')
    return value


class EventIn(CamelModel):
    """Create (POST) or replace (PUT)."""

    date: str = Field(description='2026-10-08')
    time: OptionalText = Field(default=None, description='15:30, or empty when there is no set time')
    event: EventType
    agency_id: OptionalText = None
    client_id: OptionalText = None
    notes: Annotated[str, BeforeValidator(lambda v: (v or '').strip() if isinstance(v, str) or v is None else v)] = ''
    jd_url: OptionalText = Field(default=None, description='Application link: a JD Post link or an email address')
    apply_type: Annotated[Optional[ApplyType], BeforeValidator(_blank_to_none)] = None
    calendar_event_id: OptionalText = None

    _date = field_validator('date')(_check_date)
    _time = field_validator('time')(_check_time)

    @model_validator(mode='after')
    def _passive_message_needs_an_agency(self):
        if self.event == EventType.passive_message and not self.agency_id:
            raise ValueError('A passive message needs an agency: say which agency the recruiter works for')
        return self


class EventPatch(CamelModel):
    date: Optional[str] = None
    time: OptionalText = None
    event: Optional[EventType] = None
    agency_id: OptionalText = None
    client_id: OptionalText = None
    notes: Optional[str] = None
    jd_url: OptionalText = None
    apply_type: Annotated[Optional[ApplyType], BeforeValidator(_blank_to_none)] = None
    calendar_event_id: OptionalText = None

    @field_validator('date')
    @classmethod
    def _date(cls, value):
        return value if value is None else _check_date(value)

    @field_validator('time')
    @classmethod
    def _time(cls, value):
        return _check_time(value)


class EventOut(CamelModel):
    id: str
    date: str
    time: Optional[str]
    event: EventType
    agency_id: Optional[str]
    client_id: Optional[str]
    company_label: str = Field(description="The agency's name, else the direct client's, else '—'. Derived, never stored.")
    notes: str
    jd_url: Optional[str]
    apply_type: Optional[ApplyType]
    calendar_event_id: Optional[str]


class Snapshot(CamelModel):
    agencies: list[AgencyOut]
    clients: list[ClientOut]
    events: list[EventOut]
