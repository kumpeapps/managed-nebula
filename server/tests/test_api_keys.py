"""Tests for API key authentication and management."""
import pytest
from httpx import AsyncClient

from app.services.api_key_manager import generate_api_key, verify_api_key


class TestAPIKeyGeneration:
    """Tests for API key generation and verification."""
    
    def test_generate_api_key_format(self):
        """Test that generated API keys have the correct format."""
        full_key, key_prefix, key_hash = generate_api_key()
        
        # Check key format
        assert full_key.startswith("mnapi_")
        assert len(full_key) == 70  # "mnapi_" (6 chars) + 64 hex chars
        
        # Check prefix
        assert key_prefix == full_key[:12]  # "mnapi_" + first 6 chars
        assert key_prefix.startswith("mnapi_")
        
        # Check hash
        assert len(key_hash) > 0
        assert key_hash != full_key  # Should be hashed
    
    def test_verify_api_key(self):
        """Test API key verification."""
        full_key, _, key_hash = generate_api_key()
        
        # Should verify correctly
        assert verify_api_key(full_key, key_hash) is True
        
        # Should fail with wrong key
        assert verify_api_key("mnapi_wrongkey", key_hash) is False
        assert verify_api_key("", key_hash) is False


@pytest.mark.asyncio
class TestAPIKeyEndpoints:
    """Tests for API key REST endpoints."""
    
    async def test_create_api_key(self, async_client: AsyncClient, auth_headers: dict):
        """Test creating a new API key."""
        response = await async_client.post(
            "/api/v1/api-keys",
            json={
                "name": "Test Key",
                "expires_in_days": 365
            },
            cookies=auth_headers.get("cookies", {}),
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "id" in data
        assert "key" in data  # Full key should be returned once
        assert "name" in data
        assert data["name"] == "Test Key"
        assert data["key"].startswith("mnapi_")
        assert "key_prefix" in data
        assert "created_at" in data
        assert "expires_at" in data
        
    async def test_create_api_key_without_expiration(self, async_client: AsyncClient, auth_headers: dict):
        """Test creating an API key without expiration."""
        response = await async_client.post(
            "/api/v1/api-keys",
            json={"name": "Permanent Key"},
            cookies=auth_headers.get("cookies", {}),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["expires_at"] is None
    
    async def test_list_api_keys(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing API keys."""
        # Create a key first
        create_response = await async_client.post(
            "/api/v1/api-keys",
            json={"name": "List Test Key"},
            cookies=auth_headers.get("cookies", {}),
        )
        assert create_response.status_code == 200
        
        # List keys
        response = await async_client.get(
            "/api/v1/api-keys",
            cookies=auth_headers.get("cookies", {}),
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "keys" in data
        assert "total" in data
        assert data["total"] > 0
        assert len(data["keys"]) > 0
        
        # Check that keys don't include full key value
        for key in data["keys"]:
            assert "key" not in key  # Full key should not be in list
            assert "key_prefix" in key
            assert "name" in key
            assert "is_active" in key
    
    async def test_get_api_key_by_id(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting a specific API key."""
        # Create a key
        create_response = await async_client.post(
            "/api/v1/api-keys",
            json={"name": "Get Test Key"},
            cookies=auth_headers.get("cookies", {}),
        )
        key_id = create_response.json()["id"]
        
        # Get it back
        response = await async_client.get(
            f"/api/v1/api-keys/{key_id}",
            cookies=auth_headers.get("cookies", {}),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == key_id
        assert data["name"] == "Get Test Key"
    
    async def test_update_api_key(self, async_client: AsyncClient, auth_headers: dict):
        """Test updating an API key."""
        # Create a key
        create_response = await async_client.post(
            "/api/v1/api-keys",
            json={"name": "Update Test Key"},
            cookies=auth_headers.get("cookies", {}),
        )
        key_id = create_response.json()["id"]
        
        # Update it
        response = await async_client.put(
            f"/api/v1/api-keys/{key_id}",
            json={"name": "Updated Name"},
            cookies=auth_headers.get("cookies", {}),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
    
    async def test_revoke_api_key(self, async_client: AsyncClient, auth_headers: dict):
        """Test revoking an API key."""
        # Create a key
        create_response = await async_client.post(
            "/api/v1/api-keys",
            json={"name": "Revoke Test Key"},
            cookies=auth_headers.get("cookies", {}),
        )
        key_id = create_response.json()["id"]
        
        # Revoke it
        response = await async_client.delete(
            f"/api/v1/api-keys/{key_id}",
            cookies=auth_headers.get("cookies", {}),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "revoked"
        
        # Verify it's inactive
        get_response = await async_client.get(
            f"/api/v1/api-keys/{key_id}",
            cookies=auth_headers.get("cookies", {}),
        )
        assert get_response.json()["is_active"] is False
    
    async def test_rate_limit_api_keys(self, async_client: AsyncClient, auth_headers: dict):
        """Test that users can't create more than 10 API keys."""
        # Try to create 11 keys
        for i in range(11):
            response = await async_client.post(
                "/api/v1/api-keys",
                json={"name": f"Rate Limit Test {i}"},
                cookies=auth_headers.get("cookies", {}),
            )
            
            if i < 10:
                assert response.status_code == 200
            else:
                # 11th key should fail
                assert response.status_code == 400
                assert "Maximum number" in response.json()["detail"]


@pytest.mark.asyncio
class TestAPIKeyAuthentication:
    """Tests for authenticating with API keys."""
    
    async def test_authenticate_with_api_key(self, async_client: AsyncClient, auth_headers: dict):
        """Test using an API key to authenticate."""
        # Create an API key
        create_response = await async_client.post(
            "/api/v1/api-keys",
            json={"name": "Auth Test Key"},
            cookies=auth_headers.get("cookies", {}),
        )
        api_key = create_response.json()["key"]
        
        # Use the API key to access a protected endpoint
        response = await async_client.get(
            "/api/v1/clients",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
        # Should be able to access the endpoint
    
    async def test_invalid_api_key_fails(self, async_client: AsyncClient):
        """Test that invalid API keys are rejected."""
        response = await async_client.get(
            "/api/v1/clients",
            headers={"Authorization": "Bearer mnapi_invalidkey12345"}
        )
        
        assert response.status_code == 401
    
    async def test_revoked_api_key_fails(self, async_client: AsyncClient, auth_headers: dict):
        """Test that revoked API keys can't be used."""
        # Create and then revoke a key
        create_response = await async_client.post(
            "/api/v1/api-keys",
            json={"name": "Revoke Auth Test"},
            cookies=auth_headers.get("cookies", {}),
        )
        api_key = create_response.json()["key"]
        key_id = create_response.json()["id"]
        
        # Revoke it
        await async_client.delete(
            f"/api/v1/api-keys/{key_id}",
            cookies=auth_headers.get("cookies", {}),
        )
        
        # Try to use it
        response = await async_client.get(
            "/api/v1/clients",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 401
    
    async def test_api_key_usage_tracking(self, async_client: AsyncClient, auth_headers: dict):
        """Test that API key usage is tracked."""
        # Create an API key
        create_response = await async_client.post(
            "/api/v1/api-keys",
            json={"name": "Usage Test Key"},
            cookies=auth_headers.get("cookies", {}),
        )
        api_key = create_response.json()["key"]
        key_id = create_response.json()["id"]
        
        # Use it a few times
        for _ in range(3):
            await async_client.get(
                "/api/v1/clients",
                headers={"Authorization": f"Bearer {api_key}"}
            )
        
        # Check usage count
        get_response = await async_client.get(
            f"/api/v1/api-keys/{key_id}",
            cookies=auth_headers.get("cookies", {}),
        )
        data = get_response.json()
        
        assert data["usage_count"] >= 3
        assert data["last_used_at"] is not None
