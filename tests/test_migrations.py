"""Alembic: the migrations build exactly the schema the models describe."""
import sqlite3

import pytest
from alembic import command
from alembic.script import ScriptDirectory

from app.database import alembic_config, migrate


@pytest.fixture
def path(tmp_path):
    return tmp_path / 'migrations.db'


def tables(path):
    conn = sqlite3.connect(path)
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    finally:
        conn.close()


def test_upgrade_creates_the_tables(path):
    migrate(path)
    assert {'companies', 'company_recruiters', 'events', 'alembic_version'} <= tables(path)
    assert not {'agencies', 'agency_recruiters', 'clients'} & tables(path)


def test_upgrading_twice_is_harmless(path):
    migrate(path)
    migrate(path)


def test_there_is_a_single_line_of_history():
    assert len(ScriptDirectory.from_config(alembic_config()).get_heads()) == 1


def test_the_migrations_match_the_models(path):
    """If you changed a model and forgot `alembic revision --autogenerate`, this fails."""
    migrate(path)
    command.check(alembic_config(path))  # raises when the models and the migrated database differ


def test_downgrade_empties_the_database(path):
    migrate(path)
    command.downgrade(alembic_config(path), 'base')
    assert tables(path) == {'alembic_version'}


# ---------- 0002: the AI interview and Video task types are gone ----------


def old_database(path):
    """A database as the first migration left it, with one event of each kind that is about to disappear."""
    command.upgrade(alembic_config(path), '0001')
    conn = sqlite3.connect(path)
    rows = [
        ('ai1', 'ai_interview', 'Round with the bot'), ('ai2', 'ai_interview', ''),
        ('vt1', 'video_task', 'Record 2 minutes'), ('n1', 'note', 'a plain note'), ('h1', 'hr_intro', 'kept as it is'),
    ]
    for id_, type_, notes in rows:
        conn.execute("INSERT INTO events (id, date, type, notes) VALUES (?, '2026-10-01', ?, ?)", (id_, type_, notes))
    conn.commit()
    conn.close()


def events_of(path):
    conn = sqlite3.connect(path)
    try:
        return {r[0]: (r[1], r[2]) for r in conn.execute('SELECT id, type, notes FROM events')}
    finally:
        conn.close()


def test_the_removed_types_become_notes_that_remember_their_old_name(path):
    old_database(path)
    migrate(path)
    assert events_of(path) == {
        'ai1': ('note', 'AI interview: Round with the bot'), 'ai2': ('note', 'AI interview'),
        'vt1': ('note', 'Video task: Record 2 minutes'), 'n1': ('note', 'a plain note'), 'h1': ('hr_intro', 'kept as it is'),
    }


def test_after_it_the_database_refuses_the_removed_types(path):
    old_database(path)
    migrate(path)
    conn = sqlite3.connect(path)
    for type_ in ('ai_interview', 'video_task'):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO events (id, date, type) VALUES ('x', '2026-10-02', ?)", (type_,))
    conn.execute("INSERT INTO events (id, date, type) VALUES ('ok', '2026-10-02', 'culture_interview')")  # the others still go in
    conn.close()


def test_the_data_survives_the_whole_way_down_and_up_again(path):
    old_database(path)
    migrate(path)
    command.downgrade(alembic_config(path), '0001')
    assert events_of(path)['ai1'][0] == 'note'  # what became a note stays a note
    migrate(path)
    assert len(events_of(path)) == 5


# ---------- 0003: a passive message needs an agency or a client ----------


def two_companies(path):
    conn = sqlite3.connect(path)
    conn.execute("INSERT INTO agencies (id, name) VALUES ('acme', 'Acme')")
    conn.execute("INSERT INTO clients (id, name) VALUES ('big', 'Big')")
    conn.commit()
    return conn


def test_after_it_a_passive_message_may_have_only_a_client(path):
    command.upgrade(alembic_config(path), '0003')
    conn = two_companies(path)
    conn.execute("INSERT INTO events (id, date, type, client_id) VALUES ('p1', '2026-10-02', 'passive_message', 'big')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO events (id, date, type) VALUES ('p2', '2026-10-02', 'passive_message')")
    conn.close()


def test_going_down_turns_the_passive_messages_with_no_agency_into_notes(path):
    command.upgrade(alembic_config(path), '0003')
    conn = two_companies(path)
    conn.execute("INSERT INTO events (id, date, type, client_id) VALUES ('p1', '2026-10-02', 'passive_message', 'big')")
    conn.execute("INSERT INTO events (id, date, type, agency_id) VALUES ('p2', '2026-10-02', 'passive_message', 'acme')")
    conn.commit()
    conn.close()
    command.downgrade(alembic_config(path), '0002')
    assert events_of(path) == {'p1': ('note', ''), 'p2': ('passive_message', '')}


# ---------- 0004: agencies and clients become companies ----------


def old_companies(path):
    """A database as 0003 left it: an agency with a client and a recruiter, a client that shares the agency's id and name, and
    one event of each kind (the agency's, the agency and a client's, a client's alone, and none)."""
    command.upgrade(alembic_config(path), '0003')
    conn = sqlite3.connect(path)
    conn.executescript("""
        INSERT INTO agencies (id, name, type, website, status) VALUES ('acme', 'Acme', 'staffing', 'https://acme.example', 'archived');
        INSERT INTO agency_recruiters VALUES ('acme', 0, 'https://linkedin.com/in/ana');
        INSERT INTO agencies (id, name) VALUES ('other', 'Other');
        INSERT INTO clients (id, name, notes, via_agency_id) VALUES ('big', 'Big', 'a client', 'acme');
        INSERT INTO clients (id, name) VALUES ('acme', 'ACME');
        INSERT INTO events (id, date, type, agency_id) VALUES ('e1', '2026-10-01', 'note', 'acme');
        INSERT INTO events (id, date, type, agency_id, client_id) VALUES ('e2', '2026-10-02', 'rejection', 'acme', 'big');
        INSERT INTO events (id, date, type, client_id) VALUES ('e3', '2026-10-03', 'passive_message', 'acme');
        INSERT INTO events (id, date, type) VALUES ('e4', '2026-10-04', 'note');
    """)
    conn.commit()
    conn.close()


def rows(path, query):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(query).fetchall()
    finally:
        conn.close()


def test_the_agencies_and_the_clients_become_companies(path):
    old_companies(path)
    migrate(path)
    assert tables(path) >= {'companies', 'company_recruiters', 'events'}
    assert not {'agencies', 'clients', 'agency_recruiters'} & tables(path)
    assert rows(path, 'SELECT id, name, company_type, notes, website, via_company_id FROM companies ORDER BY id') == [
        ('acme', 'Acme', 'agency', 'staffing', 'https://acme.example', None),
        ('acme-2', 'ACME (client)', 'client', '', None, None),  # the client with the agency's id and name had to change
        ('big', 'Big', 'client', 'a client', None, 'acme'),
        ('other', 'Other', 'agency', '', None, None),
    ]
    assert rows(path, 'SELECT company_id, position, url FROM company_recruiters') == [('acme', 0, 'https://linkedin.com/in/ana')]


def test_the_events_follow_their_companies(path):
    old_companies(path)
    migrate(path)
    assert rows(path, 'SELECT id, company_id, via_company_id FROM events ORDER BY id') == [
        ('e1', 'acme', None),        # an agency's event
        ('e2', 'big', 'acme'),       # a client's, with the agency it came through
        ('e3', 'acme-2', None),      # a client's alone, following the client's new id
        ('e4', None, None),
    ]


def test_after_it_the_database_refuses_what_the_old_one_allowed(path):
    old_companies(path)
    migrate(path)
    conn = sqlite3.connect(path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO companies (id, name, company_type) VALUES ('x', 'acme', 'client')")  # a name twice
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO events (id, date, type) VALUES ('p', '2026-10-05', 'passive_message')")  # no company
    conn.close()


def test_going_back_to_agencies_and_clients_keeps_the_data_and_derives_the_status(path):
    old_companies(path)
    migrate(path)
    command.downgrade(alembic_config(path), '0003')
    assert tables(path) >= {'agencies', 'clients', 'agency_recruiters', 'events'}
    assert 'companies' not in tables(path)
    # Acme's latest event is the rejection of its client Big, so it is archived; Other has none
    assert rows(path, 'SELECT id, type, status FROM agencies ORDER BY id') == [('acme', 'staffing', 'archived'), ('other', '', 'active')]
    assert rows(path, 'SELECT id, notes, via_agency_id FROM clients ORDER BY id') == [('acme-2', '', None), ('big', 'a client', 'acme')]
    assert rows(path, 'SELECT id, agency_id, client_id FROM events ORDER BY id') == [
        ('e1', 'acme', None), ('e2', 'acme', 'big'), ('e3', None, 'acme-2'), ('e4', None, None)]
    assert rows(path, 'SELECT agency_id, url FROM agency_recruiters') == [('acme', 'https://linkedin.com/in/ana')]
    migrate(path)  # and up again
    assert rows(path, 'SELECT COUNT(*) FROM companies') == [(4,)]
