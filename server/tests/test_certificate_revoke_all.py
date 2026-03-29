"""
Test POST /api/v1/clients/{client_id}/certificates/revoke endpoint.

Tests bulk certificate revocation functionality.
"""
import pytest
import shutil
from datetime import datetime, timedelta
from sqlalchemy import select
from app.models.client import ClientCertificate, RevokedCertificate


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not installed")
@pytest.mark.asyncio
async def test_revoke_all_certificates_success(async_client, async_session, auth_headers):
    """Test revoking all certificates for a client."""
    # Create CA
    ca_response = await async_client.post(
        "/api/v1/ca/create",
        json={
            "name": "Test CA",
            "duration_days": 365,
            "version": "v1"
        },
        cookies=auth_headers["cookies"]
    )
    assert ca_response.status_code == 200
    
    # Create client
    client_response = await async_client.post(
        "/api/v1/clients",
        json={
            "name": "test-client",
            "is_lighthouse": False,
            "group_ids": [],
            "pool_id": None
        },
        cookies=auth_headers["cookies"]
    )
    assert client_response.status_code == 200
    client_id = client_response.json()["id"]
    
    # Wait for certificate to be created
    await async_session.commit()
    
    # Check how many certificates exist
    cert_result = await async_session.execute(
        select(ClientCertificate).where(
            ClientCertificate.client_id == client_id,
            ClientCertificate.revoked == False
        )
    )
    certs_before = cert_result.scalars().all()
    assert len(certs_before) > 0, "Client should have at least one certificate"
    
    # Manually create additional certificates for testing
    new_cert = ClientCertificate(
        client_id=client_id,
        pem_cert="FAKE_CERT_2",
        fingerprint="abc123def456abc123def456abc123def456abc123def456abc123def456abcd",
        not_before=datetime.utcnow(),
        not_after=datetime.utcnow() + timedelta(days=180),
        issued_for_ip_cidr="10.0.0.2/24",
        revoked=False
    )
    async_session.add(new_cert)
    await async_session.commit()
    
    # Store the full fingerprint for later verification
    test_cert_fingerprint = "abc123def456abc123def456abc123def456abc123def456abc123def456abcd"
    
    # Verify we now have multiple certificates
    cert_result = await async_session.execute(
        select(ClientCertificate).where(
            ClientCertificate.client_id == client_id,
            ClientCertificate.revoked == False
        )
    )
    certs_before = cert_result.scalars().all()
    initial_cert_count = len(certs_before)
    assert initial_cert_count >= 2, f"Should have at least 2 certificates, got {initial_cert_count}"
    
    # Revoke all certificates
    revoke_response = await async_client.post(
        f"/api/v1/clients/{client_id}/certificates/revoke",
        json={
            "reason": "Testing bulk revocation",
            "issue_new": False
        },
        cookies=auth_headers["cookies"]
    )
    assert revoke_response.status_code == 200
    revoke_data = revoke_response.json()
    assert revoke_data["status"] == "revoked"
    assert revoke_data["revoked_count"] == initial_cert_count
    
    # Strengthen fingerprint format checks
    revoked_fingerprints = revoke_data["revoked_fingerprints"]
    assert isinstance(revoked_fingerprints, list)
    assert len(revoked_fingerprints) == initial_cert_count
    assert all(isinstance(fp, str) for fp in revoked_fingerprints)
    # API truncates fingerprints with fp[:12] + "..."
    assert all(fp.endswith("...") for fp in revoked_fingerprints), "All fingerprints should end with '...'"
    assert all(len(fp) == 15 for fp in revoked_fingerprints), "All fingerprints should be 15 chars (12 + '...')"
    # Verify at least one known fingerprint appears truncated correctly
    assert test_cert_fingerprint[:12] + "..." in revoked_fingerprints, \
        f"Expected truncated fingerprint {test_cert_fingerprint[:12]}... in response"
    
    assert revoke_data["new_certificate_issued"] is False
    
    # Verify all certificates are now revoked
    await async_session.commit()
    cert_result = await async_session.execute(
        select(ClientCertificate).where(
            ClientCertificate.client_id == client_id,
            ClientCertificate.revoked == False
        )
    )
    active_certs = cert_result.scalars().all()
    assert len(active_certs) == 0, "All certificates should be revoked"
    
    # Verify certificates were added to RevokedCertificate table
    revoked_result = await async_session.execute(
        select(RevokedCertificate).where(
            RevokedCertificate.client_id == client_id
        )
    )
    revoked_certs = revoked_result.scalars().all()
    assert len(revoked_certs) == initial_cert_count


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not installed")
@pytest.mark.asyncio
async def test_revoke_all_with_new_certificate(async_client, async_session, auth_headers):
    """Test revoking all certificates and issuing a new one."""
    # Create CA
    ca_response = await async_client.post(
        "/api/v1/ca/create",
        json={
            "name": "Test CA 2",
            "duration_days": 365,
            "version": "v1"
        },
        cookies=auth_headers["cookies"]
    )
    assert ca_response.status_code == 200
    
    # Create client
    client_response = await async_client.post(
        "/api/v1/clients",
        json={
            "name": "test-client-2",
            "is_lighthouse": False,
            "group_ids": [],
            "pool_id": None
        },
        cookies=auth_headers["cookies"]
    )
    assert client_response.status_code == 200
    client_id = client_response.json()["id"]
    
    await async_session.commit()
    
    # Get certificate count before revocation
    cert_result = await async_session.execute(
        select(ClientCertificate).where(
            ClientCertificate.client_id == client_id,
            ClientCertificate.revoked == False
        )
    )
    certs_before = len(cert_result.scalars().all())
    
    # Revoke all certificates AND issue new one
    revoke_response = await async_client.post(
        f"/api/v1/clients/{client_id}/certificates/revoke",
        json={
            "reason": "Scheduled rotation",
            "issue_new": True
        },
        cookies=auth_headers["cookies"]
    )
    assert revoke_response.status_code == 200
    revoke_data = revoke_response.json()
    assert revoke_data["status"] == "revoked"
    assert revoke_data["revoked_count"] == certs_before
    assert revoke_data["new_certificate_issued"] is True
    assert "issued new certificate" in revoke_data["message"].lower()
    
    # Verify we have exactly 1 active certificate (the new one)
    await async_session.commit()
    cert_result = await async_session.execute(
        select(ClientCertificate).where(
            ClientCertificate.client_id == client_id,
            ClientCertificate.revoked == False
        )
    )
    active_certs = cert_result.scalars().all()
    assert len(active_certs) == 1, "Should have exactly 1 new certificate"


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not installed")
@pytest.mark.asyncio
async def test_revoke_all_no_active_certificates(async_client, async_session, auth_headers):
    """Test revoking when there are no active certificates."""
    # Create CA
    ca_response = await async_client.post(
        "/api/v1/ca/create",
        json={
            "name": "Test CA 3",
            "duration_days": 365,
            "version": "v1"
        },
        cookies=auth_headers["cookies"]
    )
    assert ca_response.status_code == 200
    
    # Create client
    client_response = await async_client.post(
        "/api/v1/clients",
        json={
            "name": "test-client-3",
            "is_lighthouse": False,
            "group_ids": [],
            "pool_id": None
        },
        cookies=auth_headers["cookies"]
    )
    assert client_response.status_code == 200
    client_id = client_response.json()["id"]
    
    await async_session.commit()
    
    # Revoke all certificates first time
    revoke_response = await async_client.post(
        f"/api/v1/clients/{client_id}/certificates/revoke",
        json={
            "reason": "First revocation",
            "issue_new": False
        },
        cookies=auth_headers["cookies"]
    )
    assert revoke_response.status_code == 200
    
    # Try to revoke again (should fail - no active certificates)
    revoke_response2 = await async_client.post(
        f"/api/v1/clients/{client_id}/certificates/revoke",
        json={
            "reason": "Second revocation",
            "issue_new": False
        },
        cookies=auth_headers["cookies"]
    )
    assert revoke_response2.status_code == 400
    assert "no active certificates" in revoke_response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_revoke_all_client_not_found(async_client, auth_headers):
    """Test revoking certificates for non-existent client."""
    # Try to revoke certificates for non-existent client
    revoke_response = await async_client.post(
        "/api/v1/clients/99999/certificates/revoke",
        json={
            "reason": "Test",
            "issue_new": False
        },
        cookies=auth_headers["cookies"]
    )
    assert revoke_response.status_code == 404
    assert "not found" in revoke_response.json()["detail"].lower()


@pytest.mark.skipif(shutil.which("nebula-cert") is None, reason="nebula-cert not installed")
@pytest.mark.asyncio
async def test_revoke_all_certificates_integrity_error_retry(async_client, async_session, auth_headers):
    """Test revocation is idempotent when RevokedCertificate row already exists (IntegrityError retry path)."""
    # Create CA
    ca_response = await async_client.post(
        "/api/v1/ca/create",
        json={
            "name": "Retry CA",
            "duration_days": 365,
            "version": "v1"
        },
        cookies=auth_headers["cookies"]
    )
    assert ca_response.status_code == 200
    ca_data = ca_response.json()
    ca_id = ca_data["id"]

    # Create client
    client_response = await async_client.post(
        "/api/v1/clients",
        json={
            "name": "retry-client",
            "is_lighthouse": False,
            "group_ids": [],
            "pool_id": None
        },
        cookies=auth_headers["cookies"]
    )
    assert client_response.status_code == 200
    client_id = client_response.json()["id"]
    
    await async_session.commit()

    # Manually create a second certificate for this client
    second_cert = ClientCertificate(
        client_id=client_id,
        pem_cert="FAKE_CERT_RETRY",
        fingerprint="retry123456retry123456retry123456retry123456retry123456retry123456",
        not_before=datetime.utcnow(),
        not_after=datetime.utcnow() + timedelta(days=180),
        issued_for_ip_cidr="10.0.0.3/24",
        revoked=False
    )
    async_session.add(second_cert)
    await async_session.commit()

    # Load certificates from DB so we can pre-create a conflicting RevokedCertificate
    result = await async_session.execute(
        select(ClientCertificate).where(
            ClientCertificate.client_id == client_id,
            ClientCertificate.revoked == False
        ).order_by(ClientCertificate.id)
    )
    client_certs = result.scalars().all()
    assert len(client_certs) >= 2, f"Should have at least 2 certificates, got {len(client_certs)}"

    # Pre-insert a RevokedCertificate for the first certificate fingerprint
    first_fingerprint = client_certs[0].fingerprint
    async_session.add(
        RevokedCertificate(
            fingerprint=first_fingerprint,
            client_id=client_id,
            client_name="retry-client",
            not_after=client_certs[0].not_after,
            revoked_at=datetime.utcnow(),
            revoked_reason="pre_existing",
            revoked_by_user_id=1
        )
    )
    await async_session.commit()

    # Now call the bulk revoke endpoint; the service should hit IntegrityError on insert
    # and then retry inserting only missing fingerprints.
    revoke_response = await async_client.post(
        f"/api/v1/clients/{client_id}/certificates/revoke",
        json={
            "reason": "Testing retry path",
            "issue_new": False
        },
        cookies=auth_headers["cookies"]
    )
    assert revoke_response.status_code == 200
    revoke_data = revoke_response.json()
    assert revoke_data["status"] == "revoked"
    assert revoke_data["revoked_count"] == len(client_certs)

    # All client certificates should now be marked revoked.
    await async_session.commit()
    result = await async_session.execute(
        select(ClientCertificate)
        .where(ClientCertificate.client_id == client_id)
        .order_by(ClientCertificate.id)
    )
    updated_certs = result.scalars().all()
    assert len(updated_certs) >= 2
    assert all(cert.revoked is True for cert in updated_certs), "All certificates should be marked revoked"
    assert all(cert.revoked_at is not None for cert in updated_certs), "All certificates should have revoked_at timestamp"

    # There should be exactly one RevokedCertificate per certificate fingerprint
    # (no duplicates, even for the pre-existing fingerprint).
    result = await async_session.execute(
        select(RevokedCertificate)
        .where(RevokedCertificate.fingerprint.in_([c.fingerprint for c in updated_certs if c.fingerprint]))
        .order_by(RevokedCertificate.fingerprint)
    )
    revoked_rows = result.scalars().all()
    assert len(revoked_rows) == len([c for c in updated_certs if c.fingerprint]), \
        "Should have one RevokedCertificate row per certificate with fingerprint"
    revoked_fingerprints_set = {row.fingerprint for row in revoked_rows}
    expected_fingerprints = {c.fingerprint for c in updated_certs if c.fingerprint}
    assert revoked_fingerprints_set == expected_fingerprints, \
        "All certificate fingerprints should be in RevokedCertificate table exactly once"

