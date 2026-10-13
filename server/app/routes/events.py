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
    agency_id: Annotated[Optional[str], Query(alias='agencyId')] = None,
    client_id: Annotated[Optional[str], Query(alias='clientId')] = None,
    event: Optional[EventType] = None,
):
    return crud.list_events(session, jd_url=jd_url, agency_id=agency_id, client_id=client_id, event=event.value if event else None)


@router.post('', response_model=EventOut, status_code=201, summary='Create an event',
             description=(
                 'A new event sets its agency\'s status: a closing one (rejection, red_flag, on_hold, offer, archive) '
                 'archives it, any other reactivates it. A `passive_message` must have an `agencyId`.'
             ))
def create_event(data: EventIn, session: SessionDep):
    return crud.create_event(session, data)


@router.get('/{event_id}', response_model=EventOut)
def get_event(event_id: str, session: SessionDep):
    return crud.get_event(session, event_id)


@router.patch('/{event_id}', response_model=EventOut, summary='Change some fields of an event',
              description="Editing an event never changes its agency's status.")
def update_event(event_id: str, patch: EventPatch, session: SessionDep):
    return crud.update_event(session, event_id, patch)


@router.put('/{event_id}', response_model=EventOut, summary='Replace an event (creates it if the id is new)')
def replace_event(event_id: str, data: EventIn, session: SessionDep):
    return crud.replace_event(session, event_id, data)


@router.delete('/{event_id}', status_code=204, summary='Delete an event')
def delete_event(event_id: str, session: SessionDep):
    crud.delete_event(session, event_id)
    return Response(status_code=204)
