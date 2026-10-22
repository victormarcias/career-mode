"""Request and response shapes (Pydantic).

The JSON uses the camelCase names the front end has always used (`companyId`,
`jdUrl`, ...); the Python side uses snake_case. FastAPI turns these models into
the interactive docs at /docs.
"""
import datetime
import re
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, field_validator, model_validator
from pydantic.alias_generators import to_camel

from .models import ApplyType, CompanyStatus, CompanyType, EventType


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


# ---------- Companies ----------


def _recruiter_urls(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [u.strip() for u in value if isinstance(u, str) and u.strip()]
    return value


class CompanyFields(CamelModel):
    notes: Annotated[str, BeforeValidator(lambda v: (v or '').strip() if isinstance(v, str) or v is None else v)] = Field(
        default='', description='What the company does, in a line, and anything useful')
    website: OptionalText = None
    linkedin: OptionalText = None
    application_link: OptionalText = None
    recruiters: list[str] = Field(default_factory=list, description='LinkedIn profile links, in the order entered')
    via_company_id: OptionalText = Field(
        default=None, description='For a client: the agency it came through; empty = applied directly. Only a client has one')

    @field_validator('recruiters', mode='before')
    @classmethod
    def _recruiters(cls, value):
        return _recruiter_urls(value)


class CompanyIn(CompanyFields):
    """Create (POST) or replace (PUT)."""

    name: Name
    company_type: CompanyType = Field(description='agency or client: a company is one or the other, and its name is unique either way')


class CompanyPatch(CamelModel):
    """Update (PATCH): only the fields sent are changed."""

    name: Optional[Name] = None
    company_type: Optional[CompanyType] = None
    notes: Optional[str] = None
    website: OptionalText = None
    linkedin: OptionalText = None
    application_link: OptionalText = None
    recruiters: Optional[list[str]] = None
    via_company_id: OptionalText = None

    @field_validator('recruiters', mode='before')
    @classmethod
    def _recruiters(cls, value):
        return _recruiter_urls(value) if isinstance(value, list) else value


class CompanyOut(CamelModel):
    id: str
    name: str
    company_type: CompanyType
    notes: str
    website: Optional[str]
    linkedin: Optional[str]
    application_link: Optional[str]
    recruiters: list[str]
    via_company_id: Optional[str]
    status: CompanyStatus = Field(description='Derived, never stored: archived when the latest event of the company (or of a client that came through it) closes its process')

    @field_validator('recruiters', mode='before')
    @classmethod
    def _urls(cls, value):
        return [r.url if hasattr(r, 'url') else r for r in value]


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
    company_id: OptionalText = Field(default=None, description='The company the event is about: the client, or the agency when there is no client')
    via_company_id: OptionalText = Field(default=None, description='The agency a client\'s application came through, when there is one')
    notes: Annotated[str, BeforeValidator(lambda v: (v or '').strip() if isinstance(v, str) or v is None else v)] = ''
    jd_url: OptionalText = Field(default=None, description='Application link: a JD Post link or an email address')
    apply_type: Annotated[Optional[ApplyType], BeforeValidator(_blank_to_none)] = None
    calendar_event_id: OptionalText = None

    _date = field_validator('date')(_check_date)
    _time = field_validator('time')(_check_time)

    @model_validator(mode='after')
    def _passive_message_needs_a_company(self):
        if self.event == EventType.passive_message and not self.company_id:
            raise ValueError('A passive message needs a company: say which one the recruiter works for')
        return self


class EventPatch(CamelModel):
    date: Optional[str] = None
    time: OptionalText = None
    event: Optional[EventType] = None
    company_id: OptionalText = None
    via_company_id: OptionalText = None
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
    company_id: Optional[str]
    via_company_id: Optional[str]
    company_label: str = Field(description="'Agency → Client' when the event came through an agency, else the company's name, else '—'. Derived, never stored.")
    notes: str
    jd_url: Optional[str]
    apply_type: Optional[ApplyType]
    calendar_event_id: Optional[str]


class Snapshot(CamelModel):
    companies: list[CompanyOut]
    events: list[EventOut]
