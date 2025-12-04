"""Integration tests for lighthouse static_host_map generation."""
import pytest
import shutil
import asyncio
from fastapi.testclient import TestClient
from app.main import app
import yaml
# Import the bootstrap function directly from manage.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from manage import bootstrap_permissions
from app.db import AsyncSessionLocal
from app.models.user import User
from app.models.permissions import UserGroup, UserGroupMembership
from app.core.auth import hash_password
from sqlalchemy import select


# Valid Nebula public key for testing (generated with nebula-cert keygen)
VALID_NEBULA_PUBLIC_KEY = """-----BEGIN NEBULA X25519 PUBLIC KEY-----
TPwacPvxYLFZnfM8QdU1XJ93RY0NiB0apbwkBMvGSBY=
-----END NEBULA X25519 PUBLIC KEY-----"""


@pytest.fixture(scope="function")
def client():
    """Create test client for each test function."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def setup_admin_for_test():
    """Create admin user before each test."""
    async def create_admin():
        async with AsyncSessionLocal() as session:
            # Bootstrap permissions
            await bootstrap_permissions(session)
            
            # Ensure Administrators group exists
            result = await session.execute(
                select(UserGroup).where(UserGroup.name == "Administrators")
            )
            admins = result.scalar_one_or_none()
            if not admins:
                admins = UserGroup(
                    name="Administrators",
                    description="Administrators with full access",
                    is_admin=True
                )
                session.add(admins)
                await session.flush()
            
            # Create admin user
            result = await session.execute(
                select(User).where(User.email == "admin@test.com")
            )
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                admin_user = User(
                    email="admin@test.com",
                    hashed_password=hash_password("testpass123"),
                    is_active=True
                )
                session.add(admin_user)
                await session.flush()
                
                # Add to admin group
                membership = UserGroupMembership(
                    user_id=admin_user.id,
                    user_group_id=admins.id
                )
                session.add(membership)
            
            await session.commit()
    
    asyncio.run(create_admin())


def login_as_admin(client):
    """Helper to login as admin and return session token."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"}
    )
    assert login_response.status_code == 200
    return login_response.cookies.get("session")


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not installed")
def test_single_lighthouse_empty_static_map(client):
    """Test that a single lighthouse gets empty static_host_map."""
    # Setup: Create admin, CA, pool
    admin_token = login_as_admin(client)
    
    ca_response = client.post(
        "/api/v1/ca/create",
        json={"name": "test-ca", "duration_days": 540},
        cookies={"session": admin_token}
    )
    assert ca_response.status_code == 200
    
    pool_response = client.post(
        "/api/v1/ip-pools",
        json={"name": "main-pool", "cidr": "10.100.0.0/16"},
        cookies={"session": admin_token}
    )
    assert pool_response.status_code == 200
    
    # Create single lighthouse with public IP
    lh_response = client.post(
        "/api/v1/clients",
        json={
            "name": "lighthouse-1",
            "is_lighthouse": True,
            "public_ip": "1.2.3.4"
        },
        cookies={"session": admin_token}
    )
    assert lh_response.status_code == 200
    lh_data = lh_response.json()
    lh_id = lh_data["id"]
    token = lh_data["token"]  # Token is returned in client creation response
    
    # Fetch config as lighthouse (need valid PEM-formatted public key)
    config_response = client.post(
        "/api/v1/client/config",
        json={"token": token, "public_key": VALID_NEBULA_PUBLIC_KEY}
    )
    assert config_response.status_code == 200
    config_data = config_response.json()
    
    # Parse YAML config
    config = yaml.safe_load(config_data["config"])
    
    # Verify static_host_map is empty
    assert "static_host_map" in config
    assert len(config["static_host_map"]) == 0


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not installed")
def test_multiple_lighthouses_self_exclusion(client):
    """Test that each lighthouse excludes itself from static_host_map."""
    # Setup: Create admin, CA, pool
    admin_token = login_as_admin(client)
    
    ca_response = client.post(
        "/api/v1/ca/create",
        json={"name": "test-ca", "duration_days": 540},
        cookies={"session": admin_token}
    )
    assert ca_response.status_code == 200
    
    pool_response = client.post(
        "/api/v1/ip-pools",
        json={"name": "main-pool", "cidr": "10.100.0.0/16"},
        cookies={"session": admin_token}
    )
    assert pool_response.status_code == 200
    
    # Create three lighthouses
    lighthouses = []
    for i in range(1, 4):
        lh_response = client.post(
            "/api/v1/clients",
            json={
                "name": f"lighthouse-{i}",
                "is_lighthouse": True,
                "public_ip": f"1.2.3.{i}"
            },
            cookies={"session": admin_token}
        )
        assert lh_response.status_code == 200
        lh_data = lh_response.json()
        
        lighthouses.append({
            "id": lh_data["id"],
            "name": lh_data["name"],
            "token": lh_data["token"],  # Token is returned in client creation response
            "ip": lh_data["ip_address"]  # Fixed: use ip_address not ip_assignments
        })
    
    # Fetch config for each lighthouse and verify self-exclusion
    for idx, lh in enumerate(lighthouses):
        config_response = client.post(
            "/api/v1/client/config",
            json={"token": lh["token"], "public_key": VALID_NEBULA_PUBLIC_KEY}
        )
        assert config_response.status_code == 200
        config_data = config_response.json()
        
        # Parse YAML config
        config = yaml.safe_load(config_data["config"])
        
        # Verify static_host_map exists and has 2 entries (excluding self)
        assert "static_host_map" in config
        assert len(config["static_host_map"]) == 2, f"Lighthouse {lh['name']} should have 2 entries in static_host_map"
        
        # Verify self IP is NOT in the map
        assert lh["ip"] not in config["static_host_map"], f"Lighthouse {lh['name']} should not have its own IP in static_host_map"
        
        # Verify other lighthouse IPs ARE in the map
        other_ips = [other["ip"] for other in lighthouses if other["id"] != lh["id"]]
        for other_ip in other_ips:
            assert other_ip in config["static_host_map"], f"Lighthouse {lh['name']} should have {other_ip} in static_host_map"


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not installed")
def test_non_lighthouse_includes_all_lighthouses(client):
    """Test that non-lighthouse clients receive all lighthouse IPs in static_host_map."""
    # Setup: Create admin, CA, pool
    admin_token = login_as_admin(client)
    
    ca_response = client.post(
        "/api/v1/ca/create",
        json={"name": "test-ca", "duration_days": 540},
        cookies={"session": admin_token}
    )
    assert ca_response.status_code == 200
    
    pool_response = client.post(
        "/api/v1/ip-pools",
        json={"name": "main-pool", "cidr": "10.100.0.0/16"},
        cookies={"session": admin_token}
    )
    assert pool_response.status_code == 200
    
    # Create three lighthouses
    lighthouse_ips = []
    for i in range(1, 4):
        lh_response = client.post(
            "/api/v1/clients",
            json={
                "name": f"lighthouse-{i}",
                "is_lighthouse": True,
                "public_ip": f"1.2.3.{i}"
            },
            cookies={"session": admin_token}
        )
        assert lh_response.status_code == 200
        lighthouse_ips.append(lh_response.json()["ip_address"])  # Fixed: use ip_address not ip_assignments
    
    # Create regular client
    regular_response = client.post(
        "/api/v1/clients",
        json={
            "name": "regular-client",
            "is_lighthouse": False
        },
        cookies={"session": admin_token}
    )
    assert regular_response.status_code == 200
    regular_data = regular_response.json()
    token = regular_data["token"]  # Token is returned in client creation response
    
    # Fetch config as regular client
    config_response = client.post(
        "/api/v1/client/config",
        json={"token": token, "public_key": VALID_NEBULA_PUBLIC_KEY}
    )
    assert config_response.status_code == 200
    config_data = config_response.json()
    
    # Parse YAML config
    config = yaml.safe_load(config_data["config"])
    
    # Verify static_host_map contains ALL lighthouse IPs
    assert "static_host_map" in config
    assert len(config["static_host_map"]) == 3
    for lh_ip in lighthouse_ips:
        assert lh_ip in config["static_host_map"]


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not installed")
def test_cross_pool_lighthouse_isolation(client):
    """Test that lighthouses from different pools are isolated in static_host_map."""
    # Setup: Create admin, CA, two pools
    admin_token = login_as_admin(client)
    
    ca_response = client.post(
        "/api/v1/ca/create",
        json={"name": "test-ca", "duration_days": 540},
        cookies={"session": admin_token}
    )
    assert ca_response.status_code == 200
    
    pool_a_response = client.post(
        "/api/v1/ip-pools",
        json={"name": "pool-a", "cidr": "10.100.0.0/16"},
        cookies={"session": admin_token}
    )
    assert pool_a_response.status_code == 200
    pool_a_id = pool_a_response.json()["id"]
    
    pool_b_response = client.post(
        "/api/v1/ip-pools",
        json={"name": "pool-b", "cidr": "10.200.0.0/16"},
        cookies={"session": admin_token}
    )
    assert pool_b_response.status_code == 200
    pool_b_id = pool_b_response.json()["id"]
    
    # Create lighthouse in Pool A
    lh_a_response = client.post(
        "/api/v1/clients",
        json={
            "name": "lighthouse-a",
            "is_lighthouse": True,
            "public_ip": "1.2.3.1",
            "pool_id": pool_a_id
        },
        cookies={"session": admin_token}
    )
    assert lh_a_response.status_code == 200
    lh_a_data = lh_a_response.json()
    lh_a_ip = lh_a_data["ip_address"]  # Fixed: use ip_address not ip_assignments
    
    # Create lighthouse in Pool B
    lh_b_response = client.post(
        "/api/v1/clients",
        json={
            "name": "lighthouse-b",
            "is_lighthouse": True,
            "public_ip": "1.2.3.2",
            "pool_id": pool_b_id
        },
        cookies={"session": admin_token}
    )
    assert lh_b_response.status_code == 200
    lh_b_data = lh_b_response.json()
    lh_b_ip = lh_b_data["ip_address"]  # Fixed: use ip_address not ip_assignments
    
    # Create another lighthouse in Pool A
    lh_a2_response = client.post(
        "/api/v1/clients",
        json={
            "name": "lighthouse-a2",
            "is_lighthouse": True,
            "public_ip": "1.2.3.3",
            "pool_id": pool_a_id
        },
        cookies={"session": admin_token}
    )
    assert lh_a2_response.status_code == 200
    lh_a2_data = lh_a2_response.json()
    lh_a2_ip = lh_a2_data["ip_address"]  # Fixed: use ip_address not ip_assignments
    
    # Fetch config for lighthouse-a (token already in lh_a_data)
    token = lh_a_data["token"]
    config_response = client.post(
        "/api/v1/client/config",
        json={"token": token, "public_key": VALID_NEBULA_PUBLIC_KEY}
    )
    assert config_response.status_code == 200
    config_data = config_response.json()
    
    # Parse YAML config
    config = yaml.safe_load(config_data["config"])
    
    # Verify static_host_map contains only Pool A lighthouses (excluding self)
    assert "static_host_map" in config
    assert len(config["static_host_map"]) == 1, "Should only have 1 entry (lighthouse-a2 from same pool)"
    assert lh_a_ip not in config["static_host_map"], "Should not include self"
    assert lh_a2_ip in config["static_host_map"], "Should include lighthouse-a2 from same pool"
    assert lh_b_ip not in config["static_host_map"], "Should not include lighthouse from different pool"


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not installed")
def test_download_client_config_endpoint_lighthouse_exclusion(client):
    """Test that GET /api/v1/clients/{id}/config also excludes self for lighthouses."""
    # Setup: Create admin, CA, pool
    admin_token = login_as_admin(client)
    
    ca_response = client.post(
        "/api/v1/ca/create",
        json={"name": "test-ca", "duration_days": 540},
        cookies={"session": admin_token}
    )
    assert ca_response.status_code == 200
    
    pool_response = client.post(
        "/api/v1/ip-pools",
        json={"name": "main-pool", "cidr": "10.100.0.0/16"},
        cookies={"session": admin_token}
    )
    assert pool_response.status_code == 200
    
    # Create two lighthouses
    lh1_response = client.post(
        "/api/v1/clients",
        json={
            "name": "lighthouse-1",
            "is_lighthouse": True,
            "public_ip": "1.2.3.1"
        },
        cookies={"session": admin_token}
    )
    assert lh1_response.status_code == 200
    lh1_data = lh1_response.json()
    lh1_ip = lh1_data["ip_address"]  # Fixed: use ip_address not ip_assignments
    token = lh1_data["token"]  # Token is returned in client creation response
    
    lh2_response = client.post(
        "/api/v1/clients",
        json={
            "name": "lighthouse-2",
            "is_lighthouse": True,
            "public_ip": "1.2.3.2"
        },
        cookies={"session": admin_token}
    )
    assert lh2_response.status_code == 200
    lh2_data = lh2_response.json()
    lh2_ip = lh2_data["ip_address"]  # Fixed: use ip_address not ip_assignments
    
    # Fetch config via POST to trigger certificate generation
    client.post(
        "/api/v1/client/config",
        json={"token": token, "public_key": VALID_NEBULA_PUBLIC_KEY}
    )
    
    # Download config via GET endpoint (admin)
    download_response = client.get(
        f"/api/v1/clients/{lh1_data['id']}/config",
        cookies={"session": admin_token}
    )
    assert download_response.status_code == 200
    
    # Parse config from JSON response (GET endpoint returns JSON with config_yaml field)
    response_data = download_response.json()
    config = yaml.safe_load(response_data["config_yaml"])
    
    # Verify static_host_map excludes self
    assert "static_host_map" in config
    assert len(config["static_host_map"]) == 1
    assert lh1_ip not in config["static_host_map"], "Should not include self"
    assert lh2_ip in config["static_host_map"], "Should include other lighthouse"
