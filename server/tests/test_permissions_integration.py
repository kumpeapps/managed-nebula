"""Integration tests for the comprehensive permission system.

These tests use the actual database created by the migration system
and test the API endpoints with real HTTP requests.
"""
import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def test_db_file():
    """Create a temporary database file for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # Set environment variable for test database
    os.environ["DB_URL"] = f"sqlite+aiosqlite:///{path}"
    
    yield path
    
    # Clean up
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture(scope="module")
def client(test_db_file):
    """Create test client and run migrations."""
    # Run Alembic migrations to create and seed database
    # This will create tables with the correct schema including all migrations
    import subprocess
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd="/home/runner/work/managed-nebula/managed-nebula/server",
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Migration failed: {result.stderr}")
        raise RuntimeError(f"Failed to run migrations: {result.stderr}")
    
    return TestClient(app)


@pytest.fixture(scope="module")
def admin_session(client, test_db_file):
    """Create and login as admin user."""
    import asyncio
    import os
    
    # Re-import with correct DB_URL
    os.environ["DB_URL"] = f"sqlite+aiosqlite:///{test_db_file}"
    from app.db import AsyncSessionLocal
    from app.models.user import User, Role
    from app.core.auth import hash_password
    
    async def create_admin():
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            
            # Check if admin role exists
            result = await session.execute(select(Role).where(Role.name == "admin"))
            admin_role = result.scalar_one_or_none()
            
            if not admin_role:
                admin_role = Role(name="admin")
                session.add(admin_role)
                await session.commit()
                await session.refresh(admin_role)
            
            # Check if admin user exists
            result = await session.execute(select(User).where(User.email == "test_admin@test.com"))
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                admin_user = User(
                    email="test_admin@test.com",
                    hashed_password=hash_password("admin123"),
                    role_id=admin_role.id,
                    is_active=True
                )
                session.add(admin_user)
                await session.commit()
                
                # Add to Administrators group
                from app.models.permissions import UserGroup, UserGroupMembership
                result = await session.execute(select(UserGroup).where(UserGroup.name == "Administrators"))
                admin_group = result.scalar_one_or_none()
                
                if admin_group:
                    membership = UserGroupMembership(
                        user_id=admin_user.id,
                        user_group_id=admin_group.id
                    )
                    session.add(membership)
                    await session.commit()
    
    asyncio.run(create_admin())
    
    # Login
    response = client.post("/api/v1/auth/login", json={
        "email": "test_admin@test.com",
        "password": "admin123"
    })
    
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return client


def test_list_permissions(admin_session):
    """Test listing all permissions."""
    response = admin_session.get("/api/v1/permissions")
    assert response.status_code == 200
    
    permissions = response.json()
    assert isinstance(permissions, list)
    assert len(permissions) > 0
    
    # Check structure
    perm = permissions[0]
    assert "id" in perm
    assert "resource" in perm
    assert "action" in perm
    assert "description" in perm
    
    # Check that default permissions exist
    resources = {p["resource"] for p in permissions}
    assert "clients" in resources
    assert "users" in resources
    assert "groups" in resources


def test_list_user_groups(admin_session):
    """Test listing user groups."""
    response = admin_session.get("/api/v1/user-groups")
    assert response.status_code == 200
    
    groups = response.json()
    assert isinstance(groups, list)
    assert len(groups) >= 2  # At least Administrators and Users
    
    # Find Administrators group
    admin_group = next((g for g in groups if g["name"] == "Administrators"), None)
    assert admin_group is not None
    assert admin_group["is_admin"] is True
    
    # Find Users group
    users_group = next((g for g in groups if g["name"] == "Users"), None)
    assert users_group is not None
    assert users_group["is_admin"] is False


def test_create_user_group(admin_session):
    """Test creating a new user group."""
    response = admin_session.post("/api/v1/user-groups", json={
        "name": "Test Developers",
        "description": "Test development team",
        "is_admin": False
    })
    
    assert response.status_code == 200
    group = response.json()
    assert group["name"] == "Test Developers"
    assert group["is_admin"] is False
    assert group["member_count"] == 0
    assert group["permission_count"] == 0


def test_cannot_delete_administrators_group(admin_session):
    """Test that Administrators group cannot be deleted."""
    # Get Administrators group
    response = admin_session.get("/api/v1/user-groups")
    groups = response.json()
    admin_group = next((g for g in groups if g["name"] == "Administrators"), None)
    assert admin_group is not None
    
    # Try to delete it
    response = admin_session.delete(f"/api/v1/user-groups/{admin_group['id']}")
    assert response.status_code == 409
    assert "Cannot delete" in response.json()["detail"]


def test_update_user_group(admin_session):
    """Test updating a user group."""
    # Create a group first
    response = admin_session.post("/api/v1/user-groups", json={
        "name": "Test Update Group",
        "description": "Original description",
        "is_admin": False
    })
    assert response.status_code == 200
    group_id = response.json()["id"]
    
    # Update it
    response = admin_session.put(f"/api/v1/user-groups/{group_id}", json={
        "description": "Updated description"
    })
    assert response.status_code == 200
    
    updated_group = response.json()
    assert updated_group["description"] == "Updated description"


def test_cannot_remove_admin_status_from_administrators(admin_session):
    """Test that admin status cannot be removed from Administrators group."""
    # Get Administrators group
    response = admin_session.get("/api/v1/user-groups")
    groups = response.json()
    admin_group = next((g for g in groups if g["name"] == "Administrators"), None)
    
    # Try to remove admin status
    response = admin_session.put(f"/api/v1/user-groups/{admin_group['id']}", json={
        "is_admin": False
    })
    assert response.status_code == 409
    assert "Cannot remove admin status" in response.json()["detail"]


def test_grant_permission_to_group(admin_session):
    """Test granting a permission to a group."""
    # Create a group
    response = admin_session.post("/api/v1/user-groups", json={
        "name": "Test Permission Group",
        "description": "Test group for permissions",
        "is_admin": False
    })
    assert response.status_code == 200
    group_id = response.json()["id"]
    
    # Grant a permission
    response = admin_session.post(
        f"/api/v1/user-groups/{group_id}/permissions",
        json={"resource": "clients", "action": "read"}
    )
    assert response.status_code == 200
    
    # Verify permission was granted
    response = admin_session.get(f"/api/v1/user-groups/{group_id}/permissions")
    assert response.status_code == 200
    permissions = response.json()
    assert any(p["resource"] == "clients" and p["action"] == "read" for p in permissions)


def test_revoke_permission_from_group(admin_session):
    """Test revoking a permission from a group."""
    # Create a group with a permission
    response = admin_session.post("/api/v1/user-groups", json={
        "name": "Test Revoke Group",
        "description": "Test group",
        "is_admin": False
    })
    group_id = response.json()["id"]
    
    # Grant a permission
    response = admin_session.post(
        f"/api/v1/user-groups/{group_id}/permissions",
        json={"resource": "clients", "action": "read"}
    )
    assert response.status_code == 200
    
    # Get the permission ID
    response = admin_session.get(f"/api/v1/user-groups/{group_id}/permissions")
    permissions = response.json()
    permission_id = next(p["id"] for p in permissions if p["resource"] == "clients")
    
    # Revoke it
    response = admin_session.delete(
        f"/api/v1/user-groups/{group_id}/permissions/{permission_id}"
    )
    assert response.status_code == 200
    
    # Verify it was revoked
    response = admin_session.get(f"/api/v1/user-groups/{group_id}/permissions")
    new_permissions = response.json()
    assert not any(p["resource"] == "clients" and p["action"] == "read" for p in new_permissions)


def test_admin_group_has_all_permissions(admin_session):
    """Test that admin groups return all permissions."""
    # Get Administrators group
    response = admin_session.get("/api/v1/user-groups")
    groups = response.json()
    admin_group = next((g for g in groups if g["name"] == "Administrators"), None)
    
    # Get its permissions
    response = admin_session.get(f"/api/v1/user-groups/{admin_group['id']}/permissions")
    assert response.status_code == 200
    
    permissions = response.json()
    # Admin group should have all permissions
    assert len(permissions) > 20  # We seeded many permissions
    
    # Should have permissions from all resources
    resources = {p["resource"] for p in permissions}
    assert "clients" in resources
    assert "users" in resources
    assert "ca" in resources


def test_list_group_members(admin_session):
    """Test listing members of a group."""
    # Get Administrators group
    response = admin_session.get("/api/v1/user-groups")
    groups = response.json()
    admin_group = next((g for g in groups if g["name"] == "Administrators"), None)
    
    # List members
    response = admin_session.get(f"/api/v1/user-groups/{admin_group['id']}/members")
    assert response.status_code == 200
    
    members = response.json()
    assert isinstance(members, list)
    assert len(members) >= 1  # At least our test admin


def test_add_and_remove_group_member(admin_session):
    """Test adding and removing a user from a group."""
    # Create a test user
    from app.db import AsyncSessionLocal
    from app.models.user import User
    from app.core.auth import hash_password
    import asyncio
    
    async def create_test_user():
        async with AsyncSessionLocal() as session:
            user = User(
                email="test_member@test.com",
                hashed_password=hash_password("pass123"),
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user.id
    
    user_id = asyncio.run(create_test_user())
    
    # Create a test group
    response = admin_session.post("/api/v1/user-groups", json={
        "name": "Test Membership Group",
        "description": "Test group",
        "is_admin": False
    })
    group_id = response.json()["id"]
    
    # Add user to group
    response = admin_session.post(
        f"/api/v1/user-groups/{group_id}/members",
        params={"user_id": user_id}
    )
    assert response.status_code == 200
    
    # Verify membership
    response = admin_session.get(f"/api/v1/user-groups/{group_id}/members")
    members = response.json()
    assert any(m["id"] == user_id for m in members)
    
    # Remove user from group
    response = admin_session.delete(
        f"/api/v1/user-groups/{group_id}/members/{user_id}"
    )
    assert response.status_code == 200
    
    # Verify removal
    response = admin_session.get(f"/api/v1/user-groups/{group_id}/members")
    members = response.json()
    assert not any(m["id"] == user_id for m in members)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
