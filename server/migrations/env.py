"""Alembic environment: reads the models' metadata and runs in batch mode for SQLite."""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import db_path_from_env  # noqa: E402
from app.models import Base  # noqa: E402

config = context.config
if config.config_file_name is not None and config.attributes.get('configure_logger', True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url():
    # `alembic` on the command line has no url set: fall back to the app's own database.
    return config.get_main_option('sqlalchemy.url') or 'sqlite:///%s' % db_path_from_env()


def run_migrations_offline():
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = create_engine(_url())
    with engine.connect() as connection:
        # SQLite can't alter most things in place: batch mode rebuilds the table instead.
        # Foreign keys are switched off while it does, as SQLite recommends.
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
