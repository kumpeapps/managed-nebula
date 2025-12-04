from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, event
from .core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.db_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800,
)

# Ensure foreign key enforcement for every SQLite connection (needed for cascades).
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):  # pragma: no cover
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        # Non-critical: ignore if not SQLite or fails
        pass
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class _SessionContextManager:
    """Context manager returned by async_session_maker() to ensure models exist.

    Tests use `async with async_session_maker() as session:` directly, bypassing
    `get_session()`. This wrapper guarantees `_ensure_models()` runs before the
    session is created so tables are present for direct test usage.
    """
    def __init__(self):
        self._session: AsyncSession | None = None

    async def __aenter__(self):
        await _ensure_models()
        self._session = AsyncSessionLocal()
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        # Close session if it was created
        if self._session is not None:
            await self._session.close()

def async_session_maker():
    return _SessionContextManager()

async def _ensure_models():
    import os
    async with engine.begin() as conn:
        # Ensure SQLite enforces foreign key constraints (only for SQLite)
        if engine.dialect.name == 'sqlite':
            await conn.run_sync(lambda connection: connection.execute(text("PRAGMA foreign_keys=ON")))
        # NOTE: Dropping tables on every session breaks test fixtures that need persistent test data
        # Disabled for now - tests should handle their own cleanup if needed
        # if "PYTEST_CURRENT_TEST" in os.environ:
        #     # In test context, reset schema each session to ensure isolation
        #     await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    await _ensure_models()
    async with AsyncSessionLocal() as session:
        yield session
