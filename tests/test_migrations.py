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
    assert {'agencies', 'agency_recruiters', 'clients', 'events', 'alembic_version'} <= tables(path)


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
    migrate(path)
    conn = two_companies(path)
    conn.execute("INSERT INTO events (id, date, type, client_id) VALUES ('p1', '2026-10-02', 'passive_message', 'big')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO events (id, date, type) VALUES ('p2', '2026-10-02', 'passive_message')")
    conn.close()


def test_going_down_turns_the_passive_messages_with_no_agency_into_notes(path):
    migrate(path)
    conn = two_companies(path)
    conn.execute("INSERT INTO events (id, date, type, client_id) VALUES ('p1', '2026-10-02', 'passive_message', 'big')")
    conn.execute("INSERT INTO events (id, date, type, agency_id) VALUES ('p2', '2026-10-02', 'passive_message', 'acme')")
    conn.commit()
    conn.close()
    command.downgrade(alembic_config(path), '0002')
    assert events_of(path) == {'p1': ('note', ''), 'p2': ('passive_message', '')}
