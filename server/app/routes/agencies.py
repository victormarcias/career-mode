from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from .. import crud
from ..deps import get_session
from ..schemas import AgencyIn, AgencyOut, AgencyPatch

router = APIRouter(prefix='/api/agencies', tags=['agencies'])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get('', response_model=list[AgencyOut], summary='List agencies, by name')
def list_agencies(session: SessionDep):
    return crud.list_agencies(session)


@router.post('', response_model=AgencyOut, status_code=201, summary='Create an agency',
             description='The id is the slug of the name. A name that already exists (ignoring case) is a 409.')
def create_agency(data: AgencyIn, session: SessionDep):
    return crud.create_agency(session, data)


@router.get('/{agency_id}', response_model=AgencyOut)
def get_agency(agency_id: str, session: SessionDep):
    return crud.get_agency(session, agency_id)


@router.patch('/{agency_id}', response_model=AgencyOut, summary='Change some fields of an agency')
def update_agency(agency_id: str, patch: AgencyPatch, session: SessionDep):
    return crud.update_agency(session, agency_id, patch)


@router.put('/{agency_id}', response_model=AgencyOut, summary='Replace an agency (creates it if the id is new)')
def replace_agency(agency_id: str, data: AgencyIn, session: SessionDep):
    return crud.replace_agency(session, agency_id, data)


@router.delete('/{agency_id}', status_code=204, summary='Delete an agency',
               description='Refused with a 409 while it still has events. Its clients become direct.')
def delete_agency(agency_id: str, session: SessionDep):
    crud.delete_agency(session, agency_id)
    return Response(status_code=204)
