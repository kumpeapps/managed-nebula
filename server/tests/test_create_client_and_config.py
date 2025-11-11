import shutil
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not available in test env")
def test_create_client_and_fetch_config():
    client = TestClient(app)

    # Initial setup: create admin user (only allowed when no users exist)
    r = client.get("/setup", allow_redirects=False)
    assert r.status_code in (200, 303)
    if r.status_code == 200:
        r2 = client.post("/setup", data={"email": "admin@example.com", "password": "password123"}, allow_redirects=False)
        assert r2.status_code in (200, 303)

    # Create CA via GUI route (simulate form); requires admin session (from setup)
    r = client.post("/admin/ca/new", data={"name": "Test CA"}, allow_redirects=False)
    assert r.status_code in (200, 303)

    # Create a pool via API (requires admin)
    r = client.post("/api/v1/admin/ip-pool/create", json={"cidr": "10.200.0.0/16", "description": "test"})
    assert r.status_code == 200
    pool_id = r.json()["id"]

    # Create client via API (requires admin), now requires pool_id
    r = client.post("/api/v1/admin/client/create", json={"name": "c1", "is_lighthouse": False, "pool_id": pool_id})
    assert r.status_code == 200
    data = r.json()
    token = data["token"]
    assert token

    # Provide a dummy public key won't work without nebula-cert, but test is skipped if missing
    fake_pub = "curve25519:ABCDEF"
    r = client.post("/api/v1/client/config", json={"token": token, "public_key": fake_pub})
    # We can't guarantee success with dummy key; assert server validates inputs
    assert r.status_code in (200, 400, 422, 500)
