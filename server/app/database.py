"""Engine, sessions and the schema."""
from pathlib import Path

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker

from .models import Base

SERVER_DIR = Path(__file__).resolve().parent.parent
ROOT = SERVER_DIR.parent
DEFAULT_DB_PATH = ROOT / 'data' / 'career-mode.db'  # always this file: it is not a setting


def make_engine(db_path):
    """A SQLite engine that enforces foreign keys (SQLite ignores them unless asked, per connection)."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine('sqlite:///%s' % db_path, connect_args={'check_same_thread': False})

    @event.listens_for(engine, 'connect')
    def _on_connect(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys = ON')
        cursor.execute('PRAGMA journal_mode = WAL')  # readers don't block the writer
        cursor.close()

    return engine


def create_schema(db_path=None):
    """Creates the tables that are missing. Safe to run on every start.

    There are no migrations: the database always has the latest schema. When a model changes, an
    existing file keeps the old one, so this refuses to start and says how to rebuild it
    (export the backup, delete the file, start again, import the backup; see CLAUDE.md).
    """
    engine = make_engine(db_path or DEFAULT_DB_PATH)  # also makes the data/ folder a fresh clone doesn't have
    try:
        Base.metadata.create_all(engine)
        existing = inspect(engine)
        stale = []
        for table in Base.metadata.sorted_tables:
            have = {c['name'] for c in existing.get_columns(table.name)}
            stale += ['%s.%s' % (table.name, c.name) for c in table.columns if c.name not in have]
        if stale:
            raise RuntimeError(
                'The database is out of date (missing: %s). Rebuild it: export the backup, delete the '
                'database file, start the server again and import the backup.' % ', '.join(stale)
            )
    finally:
        engine.dispose()


def session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)
