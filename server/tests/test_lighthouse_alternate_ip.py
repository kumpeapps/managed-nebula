"""
Test that lighthouses with alternate IPs in different pools are properly discovered by clients.

This test verifies the fix for the issue where clients in a pool don't see lighthouses
when the lighthouse's primary IP is in a different pool but has an alternate IP in the client's pool.
"""
import pytest
import shutil
from fastapi.testclient import TestClient
from app.main import app
import yaml


# Valid Nebula public key for testing (generated with nebula-cert keygen)
VALID_NEBULA_PUBLIC_KEY = """-----BEGIN NEBULA X25519 PUBLIC KEY-----
TPwacPvxYLFZnfM8QdU1XJ93RY0NiB0apbwkBMvGSBY=
-----END NEBULA X25519 PUBLIC KEY-----"""


@pytest.fixture(scope="function")
def client():
    """Create test client for each test function."""
    # Shutdown and remove any existing scheduler from previous tests
    if hasattr(app.state, 'scheduler'):
        try:
            if app.state.scheduler.running:
                app.state.scheduler.shutdown(wait=False)
        except:
            pass
        delattr(app.state, 'scheduler')
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up scheduler after test
    if hasattr(app.state, 'scheduler'):
        try:
            if app.state.scheduler.running:
                app.state.scheduler.shutdown(wait=False)
        except:
            pass
        delattr(app.state, 'scheduler')


def login_as_admin(client):
    """Helper to login as admin and return session token."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"}
    )
    assert login_response.status_code == 200
    return login_response.cookies.get("session")


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not installed")
def test_lighthouse_with_alternate_ip_is_discovered(client):
    """Test that lighthouse with alternate IP in client's pool is included in config."""
    # Login as admin
    admin_token = login_as_admin(client)
    
    # Create two IP pools
    pool_a_response = client.post(
        "/api/v1/ip-pools",
        json={
            "cidr": "10.100.0.0/16",
            "description": "Pool A"
        },
        cookies={"session": admin_token}
    )
    assert pool_a_response.status_code == 201
    pool_a_id = pool_a_response.json()["id"]
    
    pool_b_response = client.post(
        "/api/v1/ip-pools",
        json={
            "cidr": "10.200.0.0/16",
            "description": "Pool B"
        },
        cookies={"session": admin_token}
    )
    assert pool_b_response.status_code == 201
    pool_b_id = pool_b_response.json()["id"]
    
    # Create a lighthouse with primary IP in Pool A
    lighthouse_response = client.post(
        "/api/v1/clients",
        json={
            "name": "lighthouse-cross-pool",
            "is_lighthouse": True,
            "public_ip": "1.2.3.4",
            "pool_id": pool_a_id
        },
        cookies={"session": admin_token}
    )
    assert lighthouse_response.status_code == 200
    lighthouse_data = lighthouse_response.json()
    lighthouse_id = lighthouse_data["id"]
    lighthouse_primary_ip = lighthouse_data["ip_address"]  # IP in Pool A
    
    # Add an alternate IP in Pool B for the lighthouse
    alternate_ip_response = client.post(
        f"/api/v1/clients/{lighthouse_id}/alternate-ips",
        json={
            "pool_id": pool_b_id,
            "ip_version": "ipv4"
        },
        cookies={"session": admin_token}
    )
    assert alternate_ip_response.status_code == 201
    lighthouse_alternate_ip = alternate_ip_response.json()["ip_address"]  # IP in Pool B
    
    # Create a regular client in Pool B
    regular_client_response = client.post(
        "/api/v1/clients",
        json={
            "name": "client-in-pool-b",
            "pool_id": pool_b_id
        },
        cookies={"session": admin_token}
    )
    assert regular_client_response.status_code == 200
    regular_client_data = regular_client_response.json()
    regular_client_token = regular_client_data["token"]
    
    # Fetch config for regular client using the client API
    config_response = client.post(
        "/api/v1/client/config",
        json={"token": regular_client_token, "public_key": VALID_NEBULA_PUBLIC_KEY}
    )
    assert config_response.status_code == 200
    config_data = config_response.json()
    config_yaml = yaml.safe_load(config_data["config"])
    
    # CRITICAL: The lighthouse should be included because it has an alternate IP in Pool B
    # The client should see the lighthouse's ALTERNATE IP (the one in Pool B), not the primary IP
    assert "lighthouse" in config_yaml
    assert "hosts" in config_yaml["lighthouse"]
    
    # The lighthouse's alternate IP should be in the hosts list
    assert lighthouse_alternate_ip in config_yaml["lighthouse"]["hosts"], \
        f"Expected lighthouse alternate IP {lighthouse_alternate_ip} in hosts {config_yaml['lighthouse']['hosts']}"
    
    # The primary IP should NOT be in the hosts list (it's in a different pool)
    assert lighthouse_primary_ip not in config_yaml["lighthouse"]["hosts"], \
        f"Lighthouse primary IP {lighthouse_primary_ip} should NOT be in hosts (different pool)"
    
    # Verify static_host_map contains the alternate IP
    assert "static_host_map" in config_yaml
    assert lighthouse_alternate_ip in config_yaml["static_host_map"], \
        f"Expected lighthouse alternate IP {lighthouse_alternate_ip} in static_host_map"
    assert config_yaml["static_host_map"][lighthouse_alternate_ip] == ["1.2.3.4:4242"]
    
    # The primary IP should NOT be in static_host_map (different pool)
    assert lighthouse_primary_ip not in config_yaml["static_host_map"], \
        f"Lighthouse primary IP {lighthouse_primary_ip} should NOT be in static_host_map (different pool)"


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not installed")
def test_lighthouse_with_multiple_alternate_ips_across_pools(client):
    """Test lighthouse with alternate IPs in multiple pools is discovered correctly by clients in each pool."""
    # Login as admin
    admin_token = login_as_admin(client)
    
    # Create three IP pools
    pools = []
    for i, letter in enumerate(['A', 'B', 'C']):
        pool_response = client.post(
            "/api/v1/ip-pools",
            json={
                "cidr": f"10.{i+1}00.0.0/16",
                "description": f"Pool {letter}"
            },
            cookies={"session": admin_token}
        )
        assert pool_response.status_code == 201
        pools.append(pool_response.json())
    
    # Create a lighthouse with primary IP in Pool A
    lighthouse_response = client.post(
        "/api/v1/clients",
        json={
            "name": "multi-pool-lighthouse",
            "is_lighthouse": True,
            "public_ip": "5.6.7.8",
            "pool_id": pools[0]["id"]
        },
        cookies={"session": admin_token}
    )
    assert lighthouse_response.status_code == 200
    lighthouse_data = lighthouse_response.json()
    lighthouse_id = lighthouse_data["id"]
    lighthouse_ips = {pools[0]["id"]: lighthouse_data["ip_address"]}
    
    # Add alternate IPs in Pools B and C
    for pool in pools[1:3]:
        alternate_ip_response = client.post(
            f"/api/v1/clients/{lighthouse_id}/alternate-ips",
            json={
                "pool_id": pool["id"],
                "ip_version": "ipv4"
            },
            cookies={"session": admin_token}
        )
        assert alternate_ip_response.status_code == 201
        lighthouse_ips[pool["id"]] = alternate_ip_response.json()["ip_address"]
    
    # Create a client in each pool and verify they see the correct lighthouse IP
    for pool in pools:
        client_response = client.post(
            "/api/v1/clients",
            json={
                "name": f"client-in-pool-{pool['description'][-1].lower()}",
                "pool_id": pool["id"]
            },
            cookies={"session": admin_token}
        )
        assert client_response.status_code == 200
        client_data = client_response.json()
        client_token = client_data["token"]
        
        # Fetch config
        config_response = client.post(
            "/api/v1/client/config",
            json={"token": client_token, "public_key": VALID_NEBULA_PUBLIC_KEY}
        )
        assert config_response.status_code == 200
        config_data = config_response.json()
        config_yaml = yaml.safe_load(config_data["config"])
        
        # Verify the client sees the lighthouse's IP from its own pool
        expected_lighthouse_ip = lighthouse_ips[pool["id"]]
        assert expected_lighthouse_ip in config_yaml["lighthouse"]["hosts"], \
            f"Client in {pool['description']} should see lighthouse IP {expected_lighthouse_ip}"
        
        # Verify other pool IPs are NOT included
        for other_pool_id, other_ip in lighthouse_ips.items():
            if other_pool_id != pool["id"]:
                assert other_ip not in config_yaml["lighthouse"]["hosts"], \
                    f"Client in {pool['description']} should NOT see lighthouse IP {other_ip} from other pool"


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not installed")
def test_lighthouse_alternate_ip_in_admin_download_config(client):
    """Test that admin config download API also includes lighthouses with alternate IPs."""
    # Login as admin
    admin_token = login_as_admin(client)
    
    # Create two IP pools
    pool_a_response = client.post(
        "/api/v1/ip-pools",
        json={"cidr": "10.100.0.0/16", "description": "Pool A"},
        cookies={"session": admin_token}
    )
    assert pool_a_response.status_code == 201
    pool_a_id = pool_a_response.json()["id"]
    
    pool_b_response = client.post(
        "/api/v1/ip-pools",
        json={"cidr": "10.200.0.0/16", "description": "Pool B"},
        cookies={"session": admin_token}
    )
    assert pool_b_response.status_code == 201
    pool_b_id = pool_b_response.json()["id"]
    
    # Create lighthouse with primary IP in Pool A
    lighthouse_response = client.post(
        "/api/v1/clients",
        json={
            "name": "lighthouse",
            "is_lighthouse": True,
            "public_ip": "9.9.9.9",
            "pool_id": pool_a_id
        },
        cookies={"session": admin_token}
    )
    assert lighthouse_response.status_code == 200
    lighthouse_id = lighthouse_response.json()["id"]
    
    # Add alternate IP in Pool B
    alternate_ip_response = client.post(
        f"/api/v1/clients/{lighthouse_id}/alternate-ips",
        json={"pool_id": pool_b_id, "ip_version": "ipv4"},
        cookies={"session": admin_token}
    )
    assert alternate_ip_response.status_code == 201
    lighthouse_alternate_ip = alternate_ip_response.json()["ip_address"]
    
    # Create client in Pool B
    regular_client_response = client.post(
        "/api/v1/clients",
        json={"name": "client-pool-b", "pool_id": pool_b_id},
        cookies={"session": admin_token}
    )
    assert regular_client_response.status_code == 200
    regular_client_id = regular_client_response.json()["id"]
    
    # Download config via admin API
    config_response = client.get(
        f"/api/v1/clients/{regular_client_id}/config",
        cookies={"session": admin_token}
    )
    assert config_response.status_code == 200
    config_data = config_response.json()
    config_yaml = yaml.safe_load(config_data["config"])
    
    # Verify lighthouse alternate IP is included
    assert lighthouse_alternate_ip in config_yaml["lighthouse"]["hosts"], \
        f"Expected lighthouse alternate IP {lighthouse_alternate_ip} in hosts"
    assert lighthouse_alternate_ip in config_yaml["static_host_map"], \
        f"Expected lighthouse alternate IP {lighthouse_alternate_ip} in static_host_map"
