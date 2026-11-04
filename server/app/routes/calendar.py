import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy.orm import Session

from .. import google_calendar, settings
from ..crud import DomainError
from ..deps import get_session
from ..models import CompanyType, EventType
from ..schemas import CamelModel, OptionalText

router = APIRouter(prefix='/api/calendar', tags=['calendar'])
SessionDep = Annotated[Session, Depends(get_session)]


class Range(CamelModel):
    start: datetime.date
    end: datetime.date = Field(description='The last day, included')


class Chosen(CamelModel):
    key: str = Field(description='The `key` the preview gave the event')
    type: EventType = Field(description='hr_intro, tech_interview or culture_interview')
    company: OptionalText = Field(default=None, description='A new event needs a company, by name; one that does not exist is created')
    company_type: Optional[CompanyType] = Field(default=None, description='agency (the default) or client: what a new company is, and what an existing one must already be')
    via: OptionalText = Field(default=None, description='For a client: the agency it came through, by name; one that does not exist is created')


class SyncIn(Range):
    events: list[Chosen] = Field(description='Only these are logged; a type other than hr_intro, tech_interview or culture_interview is refused')


class PreviewEvent(CamelModel):
    key: str
    summary: str
    notes: str = Field(description='What the event\'s notes would hold: the Google event\'s title and description')
    date: str
    time: str
    company: Optional[str] = Field(description='The company to offer (from the description\'s "Company:" line), or the one a moved event has')
    company_type: Optional[CompanyType]
    via: Optional[str] = Field(description='For a client: the agency it came through')
    action: str = Field(description='"new" or "moved" (already logged, but its day or time changed in Google)')
    type: EventType = Field(description='What to log it as: tech_interview when the title says "tech", culture_interview when it says "culture", else hr_intro')


class PreviewOut(CamelModel):
    events: list[PreviewEvent]
    unchanged: int
    recurring_skipped: int


class SyncOut(CamelModel):
    created: int
    updated: int


def _calendar_text(data: Range, request: Request) -> str:
    calendar_id = settings.get('GOOGLE_CALENDAR_ID', request.app.state.env_path)
    if not calendar_id:
        raise DomainError(409, 'Google Calendar is not synced: set the Calendar ID in Settings first')
    if data.end < data.start:
        raise DomainError(422, 'end is before start')
    return request.app.state.fetch_ics(google_calendar.ics_url(calendar_id))


@router.post('/preview', response_model=PreviewOut, summary='What a sync of a date range would add',
             description=(
                 'Reads the calendar named by the `GOOGLE_CALENDAR_ID` setting and changes nothing. Repeating events are counted, '
                 'not listed, because they are not expanded.'
             ))
def preview(data: Range, session: SessionDep, request: Request):
    return google_calendar.plan_range(session, _calendar_text(data, request), data.start, data.end)


@router.post('/sync', response_model=SyncOut, summary='Log the chosen Google Calendar events of a date range',
             description=(
                 'Each event is logged once (its calendar id is kept on the event) with the type and the company chosen '
                 'for it (one that does not exist is created), and its notes are the Google event\'s title and description. One '
                 'that moved only gets its new date and time. Anything not listed in `events` is left alone.'
             ))
def sync(data: SyncIn, session: SessionDep, request: Request):
    wrong = [c.type.value for c in data.events if c.type not in google_calendar.SYNC_TYPES]
    if wrong:
        raise DomainError(422, 'An event of the calendar can only be an hr_intro, a tech_interview or a culture_interview, not "%s"' % wrong[0])
    text = _calendar_text(data, request)
    chosen = {c.key: google_calendar.Choice(c.type, c.company, c.company_type.value if c.company_type else None, c.via) for c in data.events}
    return google_calendar.apply_range(session, text, data.start, data.end, chosen)
