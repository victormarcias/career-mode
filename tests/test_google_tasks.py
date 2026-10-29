"""Google Tasks sync: the links in the tasks, what gets queued, and the route. Nothing here reaches Google."""
import pytest

from app import google_tasks

CREDENTIALS = 'GOOGLE_TASKS_CLIENT_ID=id\nGOOGLE_TASKS_CLIENT_SECRET=secret\nGOOGLE_TASKS_REFRESH_TOKEN=token\n'


def feed(client, env_path, *texts):
    """The open tasks have these texts; whatever is marked completed is collected in the list that comes back."""
    env_path.write_text(CREDENTIALS)
    done = []
    client.app.state.fetch_tasks = lambda *credentials: [{'list': 'L', 'id': 't%d' % i, 'text': text} for i, text in enumerate(texts)]
    client.app.state.complete_tasks = lambda *credentials_and_tasks: done.extend(task['id'] for task in credentials_and_tasks[-1])
    return done


def test_it_takes_every_link_once_without_the_punctuation_of_the_sentence():
    texts = ['Apply https://acme.example/jobs/1?ref=x.\nnotes', 'see (https://acme.example/jobs/2) and https://acme.example/jobs/1?ref=x', 'no link here']
    assert google_tasks.links_in(texts) == ['https://acme.example/jobs/1?ref=x', 'https://acme.example/jobs/2']


def test_it_refuses_without_the_settings(client, env_path):
    env_path.write_text('GOOGLE_TASKS_CLIENT_ID=id\n')
    r = client.post('/api/google-tasks/sync')
    assert r.status_code == 409 and 'Settings' in r.json()['detail']


def test_it_queues_each_new_link_as_a_pending_event(client, env_path):
    feed(client, env_path, 'Acme https://acme.example/jobs/1', 'https://acme.example/jobs/2')
    assert client.post('/api/google-tasks/sync').json() == {'found': 2, 'queued': 2, 'existing': 0, 'completed': 2, 'completeError': None}
    pending = client.get('/api/events', params={'event': 'pending'}).json()
    assert sorted(e['jdUrl'] for e in pending) == ['https://acme.example/jobs/1', 'https://acme.example/jobs/2']
    assert {(e['applyType'], e['companyId']) for e in pending} == {('web_form', None)}


def test_a_link_an_event_has_already_is_skipped_so_a_second_sync_adds_nothing(client, env_path):
    client.post('/api/companies', json={'name': 'Acme', 'companyType': 'client'})
    company = client.get('/api/companies').json()[0]['id']
    client.post('/api/events', json={'date': '2026-10-01', 'event': 'application', 'companyId': company, 'jdUrl': 'https://acme.example/jobs/1'})
    feed(client, env_path, 'https://acme.example/jobs/1', 'https://acme.example/jobs/2')
    assert client.post('/api/google-tasks/sync').json() == {'found': 2, 'queued': 1, 'existing': 1, 'completed': 2, 'completeError': None}
    assert client.post('/api/google-tasks/sync').json() == {'found': 2, 'queued': 0, 'existing': 2, 'completed': 2, 'completeError': None}
    assert len(client.get('/api/events').json()) == 2


def test_a_google_error_is_said_and_queues_nothing(client, env_path):
    env_path.write_text(CREDENTIALS)

    def refuse(*credentials):
        raise google_tasks.crud.DomainError(502, 'Google Tasks answered an error')

    client.app.state.fetch_tasks = refuse
    assert client.post('/api/google-tasks/sync').status_code == 502
    assert client.get('/api/events').json() == []


def test_a_task_is_marked_completed_once_its_links_are_in_pending_and_one_without_a_link_is_left(client, env_path):
    done = feed(client, env_path, 'Acme https://acme.example/jobs/1', 'buy milk', 'two https://a.example/1 https://a.example/2')
    assert client.post('/api/google-tasks/sync').json()['completed'] == 2
    assert done == ['t0', 't2']


def test_when_google_refuses_to_complete_the_links_are_queued_all_the_same(client, env_path):
    feed(client, env_path, 'https://acme.example/jobs/1')

    def refuse(*credentials_and_tasks):
        raise google_tasks.crud.DomainError(502, 'needs the tasks scope')

    client.app.state.complete_tasks = refuse
    assert client.post('/api/google-tasks/sync').json() == {'found': 1, 'queued': 1, 'existing': 0, 'completed': 0, 'completeError': 'needs the tasks scope'}
    assert len(client.get('/api/events', params={'event': 'pending'}).json()) == 1
