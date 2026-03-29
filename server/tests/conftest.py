"""Pytest configuration for test suite."""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, select
from app.db import engine, Base, AsyncSessionLocal
from app.main import app
from app.models.user import User, Role
from app.core.auth import hash_password


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
    from app.models.client import Client, Group, FirewallRuleset, IPPool, ClientToken, ClientCertificate, RevokedCertificate
    from app.models.ca import CACertificate
    from app.models.api_key import UserAPIKey

    return [
        ClientToken,
        UserAPIKey,
        ClientCertificate,
        RevokedCertificate,
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


@pytest.fixture
async def async_client():
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def async_session():
    """Create an async database session for testing."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def admin_user():
    """Create or get admin user for testing with admin group membership."""
    async with AsyncSessionLocal() as session:
        from app.models.permissions import UserGroup, UserGroupMembership
        
        # Check if admin user exists
        result = await session.execute(
            select(User).where(User.email == "test_admin@test.com")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create admin user
            user = User(
                email="test_admin@test.com",
                hashed_password=hash_password("testpass123"),
                is_active=True
            )
            session.add(user)
            await session.flush()
            
            # Get or create admin group
            group_result = await session.execute(
                select(UserGroup).where(UserGroup.name == "Administrators")
            )
            admin_group = group_result.scalar_one_or_none()
            
            if not admin_group:
                admin_group = UserGroup(
                    name="Administrators",
                    is_admin=True
                )
                session.add(admin_group)
                await session.flush()
            
            # Add user to admin group
            membership = UserGroupMembership(
                user_id=user.id,
                user_group_id=admin_group.id
            )
            session.add(membership)
            
            await session.commit()
            await session.refresh(user)
        
        return user


@pytest.fixture
async def auth_headers(async_client: AsyncClient, admin_user: User):
    """Get authentication headers/cookies for admin user."""
    # Login to get session cookie
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "test_admin@test.com",
            "password": "testpass123"
        }
    )
    
    assert response.status_code == 200, f"Login failed: {response.text}"
    
    # Return cookies from the response
    return {
        "cookies": response.cookies
    }
