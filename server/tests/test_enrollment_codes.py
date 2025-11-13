"""Tests for mobile enrollment codes functionality."""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, get_session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine and session
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_session():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_session] = override_get_session
client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
async def setup_database():
    """Create tables before each test and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def admin_user_and_session():
    """Create an admin user and return session cookie."""
    from app.models.user import User, Role
    from app.core.auth import hash_password
    
    async with TestingSessionLocal() as session:
        # Create admin role
        admin_role = Role(name="admin")
        session.add(admin_role)
        await session.flush()
        
        # Create admin user
        admin = User(
            email="admin@test.com",
            hashed_password=hash_password("testpassword"),
            role_id=admin_role.id,
            is_active=True
        )
        session.add(admin)
        await session.commit()
    
    # Login to get session cookie
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpassword"}
    )
    assert response.status_code == 200
    
    # Extract session cookie
    cookies = response.cookies
    return cookies


@pytest.fixture
async def test_client_with_ip(admin_user_and_session):
    """Create a test client with IP assignment."""
    from app.models import Client, IPPool, IPAssignment, CACertificate, GlobalSettings
    
    async with TestingSessionLocal() as session:
        # Create global settings
        settings = GlobalSettings(
            default_cidr_pool="10.100.0.0/16",
            lighthouse_port=4242,
            server_url="http://localhost:8080"
        )
        session.add(settings)
        
        # Create IP pool
        pool = IPPool(cidr="10.100.0.0/16", description="Test pool")
        session.add(pool)
        await session.flush()
        
        # Create CA certificate
        ca = CACertificate(
            name="Test CA",
            pem_cert=b"-----BEGIN NEBULA CERTIFICATE-----\ntest\n-----END NEBULA CERTIFICATE-----",
            pem_key=b"-----BEGIN NEBULA KEY-----\ntest\n-----END NEBULA KEY-----",
            not_before=datetime.utcnow(),
            not_after=datetime.utcnow() + timedelta(days=365),
            is_active=True,
            is_previous=False,
            can_sign=True,
            include_in_config=True,
            created_at=datetime.utcnow()
        )
        session.add(ca)
        
        # Create test client
        test_client = Client(
            name="test-mobile-client",
            is_lighthouse=False,
            is_blocked=False,
            created_at=datetime.utcnow()
        )
        session.add(test_client)
        await session.flush()
        
        # Create IP assignment
        ip_assignment = IPAssignment(
            client_id=test_client.id,
            ip_address="10.100.0.100",
            pool_id=pool.id
        )
        session.add(ip_assignment)
        await session.commit()
        
        return test_client.id
    
    return None


@pytest.mark.asyncio
async def test_create_enrollment_code(admin_user_and_session, test_client_with_ip):
    """Test creating an enrollment code."""
    cookies = await admin_user_and_session
    client_id = await test_client_with_ip
    
    response = client.post(
        "/api/v1/enrollment/codes",
        json={
            "client_id": client_id,
            "validity_hours": 24,
            "device_name": "Test iPhone"
        },
        cookies=cookies
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "code" in data
    assert data["client_id"] == client_id
    assert data["client_name"] == "test-mobile-client"
    assert data["device_name"] == "Test iPhone"
    assert data["is_used"] is False
    assert "enrollment_url" in data
    assert "/enroll?code=" in data["enrollment_url"]


@pytest.mark.asyncio
async def test_create_enrollment_code_invalid_validity(admin_user_and_session, test_client_with_ip):
    """Test creating enrollment code with invalid validity hours."""
    cookies = await admin_user_and_session
    client_id = await test_client_with_ip
    
    # Test validity too short (< 1 hour)
    response = client.post(
        "/api/v1/enrollment/codes",
        json={
            "client_id": client_id,
            "validity_hours": 0
        },
        cookies=cookies
    )
    assert response.status_code == 400
    
    # Test validity too long (> 168 hours = 7 days)
    response = client.post(
        "/api/v1/enrollment/codes",
        json={
            "client_id": client_id,
            "validity_hours": 200
        },
        cookies=cookies
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_enrollment_codes(admin_user_and_session, test_client_with_ip):
    """Test listing enrollment codes."""
    cookies = await admin_user_and_session
    client_id = await test_client_with_ip
    
    # Create two enrollment codes
    client.post(
        "/api/v1/enrollment/codes",
        json={"client_id": client_id, "validity_hours": 24},
        cookies=cookies
    )
    client.post(
        "/api/v1/enrollment/codes",
        json={"client_id": client_id, "validity_hours": 48},
        cookies=cookies
    )
    
    # List codes
    response = client.get("/api/v1/enrollment/codes", cookies=cookies)
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    assert all(code["client_id"] == client_id for code in data)


@pytest.mark.asyncio
async def test_delete_unused_enrollment_code(admin_user_and_session, test_client_with_ip):
    """Test deleting an unused enrollment code."""
    cookies = await admin_user_and_session
    client_id = await test_client_with_ip
    
    # Create enrollment code
    create_response = client.post(
        "/api/v1/enrollment/codes",
        json={"client_id": client_id, "validity_hours": 24},
        cookies=cookies
    )
    code_id = create_response.json()["id"]
    
    # Delete the code
    delete_response = client.delete(
        f"/api/v1/enrollment/codes/{code_id}",
        cookies=cookies
    )
    assert delete_response.status_code == 200
    
    # Verify it's deleted
    list_response = client.get("/api/v1/enrollment/codes", cookies=cookies)
    data = list_response.json()
    assert len(data) == 0


@pytest.mark.asyncio  
async def test_cannot_delete_used_enrollment_code(admin_user_and_session, test_client_with_ip):
    """Test that used enrollment codes cannot be deleted."""
    from app.models.client import EnrollmentCode
    
    cookies = await admin_user_and_session
    client_id = await test_client_with_ip
    
    # Create and mark code as used directly in database
    async with TestingSessionLocal() as session:
        code = EnrollmentCode(
            code="test-used-code",
            client_id=client_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=True,
            used_at=datetime.utcnow()
        )
        session.add(code)
        await session.commit()
        code_id = code.id
    
    # Try to delete
    response = client.delete(
        f"/api/v1/enrollment/codes/{code_id}",
        cookies=cookies
    )
    assert response.status_code == 409
    assert "used" in response.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
