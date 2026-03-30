"""Alembic environment — resolves DATABASE_URL from app runtime settings."""

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Ensure the project root is on sys.path so app.config is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import get_settings  # noqa: E402
from app.models import (  # noqa: F401, E402
    Base,  # noqa: E402
    observation,
    prediction,
    roi,
    spectral,
)

# Alembic Config object — provides access to the .ini file values.
config = context.config

# Apply logging configuration from alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the connection URL from runtime settings (never hardcoded).
_settings = get_settings()
config.set_main_option("sqlalchemy.url", _settings.DATABASE_URL)

# Use ORM metadata for migration autogeneration.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode (no live DB connection required)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in online mode (requires live DB connection)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
