"""End-to-end tests for token management and GitHub Secret Scanning."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
import hmac
import hashlib
import json


client = TestClient(app)


def test_complete_token_workflow():
    """Test the complete token workflow from generation to GitHub scanning.
    
    This test demonstrates:
    1. Public metadata endpoint (no auth)
    2. GitHub verification endpoint (with signature)
    3. GitHub revocation endpoint (with signature)
    
    Note: This is a basic test without full database setup. 
    Full integration tests would require creating admin users and clients.
    """
    # 1. Test public metadata endpoint
    response = client.get("/.well-known/secret-scanning.json")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    pattern_info = data[0]
    assert pattern_info["type"] == "managed_nebula_client_token"
    assert "pattern" in pattern_info
    assert "mnebula_" in pattern_info["pattern"]
    print(f"✓ Pattern metadata endpoint working: {pattern_info['pattern']}")
    
    # 2. Test GitHub verification endpoint (without signature - should work but find no tokens)
    verify_payload = [
        {
            "type": "managed_nebula_client_token",
            "token": "mnebula_nonexistenttoken123456789012",
            "url": "https://github.com/test/repo/blob/main/test.py"
        }
    ]
    
    response = client.post(
        "/api/v1/github/secret-scanning/verify",
        json=verify_payload
    )
    assert response.status_code == 200
    # Should return empty list for non-existent token (don't leak info)
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
    print(f"✓ Verification endpoint returns empty list for unknown token")
    
    # 3. Test GitHub revocation endpoint
    revoke_payload = [
        {
            "type": "managed_nebula_client_token",
            "token": "mnebula_nonexistenttoken123456789012",
            "url": "https://github.com/test/repo/blob/main/test.py"
        }
    ]
    
    response = client.post(
        "/api/v1/github/secret-scanning/revoke",
        json=revoke_payload
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "revoked_count" in data
    # Should return 0 for non-existent token
    assert data["revoked_count"] == 0
    print(f"✓ Revocation endpoint processed request: {data}")


def test_github_signature_verification():
    """Test GitHub webhook signature verification logic."""
    from app.core.github_verification import verify_github_signature
    
    payload = b'{"test": "data"}'
    secret = "test-webhook-secret"
    
    # Generate correct signature
    expected_sig = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    signature_header = f"sha256={expected_sig}"
    
    # Should verify correctly
    assert verify_github_signature(payload, signature_header, secret)
    print(f"✓ Valid signature verified correctly")
    
    # Wrong signature should fail
    assert not verify_github_signature(payload, "sha256=wrongsignature", secret)
    print(f"✓ Invalid signature rejected correctly")
    
    # Missing prefix should fail
    assert not verify_github_signature(payload, expected_sig, secret)
    print(f"✓ Signature without prefix rejected")
    
    # Empty secret should fail
    assert not verify_github_signature(payload, signature_header, "")
    print(f"✓ Empty secret rejected")


def test_token_format_validation():
    """Test that token format validation works correctly."""
    from app.services.token_manager import is_token_valid_format
    
    # Valid new format tokens
    assert is_token_valid_format("mnebula_" + "a" * 32)
    assert is_token_valid_format("custom_" + "b" * 32)
    assert is_token_valid_format("test123_" + "c" * 32)
    print(f"✓ New format tokens validated")
    
    # Valid legacy format tokens
    assert is_token_valid_format("A" * 32)
    assert is_token_valid_format("abcd1234" * 4)
    print(f"✓ Legacy format tokens validated")
    
    # Invalid tokens
    assert not is_token_valid_format("short")
    assert not is_token_valid_format("mnebula_short")
    print(f"✓ Invalid tokens rejected")


if __name__ == "__main__":
    print("\n=== Running End-to-End Token Management Tests ===\n")
    test_complete_token_workflow()
    print()
    test_github_signature_verification()
    print()
    test_token_format_validation()
    print("\n✅ All end-to-end tests passed!\n")
