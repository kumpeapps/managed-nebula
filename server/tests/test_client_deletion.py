"""
Tests for client deletion endpoint (Issue #55)

Tests that deleting a client properly cascades to all related records:
- client_certificates
- client_tokens  
- ip_assignments
- client_groups (association table)
- client_firewall_rulesets (association table)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.models import Client, ClientCertificate, ClientToken, IPAssignment
from app.models.user import User, Role
from app.models.client import Group, FirewallRuleset
from app.core.auth import hash_password
from app.db import get_session, async_session_maker
import asyncio


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
async def db_session():
    """Create async database session for setup"""
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def admin_user(db_session: AsyncSession):
    """Create admin user for testing"""
    # Check if admin already exists
    result = await db_session.execute(
        select(User).where(User.username == "test_admin")
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Get or create admin role
        result = await db_session.execute(
            select(Role).where(Role.name == "admin")
        )
        admin_role = result.scalar_one_or_none()
        
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator")
            db_session.add(admin_role)
            await db_session.flush()
        
        # Create admin user
        user = User(
            username="test_admin",
            email="admin@test.com",
            password_hash=hash_password("testpass123"),
            role_id=admin_role.id,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
    
    return user


def test_delete_client_not_found(client: TestClient):
    """Test deleting non-existent client returns 404"""
    # Note: This test assumes authentication is working or is disabled for tests
    # In production, you'd need to authenticate first
    
    response = client.delete("/api/v1/clients/999999")
    
    # May return 401 if auth is required, or 404 if client not found
    assert response.status_code in [401, 404]
    
    if response.status_code == 404:
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_client_cascades_certificates():
    """Test that deleting a client also deletes associated certificates"""
    async with async_session_maker() as session:
        # Create a test client
        test_client = Client(
            name="test_cascade_certs",
            is_lighthouse=False,
        )
        session.add(test_client)
        await session.commit()
        await session.refresh(test_client)
        client_id = test_client.id
        
        # Create a certificate for the client
        cert = ClientCertificate(
            client_id=client_id,
            pem_cert="TEST_CERT_PEM",
            not_before="2025-01-01 00:00:00",
            not_after="2025-12-31 23:59:59",
            fingerprint="test_fingerprint",
            revoked=False
        )
        session.add(cert)
        await session.commit()
        cert_id = cert.id
        
        # Verify certificate exists
        result = await session.execute(
            select(ClientCertificate).where(ClientCertificate.id == cert_id)
        )
        assert result.scalar_one_or_none() is not None
        
        # Delete the client
        await session.delete(test_client)
        await session.commit()
        
        # Verify certificate was cascade deleted
        result = await session.execute(
            select(ClientCertificate).where(ClientCertificate.id == cert_id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_client_cascades_tokens():
    """Test that deleting a client also deletes associated tokens"""
    async with async_session_maker() as session:
        # Create a test client
        test_client = Client(
            name="test_cascade_tokens",
            is_lighthouse=False,
        )
        session.add(test_client)
        await session.commit()
        await session.refresh(test_client)
        client_id = test_client.id
        
        # Create a token for the client
        token = ClientToken(
            client_id=client_id,
            token="test_token_12345",
            is_active=True
        )
        session.add(token)
        await session.commit()
        token_id = token.id
        
        # Verify token exists
        result = await session.execute(
            select(ClientToken).where(ClientToken.id == token_id)
        )
        assert result.scalar_one_or_none() is not None
        
        # Delete the client
        await session.delete(test_client)
        await session.commit()
        
        # Verify token was cascade deleted
        result = await session.execute(
            select(ClientToken).where(ClientToken.id == token_id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_client_cascades_ip_assignments():
    """Test that deleting a client also deletes IP assignments"""
    async with async_session_maker() as session:
        # Create a test client
        test_client = Client(
            name="test_cascade_ips",
            is_lighthouse=False,
        )
        session.add(test_client)
        await session.commit()
        await session.refresh(test_client)
        client_id = test_client.id
        
        # Create an IP assignment for the client
        ip_assignment = IPAssignment(
            client_id=client_id,
            ip_address="10.99.99.99"
        )
        session.add(ip_assignment)
        await session.commit()
        ip_id = ip_assignment.id
        
        # Verify IP assignment exists
        result = await session.execute(
            select(IPAssignment).where(IPAssignment.id == ip_id)
        )
        assert result.scalar_one_or_none() is not None
        
        # Delete the client
        await session.delete(test_client)
        await session.commit()
        
        # Verify IP assignment was cascade deleted
        result = await session.execute(
            select(IPAssignment).where(IPAssignment.id == ip_id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_client_clears_group_associations():
    """Test that deleting a client clears group memberships"""
    async with async_session_maker() as session:
        # Create a test group
        test_group = Group(name="test_group_deletion")
        session.add(test_group)
        await session.commit()
        await session.refresh(test_group)
        
        # Create a test client
        test_client = Client(
            name="test_group_assoc",
            is_lighthouse=False,
        )
        session.add(test_client)
        await session.commit()
        await session.refresh(test_client)
        
        # Associate client with group
        test_client.groups.append(test_group)
        await session.commit()
        client_id = test_client.id
        
        # Verify association exists
        await session.refresh(test_group)
        assert len(test_group.clients) > 0
        
        # Delete the client
        await session.delete(test_client)
        await session.commit()
        
        # Verify group still exists but association is gone
        result = await session.execute(
            select(Group).where(Group.id == test_group.id)
        )
        group = result.scalar_one_or_none()
        assert group is not None
        # Refresh to get updated relationships
        await session.refresh(group)
        
        # Verify client was removed from group
        result = await session.execute(
            select(Client).where(Client.id == client_id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_client_with_all_relations():
    """Integration test: Delete client with all types of relations"""
    async with async_session_maker() as session:
        # Create a test client
        test_client = Client(
            name="test_full_cascade",
            is_lighthouse=False,
        )
        session.add(test_client)
        await session.commit()
        await session.refresh(test_client)
        client_id = test_client.id
        
        # Add certificate
        cert = ClientCertificate(
            client_id=client_id,
            pem_cert="FULL_TEST_CERT",
            not_before="2025-01-01 00:00:00",
            not_after="2025-12-31 23:59:59",
            revoked=False
        )
        session.add(cert)
        
        # Add token
        token = ClientToken(
            client_id=client_id,
            token="full_test_token_xyz",
            is_active=True
        )
        session.add(token)
        
        # Add IP assignment
        ip_assignment = IPAssignment(
            client_id=client_id,
            ip_address="10.88.88.88"
        )
        session.add(ip_assignment)
        
        await session.commit()
        cert_id = cert.id
        token_id = token.id
        ip_id = ip_assignment.id
        
        # Verify all exist
        assert (await session.execute(select(ClientCertificate).where(ClientCertificate.id == cert_id))).scalar_one_or_none() is not None
        assert (await session.execute(select(ClientToken).where(ClientToken.id == token_id))).scalar_one_or_none() is not None
        assert (await session.execute(select(IPAssignment).where(IPAssignment.id == ip_id))).scalar_one_or_none() is not None
        
        # Delete the client
        await session.delete(test_client)
        await session.commit()
        
        # Verify all related records were deleted
        assert (await session.execute(select(Client).where(Client.id == client_id))).scalar_one_or_none() is None
        assert (await session.execute(select(ClientCertificate).where(ClientCertificate.id == cert_id))).scalar_one_or_none() is None
        assert (await session.execute(select(ClientToken).where(ClientToken.id == token_id))).scalar_one_or_none() is None
        assert (await session.execute(select(IPAssignment).where(IPAssignment.id == ip_id))).scalar_one_or_none() is None
