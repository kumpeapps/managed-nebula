"""Pytest configuration for test suite."""
import pytest
import asyncio
from sqlalchemy import text
from app.db import engine, Base


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Drop and recreate all tables once at the start of the test session."""
    async def reset_db():
        async with engine.begin() as conn:
            # Enable foreign keys for SQLite
            if engine.dialect.name == 'sqlite':
                await conn.run_sync(lambda connection: connection.execute(text("PRAGMA foreign_keys=ON")))
            # Drop all existing tables
            await conn.run_sync(Base.metadata.drop_all)
            # Create fresh tables
            await conn.run_sync(Base.metadata.create_all)
    
    asyncio.run(reset_db())
    yield


def _models_to_clear_for_test_cleanup():
    """
    Central definition of models whose data is cleared between tests.

    We intentionally *do not* include auth/user/permission reference data here
    (e.g. User, Permission, Role, UserGroup, UserGroupMembership) so that 
    authentication/authorization fixtures can rely on a stable baseline of seeded 
    data across tests.

    When adding new domain tables that should be cleaned between tests, add the
    corresponding model classes to this list instead of updating fixtures in
    multiple places.
    """
    from app.models.client import Client, Group, FirewallRuleset, IPPool, ClientToken
    from app.models.ca import CACertificate

    return [
        ClientToken,
        Client,
        Group,
        FirewallRuleset,
        IPPool,
        CACertificate,
    ]


@pytest.fixture(scope="function", autouse=True)
def clear_test_data_between_tests():
    """Clear all (non-reference) test data between tests to ensure isolation.

    Data is cleared AFTER each test to avoid interference with the running test.
    Reference data (users, permissions) is preserved as defined in 
    _models_to_clear_for_test_cleanup().
    """
    # Let the test run first
    yield

    async def cleanup():
        from app.db import AsyncSessionLocal
        from sqlalchemy import delete

        async with AsyncSessionLocal() as session:
            # Delete rows from all configured models; reference data is excluded
            # by design in `_models_to_clear_for_test_cleanup`.
            for model in _models_to_clear_for_test_cleanup():
                await session.execute(delete(model))
            await session.commit()

    asyncio.run(cleanup())
