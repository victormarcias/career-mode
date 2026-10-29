"""Reads the open tasks of the user's Google Tasks and queues the job links in them as pending events.

The three `GOOGLE_TASKS_*` settings are an OAuth client and a refresh token with the Tasks scope: the token is
exchanged for an access token on every call. The tasks are read, and once their links are in an event a task is marked
completed (the only thing written in Google), so the next sync has less to read.
A link already in an event (pending, applied or anything else) is skipped, so a sync can be repeated.
"""
import datetime as dt
import json
import re
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi
from sqlalchemy.orm import Session

from . import crud
from .models import ApplyType, EventType
from .schemas import EventIn

TOKEN_URL = 'https://oauth2.googleapis.com/token'
API = 'https://tasks.googleapis.com/tasks/v1'
LINK = re.compile(r'https?://[^\s<>"\')\]]+')


def _call(url: str, data: bytes = None, token: str = None, method: str = None) -> dict:
    # certifi's certificates, not the system's: see google_calendar.fetch_ics
    context = ssl.create_default_context(cafile=certifi.where())
    headers = {'User-Agent': 'career-mode'}
    if token:
        headers['Authorization'] = 'Bearer %s' % token
    if method == 'PATCH':
        headers['Content-Type'] = 'application/json'
    try:
        with urlopen(Request(url, data=data, headers=headers, method=method), timeout=15, context=context) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as err:
        detail = ''
        try:
            detail = json.loads(err.read().decode('utf-8')).get('error')
            detail = detail if isinstance(detail, str) else (detail or {}).get('message', '')
        except Exception:
            pass
        hint = ''
        if detail == 'invalid_grant':
            hint = ' The refresh token was revoked or has expired: get a new one in the OAuth Playground and save it in Settings.'
        elif err.code == 403:
            hint = ' The refresh token needs the https://www.googleapis.com/auth/tasks scope to mark tasks as done: get a new one in the OAuth Playground with it.'
        raise crud.DomainError(502, 'Google Tasks answered an error (HTTP %d%s).%s Check the Google Tasks settings.' % (err.code, ': ' + detail if detail else '', hint))
    except (URLError, TimeoutError, OSError, ValueError) as err:
        raise crud.DomainError(502, 'Cannot reach Google Tasks: %s' % getattr(err, 'reason', err))


def _token(client_id: str, client_secret: str, refresh_token: str) -> str:
    body = urlencode({'grant_type': 'refresh_token', 'client_id': client_id, 'client_secret': client_secret, 'refresh_token': refresh_token})
    return _call(TOKEN_URL, data=body.encode())['access_token']


def fetch_tasks(client_id: str, client_secret: str, refresh_token: str) -> list:
    """Every open task of every list, as {'list': the list's id, 'id': the task's id, 'text': its title and notes}."""
    token = _token(client_id, client_secret, refresh_token)
    tasks = []
    for task_list in _call('%s/users/@me/lists?maxResults=100' % API, token=token).get('items', []):
        page = None
        while True:
            url = '%s/lists/%s/tasks?showCompleted=false&showHidden=false&maxResults=100' % (API, task_list['id'])
            answer = _call(url + ('&pageToken=%s' % page if page else ''), token=token)
            tasks += [{'list': task_list['id'], 'id': task['id'], 'text': '%s\n%s' % (task.get('title', ''), task.get('notes', ''))} for task in answer.get('items', [])]
            page = answer.get('nextPageToken')
            if not page:
                break
    return tasks


def complete_tasks(client_id: str, client_secret: str, refresh_token: str, tasks: list) -> None:
    """Marks each task ({'list', 'id'}) completed. Needs the `tasks` scope: with the read-only one Google refuses."""
    token = _token(client_id, client_secret, refresh_token)
    for task in tasks:
        _call('%s/lists/%s/tasks/%s' % (API, task['list'], task['id']), data=json.dumps({'status': 'completed'}).encode(), token=token, method='PATCH')


def links_in(texts: list) -> list:
    """Every http(s) link in the texts, as written, once each and in order, without the punctuation that ends a sentence."""
    seen = []
    for text in texts:
        for link in LINK.findall(text):
            link = link.rstrip('.,;:!?')
            if link not in seen:
                seen.append(link)
    return seen


def queue(session: Session, links: list) -> dict:
    """A pending event for each link no event has; the same placeholder the Pending page makes."""
    queued = 0
    for link in links:
        if crud.list_events(session, jd_url=link):
            continue
        crud.create_event(session, EventIn(date=dt.date.today().isoformat(), event=EventType.pending, jd_url=link, apply_type=ApplyType.web_form))
        queued += 1
    return {'found': len(links), 'queued': queued, 'existing': len(links) - queued}
