from __future__ import annotations

import logging
from typing import Iterable
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.schema import CreateIndex
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


async def create_missing_tables(engine: AsyncEngine, Base: type[DeclarativeBase]) -> None:
    """Create all mapped tables that don't exist yet (non-destructive).
    Uses SQLAlchemy metadata.create_all via a sync run on the async engine.
    """
    logger.info("Creating missing tables from metadata...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Table creation complete")


async def add_missing_columns(engine: AsyncEngine, table_columns: dict[str, dict[str, str]]) -> None:
    """Add missing columns per-table using raw ALTER TABLE ADD COLUMN statements.
    table_columns: { table_name: { column_name: ddl_fragment } }
    DDL fragments should be vendor-neutral where possible (VARCHAR, INTEGER, BOOLEAN, DATETIME).
    """
    async with engine.begin() as conn:
        def _get_existing_columns(sync_conn, table: str) -> set[str]:
            insp = inspect(sync_conn)
            try:
                cols = insp.get_columns(table)
            except Exception:
                # table not present; skip - create_missing_tables should handle creation
                return set()
            return {c["name"] for c in cols}

        for table, cols in table_columns.items():
            existing = await conn.run_sync(_get_existing_columns, table)
            for col, ddl in cols.items():
                if col not in existing:
                    logger.info(f"Adding column {table}.{col}")
                    await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))


async def ensure_indexes(engine: AsyncEngine, index_statements: Iterable[str]) -> None:
    """Create indexes if they do not exist. Provide vendor-compatible statements.
    Note: MySQL and SQLite differ on IF NOT EXISTS support for CREATE INDEX.
    We'll try IF NOT EXISTS and fallback silently on error.
    """
    async with engine.begin() as conn:
        for stmt in index_statements:
            try:
                logger.info(f"Ensuring index: {stmt[:60]}...")
                await conn.execute(text(stmt))
            except Exception as e:
                # best-effort; skip if backend doesn't support IF NOT EXISTS
                logger.debug(f"Index creation skipped or failed: {e}")


async def sync_schema(engine: AsyncEngine, Base: type[DeclarativeBase]) -> None:
    """Best-effort schema synchronization at startup.
    - Creates all mapped tables that don't exist
    - Adds missing additive columns on known tables
    - Creates key indexes if missing
    This is intentionally conservative: no drops, no type/nullable changes.
    """
    await create_missing_tables(engine, Base)

    # Columns we know we may add over time
    columns = {
        "clients": {
            "last_config_download_at": "DATETIME",
            "config_last_changed_at": "DATETIME",
            "is_blocked": "BOOLEAN DEFAULT 0 NOT NULL",
            "blocked_at": "DATETIME",
            "owner_user_id": "INTEGER",
        },
        "client_certificates": {
            "fingerprint": "VARCHAR(128)",
            "issued_for_ip_cidr": "VARCHAR(64)",
            "issued_for_groups_hash": "VARCHAR(64)",
            "revoked": "BOOLEAN DEFAULT 0 NOT NULL",
            "revoked_at": "DATETIME",
        },
        "client_tokens": {
            "owner_user_id": "INTEGER",
        },
        "ca_certificates": {
            "can_sign": "BOOLEAN DEFAULT 1 NOT NULL",
            "include_in_config": "BOOLEAN DEFAULT 1 NOT NULL",
        },
        "ip_assignments": {
            "ip_group_id": "INTEGER",
        },
    }
    await add_missing_columns(engine, columns)

    # Tables that might be introduced later (create if not exists)
    # Note: base create_missing_tables handles mapped tables; these are auxiliary tables
    # that aren't mapped directly or appeared before mapping existed mid-dev.
    aux_tables_sql = {
        "ip_groups": "(id INTEGER PRIMARY KEY, pool_id INTEGER NOT NULL, name VARCHAR(100) NOT NULL, start_ip VARCHAR(64) NOT NULL, end_ip VARCHAR(64) NOT NULL)",
        "client_access": "(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, client_id INTEGER NOT NULL)",
        "owner_access_all": "(id INTEGER PRIMARY KEY, owner_user_id INTEGER NOT NULL, user_id INTEGER NOT NULL)",
        "user_group_assignments": "(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, group_id INTEGER NOT NULL)",
        "ip_group_group_assignments": "(id INTEGER PRIMARY KEY, ip_group_id INTEGER NOT NULL, group_id INTEGER NOT NULL)",
    }
    async with engine.begin() as conn:
        for name, sql in aux_tables_sql.items():
            logger.info(f"Ensuring auxiliary table exists: {name}")
            await conn.execute(text(f"CREATE TABLE IF NOT EXISTS {name} {sql}"))

    # Best-effort indexes (SQLite supports IF NOT EXISTS since 3.8.0; MySQL 8 supports it)
    await ensure_indexes(
        engine,
        [
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_roles_name ON roles(name)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_groups_name ON groups(name)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_client_tokens_token ON client_tokens(token)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_ip_pools_cidr ON ip_pools(cidr)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_ip_assignments_ip_address ON ip_assignments(ip_address)",
        ],
    )
