"""Tests for version status endpoint."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
class TestVersionStatusEndpoint:
    """Tests for /api/v1/version-status endpoint."""
    
    def test_version_status_requires_auth(self):
        """Test that version-status endpoint requires authentication."""
        response = client.get("/api/v1/version-status")
        # Should redirect or return 401 if not authenticated
        assert response.status_code in [401, 307, 403]
    
    @pytest.mark.skip(reason="Requires authenticated session - manual test")
    def test_version_status_returns_data(self):
        """Test that version-status endpoint returns expected data structure."""
        # This would need to be tested with an authenticated session
        # For now, we test the endpoint exists and requires auth
        pass
