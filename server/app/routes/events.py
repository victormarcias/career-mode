from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import crud
from ..deps import get_session
from ..models import EventType
from ..schemas import EventIn, EventOut, EventPatch

router = APIRouter(prefix='/api/events', tags=['events'])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get('', response_model=list[EventOut], summary='List events, newest first')
def list_events(
    session: SessionDep,
    jd_url: Annotated[Optional[str], Query(alias='jdUrl')] = None,
    company_id: Annotated[Optional[str], Query(alias='companyId', description='The events of this company, and those of the clients that came through it')] = None,
    event: Optional[EventType] = None,
):
    return crud.list_events(session, jd_url=jd_url, company_id=company_id, event=event.value if event else None)


@router.post('', response_model=EventOut, status_code=201, summary='Create an event',
             description=(
                 '`companyId` is the company the event is about (the client, or the agency when there is no client) and '
                 '`viaCompanyId` the agency a client\'s application came through. A company is archived when its latest event '
                 'closes the process (rejection, red_flag, on_hold, offer, archive) and active again with any later one: the '
                 'status is derived, never set. A `passive_message` must have a `companyId`.'
             ))
def create_event(data: EventIn, session: SessionDep):
    return crud.create_event(session, data)


@router.get('/{event_id}', response_model=EventOut)
def get_event(event_id: str, session: SessionDep):
    return crud.get_event(session, event_id)


@router.patch('/{event_id}', response_model=EventOut, summary='Change some fields of an event',
              description="`companyId` and `viaCompanyId` follow the same rules as when it is created. A company's status is derived from its events, so changing the latest one of a company can change its status too.")
def update_event(event_id: str, patch: EventPatch, session: SessionDep):
    return crud.update_event(session, event_id, patch)


@router.put('/{event_id}', response_model=EventOut, summary='Replace an event (creates it if the id is new)')
def replace_event(event_id: str, data: EventIn, session: SessionDep):
    return crud.replace_event(session, event_id, data)


@router.delete('/{event_id}', status_code=204, summary='Delete an event')
def delete_event(event_id: str, session: SessionDep):
    crud.delete_event(session, event_id)
    return Response(status_code=204)
