from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import crud
from ..deps import get_session
from ..models import CompanyType
from ..schemas import CompanyIn, CompanyOut, CompanyPatch

router = APIRouter(prefix='/api/companies', tags=['companies'])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get('', response_model=list[CompanyOut], summary='List companies, by name',
            description='Agencies and clients together; `companyType` keeps only one kind. `status` is derived from the events.')
def list_companies(session: SessionDep, company_type: Annotated[Optional[CompanyType], Query(alias='companyType')] = None):
    return crud.list_companies(session, company_type.value if company_type else None)


@router.post('', response_model=CompanyOut, status_code=201, summary='Create a company',
             description=(
                 'The id is the slug of the name, and the name is unique among agencies and clients together: a name that already '
                 'exists (ignoring case) is a 409, whichever it is. `companyType` is `agency` or `client`. `viaCompanyId` is the '
                 'agency a client came through; leave it empty for a direct application.'
             ))
def create_company(data: CompanyIn, session: SessionDep):
    return crud.create_company(session, data)


@router.get('/{company_id}', response_model=CompanyOut)
def get_company(company_id: str, session: SessionDep):
    return crud.get_company(session, company_id)


@router.patch('/{company_id}', response_model=CompanyOut, summary='Change some fields of a company',
              description='`companyType` can change (an agency that is really an employer becomes a client), unless the agency still has clients or events that came through it.')
def update_company(company_id: str, patch: CompanyPatch, session: SessionDep):
    return crud.update_company(session, company_id, patch)


@router.put('/{company_id}', response_model=CompanyOut, summary='Replace a company (creates it if the id is new)')
def replace_company(company_id: str, data: CompanyIn, session: SessionDep):
    return crud.replace_company(session, company_id, data)


@router.delete('/{company_id}', status_code=204, summary='Delete a company',
               description='Refused with a 409 while it still has events (its own, or those of a client that came through it). Its clients become direct.')
def delete_company(company_id: str, session: SessionDep):
    crud.delete_company(session, company_id)
    return Response(status_code=204)
