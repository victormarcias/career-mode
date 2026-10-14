"""Engine, sessions and migrations."""
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

SERVER_DIR = Path(__file__).resolve().parent.parent
ROOT = SERVER_DIR.parent
DEFAULT_DB_PATH = ROOT / 'data' / 'career-mode.db'


def db_path_from_env() -> Path:
    from .settings import load_env_file  # imported here: settings itself imports ROOT from this module

    load_env_file()
    path = Path(os.environ.get('CAREER_MODE_DB') or DEFAULT_DB_PATH)
    return path if path.is_absolute() else ROOT / path


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


def alembic_config(db_path=None) -> Config:
    """The same Alembic setup the `alembic` command line uses, pointed at a given file."""
    config = Config(str(SERVER_DIR / 'alembic.ini'))
    config.set_main_option('script_location', str(SERVER_DIR / 'migrations'))
    config.set_main_option('sqlalchemy.url', 'sqlite:///%s' % (db_path or db_path_from_env()))
    config.attributes['configure_logger'] = False  # don't reconfigure the app's own logging
    return config


def migrate(db_path=None):
    """Brings the database up to the latest schema. Safe to run on every start."""
    # A fresh clone has no data/ folder (git ignores it) and SQLite won't create it.
    Path(db_path or db_path_from_env()).parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(alembic_config(db_path), 'head')


def session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)
