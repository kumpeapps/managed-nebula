from __future__ import with_statement
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import Base
from app.core.config import settings
# Import all models so they are registered with Base.metadata
from app.models import (
    User,
    Client, ClientToken, ClientCertificate, Group, FirewallRule, FirewallRuleset,
    IPPool, IPAssignment, IPGroup,
    CACertificate,
    GlobalSettings,
    ClientPermission, GroupPermission, UserGroup, UserGroupMembership
)


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    # Convert async URLs to sync for Alembic
    url = settings.db_url
    if "+aiosqlite" in url:
        url = url.replace("+aiosqlite", "")
    elif "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg2")
    elif "+aiomysql" in url:
        url = url.replace("+aiomysql", "+pymysql")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    ini_config = config.get_section(config.config_ini_section)
    
    # Convert async URLs to sync for Alembic
    url = settings.db_url
    if "+aiosqlite" in url:
        url = url.replace("+aiosqlite", "")
    elif "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg2")
    elif "+aiomysql" in url:
        url = url.replace("+aiomysql", "+pymysql")
    
    ini_config["sqlalchemy.url"] = url
    connectable = engine_from_config(
        ini_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
