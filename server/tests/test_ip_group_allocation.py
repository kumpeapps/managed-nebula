"""Test IP allocation from IP groups."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auto_allocate_from_ip_group(async_client: AsyncClient, admin_user):
    """Test that auto-allocation respects IP group range when specified."""
    # Login as admin
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test_admin@test.com", "password": "testpass123"}
    )
    assert login_resp.status_code == 200
    
    # Create IP pool with CIDR 10.0.0.0/24
    pool_resp = await async_client.post(
        "/api/v1/ip-pools",
        json={"cidr": "10.0.0.0/24", "description": "Test pool"}
    )
    assert pool_resp.status_code == 200
    pool_id = pool_resp.json()["id"]
    
    # Create IP group with range 10.0.0.100 - 10.0.0.110
    # This is a subset of the pool's CIDR
    ip_group_resp = await async_client.post(
        "/api/v1/ip-groups",
        json={
            "name": "test-group",
            "description": "Test IP group",
            "pool_id": pool_id,
            "start_ip": "10.0.0.100",
            "end_ip": "10.0.0.110"
        }
    )
    assert ip_group_resp.status_code == 200
    ip_group_id = ip_group_resp.json()["id"]
    
    # Create client with IP group - should auto-allocate from group range (10.0.0.100-110)
    # not from the beginning of the pool (10.0.0.1)
    client_resp = await async_client.post(
        "/api/v1/clients",
        json={
            "name": "test-client-1",
            "pool_id": pool_id,
            "ip_group_id": ip_group_id
        }
    )
    assert client_resp.status_code == 200
    client_data = client_resp.json()
    
    # Verify the allocated IP is within the IP group range
    allocated_ip = client_data["assigned_ips"][0]["ip_address"]
    assert allocated_ip.startswith("10.0.0."), f"IP should be from pool: {allocated_ip}"
    
    # Parse the last octet
    last_octet = int(allocated_ip.split(".")[-1])
    assert 100 <= last_octet <= 110, \
        f"IP should be in range 10.0.0.100-110, got {allocated_ip}"
    
    # Specifically, the first available IP in the group should be 10.0.0.100
    assert allocated_ip == "10.0.0.100", \
        f"First auto-allocated IP from group should be 10.0.0.100, got {allocated_ip}"
    
    print(f"✓ Client allocated IP {allocated_ip} from IP group range (10.0.0.100-110)")


@pytest.mark.asyncio
async def test_auto_allocate_without_ip_group(async_client: AsyncClient, admin_user):
    """Test that auto-allocation without IP group uses entire pool."""
    # Login as admin
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test_admin@test.com", "password": "testpass123"}
    )
    assert login_resp.status_code == 200
    
    # Create IP pool
    pool_resp = await async_client.post(
        "/api/v1/ip-pools",
        json={"cidr": "10.1.0.0/24", "description": "Test pool 2"}
    )
    assert pool_resp.status_code == 200
    pool_id = pool_resp.json()["id"]
    
    # Create client WITHOUT IP group - should allocate from beginning of pool
    client_resp = await async_client.post(
        "/api/v1/clients",
        json={
            "name": "test-client-2",
            "pool_id": pool_id
        }
    )
    assert client_resp.status_code == 200
    client_data = client_resp.json()
    
    # Verify the allocated IP is the first host IP in the pool (10.1.0.1)
    allocated_ip = client_data["assigned_ips"][0]["ip_address"]
    assert allocated_ip == "10.1.0.1", \
        f"First auto-allocated IP from pool should be 10.1.0.1, got {allocated_ip}"
    
    print(f"✓ Client allocated IP {allocated_ip} from entire pool (no IP group)")


@pytest.mark.asyncio
async def test_manual_ip_with_ip_group_validation(async_client: AsyncClient, admin_user):
    """Test that manual IP assignment validates against IP group range."""
    # Login as admin
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test_admin@test.com", "password": "testpass123"}
    )
    assert login_resp.status_code == 200
    
    # Create IP pool
    pool_resp = await async_client.post(
        "/api/v1/ip-pools",
        json={"cidr": "10.2.0.0/24", "description": "Test pool 3"}
    )
    assert pool_resp.status_code == 200
    pool_id = pool_resp.json()["id"]
    
    # Create IP group with range 10.2.0.50 - 10.2.0.60
    ip_group_resp = await async_client.post(
        "/api/v1/ip-groups",
        json={
            "name": "test-group-3",
            "description": "Test IP group 3",
            "pool_id": pool_id,
            "start_ip": "10.2.0.50",
            "end_ip": "10.2.0.60"
        }
    )
    assert ip_group_resp.status_code == 200
    ip_group_id = ip_group_resp.json()["id"]
    
    # Try to create client with manual IP outside group range - should fail
    client_resp = await async_client.post(
        "/api/v1/clients",
        json={
            "name": "test-client-3-fail",
            "pool_id": pool_id,
            "ip_group_id": ip_group_id,
            "ip_address": "10.2.0.10"  # Outside group range
        }
    )
    assert client_resp.status_code == 400, "Should reject IP outside group range"
    assert "not in selected IP group range" in client_resp.json()["detail"]
    
    # Create client with manual IP inside group range - should succeed
    client_resp = await async_client.post(
        "/api/v1/clients",
        json={
            "name": "test-client-3-success",
            "pool_id": pool_id,
            "ip_group_id": ip_group_id,
            "ip_address": "10.2.0.55"  # Inside group range
        }
    )
    assert client_resp.status_code == 200
    allocated_ip = client_resp.json()["assigned_ips"][0]["ip_address"]
    assert allocated_ip == "10.2.0.55"
    
    print(f"✓ Manual IP validation against IP group working correctly")


@pytest.mark.asyncio
async def test_sequential_allocation_from_ip_group(async_client: AsyncClient, admin_user):
    """Test that multiple clients sequentially fill IP group range."""
    # Login as admin
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test_admin@test.com", "password": "testpass123"}
    )
    assert login_resp.status_code == 200
    
    # Create IP pool
    pool_resp = await async_client.post(
        "/api/v1/ip-pools",
        json={"cidr": "10.3.0.0/24", "description": "Test pool 4"}
    )
    assert pool_resp.status_code == 200
    pool_id = pool_resp.json()["id"]
    
    # Create small IP group: 10.3.0.20 - 10.3.0.22 (3 IPs)
    ip_group_resp = await async_client.post(
        "/api/v1/ip-groups",
        json={
            "name": "test-group-4",
            "description": "Small IP group",
            "pool_id": pool_id,
            "start_ip": "10.3.0.20",
            "end_ip": "10.3.0.22"
        }
    )
    assert ip_group_resp.status_code == 200
    ip_group_id = ip_group_resp.json()["id"]
    
    # Create 3 clients - should get 10.3.0.20, 10.3.0.21, 10.3.0.22
    allocated_ips = []
    for i in range(3):
        client_resp = await async_client.post(
            "/api/v1/clients",
            json={
                "name": f"test-client-4-{i}",
                "pool_id": pool_id,
                "ip_group_id": ip_group_id
            }
        )
        assert client_resp.status_code == 200
        ip = client_resp.json()["assigned_ips"][0]["ip_address"]
        allocated_ips.append(ip)
    
    # Verify sequential allocation
    assert allocated_ips == ["10.3.0.20", "10.3.0.21", "10.3.0.22"], \
        f"Expected sequential IPs from group, got {allocated_ips}"
    
    # Try to create 4th client - should fail (no more IPs in group)
    client_resp = await async_client.post(
        "/api/v1/clients",
        json={
            "name": "test-client-4-overflow",
            "pool_id": pool_id,
            "ip_group_id": ip_group_id
        }
    )
    assert client_resp.status_code == 409, "Should fail when IP group is exhausted"
    assert "No available IPs" in client_resp.json()["detail"]
    
    print(f"✓ Sequential allocation from IP group working correctly: {allocated_ips}")
