"""Tests for token generation, re-issuance, and GitHub Secret Scanning integration."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.token_manager import (
    generate_client_token,
    validate_token_prefix,
    is_token_valid_format,
    get_token_preview
)
from app.core.github_verification import verify_github_signature, get_github_pattern_regex
import hmac
import hashlib


client = TestClient(app)


# ============ Token Manager Tests ============

def test_generate_client_token_default_prefix():
    """Test token generation with default prefix."""
    token = generate_client_token("mnebula_")
    assert token.startswith("mnebula_")
    assert len(token) == len("mnebula_") + 32
    # Should be lowercase alphanumeric only
    suffix = token[len("mnebula_"):]
    assert suffix.isalnum() and suffix.islower()


def test_generate_client_token_custom_prefix():
    """Test token generation with custom prefix."""
    token = generate_client_token("custom_")
    assert token.startswith("custom_")
    assert len(token) == len("custom_") + 32


def test_generate_client_token_invalid_prefix():
    """Test that invalid prefixes raise ValueError."""
    # Too short
    with pytest.raises(ValueError):
        generate_client_token("ab")
    
    # Too long
    with pytest.raises(ValueError):
        generate_client_token("a" * 21)
    
    # Invalid characters
    with pytest.raises(ValueError):
        generate_client_token("test-prefix")
    
    with pytest.raises(ValueError):
        generate_client_token("test prefix")


def test_validate_token_prefix():
    """Test token prefix validation."""
    assert validate_token_prefix("mnebula_")
    assert validate_token_prefix("test123_")
    assert validate_token_prefix("abc")
    assert validate_token_prefix("a" * 20)
    
    assert not validate_token_prefix("ab")  # Too short
    assert not validate_token_prefix("a" * 21)  # Too long
    assert not validate_token_prefix("test-prefix")  # Invalid char
    assert not validate_token_prefix("")  # Empty


def test_is_token_valid_format():
    """Test token format validation."""
    # New format with prefix
    assert is_token_valid_format("mnebula_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6")
    assert is_token_valid_format("custom_" + "a" * 32)
    
    # Legacy format (backward compatibility)
    assert is_token_valid_format("A" * 32)
    assert is_token_valid_format("a1B2c3D4" * 4)
    
    # Invalid formats
    assert not is_token_valid_format("short")
    assert not is_token_valid_format("mnebula_short")


def test_get_token_preview():
    """Test token preview generation."""
    token = "mnebula_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    preview = get_token_preview(token, 12)
    assert preview == "mnebula_a1b2"
    assert len(preview) == 12


# ============ GitHub Verification Tests ============

def test_verify_github_signature_valid():
    """Test GitHub webhook signature verification with valid signature."""
    payload = b'{"token": "test"}'
    secret = "my-webhook-secret"
    
    # Compute correct signature
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    signature_header = f"sha256={expected}"
    
    assert verify_github_signature(payload, signature_header, secret)


def test_verify_github_signature_invalid():
    """Test GitHub webhook signature verification with invalid signature."""
    payload = b'{"token": "test"}'
    secret = "my-webhook-secret"
    wrong_signature = "sha256=wrongsignature"
    
    assert not verify_github_signature(payload, wrong_signature, secret)


def test_verify_github_signature_no_prefix():
    """Test signature verification fails without sha256= prefix."""
    payload = b'{"token": "test"}'
    secret = "my-webhook-secret"
    
    assert not verify_github_signature(payload, "invalid", secret)
    assert not verify_github_signature(payload, "", secret)


def test_verify_github_signature_no_secret():
    """Test signature verification fails when no secret is configured."""
    payload = b'{"token": "test"}'
    signature = "sha256=something"
    
    assert not verify_github_signature(payload, signature, "")
    assert not verify_github_signature(payload, signature, None)


def test_get_github_pattern_regex():
    """Test GitHub secret scanning pattern generation."""
    pattern = get_github_pattern_regex("mnebula_")
    assert pattern == "mnebula_[a-z0-9]{32}"
    
    pattern = get_github_pattern_regex("custom_")
    assert pattern == "custom_[a-z0-9]{32}"


# ============ API Integration Tests ============

def test_github_secret_scanning_metadata_endpoint():
    """Test the public metadata endpoint for GitHub Secret Scanning."""
    response = client.get("/.well-known/secret-scanning.json")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    pattern = data[0]
    assert pattern["type"] == "managed_nebula_client_token"
    assert "pattern" in pattern
    assert "description" in pattern
    assert "mnebula_" in pattern["pattern"]


def test_token_prefix_settings_without_auth():
    """Test that token prefix endpoints require authentication."""
    response = client.get("/api/v1/settings/token-prefix")
    assert response.status_code == 401


def test_github_webhook_secret_settings_without_auth():
    """Test that webhook secret endpoints require authentication."""
    response = client.get("/api/v1/settings/github-webhook-secret")
    assert response.status_code == 401


# Note: Full integration tests with authentication would require setting up
# a test database, creating admin users, and managing sessions. These tests
# verify the basic functionality of the utility functions and public endpoints.
