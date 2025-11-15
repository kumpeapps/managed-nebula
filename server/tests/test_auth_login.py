import os
from fastapi.testclient import TestClient
from app.main import app


def test_login_and_me_with_seed_admin():
    client = TestClient(app)
    email = os.getenv("TEST_ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("TEST_ADMIN_PASSWORD", "TestAdmin123!")

    # Login with seeded credentials
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == email

    # Session cookie should be present and subsequent authenticated call should succeed
    r2 = client.get("/api/v1/auth/me")
    assert r2.status_code == 200, r2.text
    me = r2.json()
    assert me["email"] == email
