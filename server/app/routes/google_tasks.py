from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import google_tasks, settings
from ..crud import DomainError
from ..deps import get_session
from ..schemas import CamelModel

router = APIRouter(prefix='/api/google-tasks', tags=['google-tasks'])
SessionDep = Annotated[Session, Depends(get_session)]
NAMES = ('GOOGLE_TASKS_CLIENT_ID', 'GOOGLE_TASKS_CLIENT_SECRET', 'GOOGLE_TASKS_REFRESH_TOKEN')


class SyncOut(CamelModel):
    found: int
    queued: int
    existing: int
    completed: int
    complete_error: Optional[str] = None


@router.post('/sync', response_model=SyncOut, summary='Queue the job links of the open Google Tasks as pending',
             description=(
                 'Reads the open tasks with the `GOOGLE_TASKS_*` settings (read only, nothing is written in Google) and creates a '
                 '`pending` event for each link that no event has. `found` links, `queued` new and `existing` already logged. Then each '
                 'task whose links are all logged is marked completed in Google (`completed` of them); when Google refuses that (the token '
                 'has the read-only scope), the links are queued all the same and `completeError` says why.'
             ))
def sync(session: SessionDep, request: Request):
    values = [settings.get(name, request.app.state.env_path) for name in NAMES]
    if not all(values):
        raise DomainError(409, 'Google Tasks is not synced: set its client ID, client secret and refresh token in Settings first')
    tasks = request.app.state.fetch_tasks(*values)
    result = google_tasks.queue(session, google_tasks.links_in([task['text'] for task in tasks]))
    # every link of these tasks is in an event now: they are done
    done = [{'list': task['list'], 'id': task['id']} for task in tasks if google_tasks.links_in([task['text']])]
    result['completed'], result['completeError'] = 0, None
    try:
        request.app.state.complete_tasks(*values, done)
        result['completed'] = len(done)
    except DomainError as err:
        result['completeError'] = err.message
    return result
