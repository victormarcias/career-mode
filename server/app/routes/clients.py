from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from .. import crud
from ..deps import get_session
from ..schemas import ClientIn, ClientOut, ClientPatch

router = APIRouter(prefix='/api/clients', tags=['clients'])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get('', response_model=list[ClientOut], summary='List clients, by name')
def list_clients(session: SessionDep):
    return crud.list_clients(session)


@router.post('', response_model=ClientOut, status_code=201, summary='Create a client',
             description='`viaAgencyId` is the agency it came through; leave it empty for a direct application.')
def create_client(data: ClientIn, session: SessionDep):
    return crud.create_client(session, data)


@router.get('/{client_id}', response_model=ClientOut)
def get_client(client_id: str, session: SessionDep):
    return crud.get_client(session, client_id)


@router.patch('/{client_id}', response_model=ClientOut, summary='Change some fields of a client')
def update_client(client_id: str, patch: ClientPatch, session: SessionDep):
    return crud.update_client(session, client_id, patch)


@router.put('/{client_id}', response_model=ClientOut, summary='Replace a client (creates it if the id is new)')
def replace_client(client_id: str, data: ClientIn, session: SessionDep):
    return crud.replace_client(session, client_id, data)


@router.delete('/{client_id}', status_code=204, summary='Delete a client',
               description='Refused with a 409 while it still has events.')
def delete_client(client_id: str, session: SessionDep):
    crud.delete_client(session, client_id)
    return Response(status_code=204)
