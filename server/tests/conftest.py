"""Pytest configuration for test suite."""
import pytest
import asyncio
from sqlalchemy import text
from app.db import engine, Base


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(event_loop):
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
    
    event_loop.run_until_complete(reset_db())
    yield


@pytest.fixture(scope="function", autouse=True)
def clear_test_data_between_tests():
    """Clear all test data between tests to ensure isolation."""
    # Data is cleared AFTER each test to avoid interference
    yield
    
    async def cleanup():
        from app.db import AsyncSessionLocal
        from sqlalchemy import delete
        from app.models.client import Client, Group, FirewallRuleset, IPPool, ClientToken
        from app.models.ca import CACertificate
        from app.models.user import User
        from app.models.permissions import UserGroup
        
        async with AsyncSessionLocal() as session:
            # Delete in reverse dependency order
            await session.execute(delete(ClientToken))
            await session.execute(delete(Client))
            await session.execute(delete(Group))
            await session.execute(delete(FirewallRuleset))
            await session.execute(delete(IPPool))
            await session.execute(delete(CACertificate))
            # Keep users and permissions for next test
            await session.commit()
    
    asyncio.run(cleanup())
