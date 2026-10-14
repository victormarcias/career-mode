"""Fixtures: every test gets its own empty database, migrated by Alembic like a real start."""
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import make_engine
from app.main import LOCAL_HOSTS, create_app


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / 'test.db'


@pytest.fixture
def env_path(tmp_path):
    """A throwaway .env, so no test ever touches the real one."""
    return tmp_path / '.env'


@pytest.fixture
def client(db_path, env_path):
    """The app in-process (no network). Its lifespan runs, so the migrations do too."""
    with TestClient(create_app(db_path, allowed_hosts=LOCAL_HOSTS + ('testserver',), env_path=env_path)) as c:
        yield c


@pytest.fixture
def sql(client, db_path):
    """Raw SQL against the same database, to check what the schema itself enforces."""
    engine = make_engine(db_path)

    def run(statement, **params):
        with engine.begin() as conn:
            return conn.execute(text(statement), params)

    yield run
    engine.dispose()


@pytest.fixture
def live_server(db_path):
    """A real server on a free port, for what only a real socket can show (raw paths, streaming)."""
    server = uvicorn.Server(uvicorn.Config(create_app(db_path), host='127.0.0.1', port=0, log_level='warning'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.02)
    assert server.started, 'the test server did not start'
    yield server.servers[0].sockets[0].getsockname()[1], db_path
    server.should_exit = True
    thread.join(5)


# ----- small helpers that create things through the API -----


@pytest.fixture
def make_agency(client):
    def make(name='Acme', **extra):
        r = client.post('/api/agencies', json={'name': name, **extra})
        assert r.status_code == 201, r.text
        return r.json()
    return make


@pytest.fixture
def make_client(client):
    def make(name='Big Client', **extra):
        r = client.post('/api/clients', json={'name': name, **extra})
        assert r.status_code == 201, r.text
        return r.json()
    return make


@pytest.fixture
def make_event(client):
    def make(**fields):
        fields.setdefault('date', '2026-10-08')
        fields.setdefault('event', 'note')
        r = client.post('/api/events', json=fields)
        assert r.status_code == 201, r.text
        return r.json()
    return make
