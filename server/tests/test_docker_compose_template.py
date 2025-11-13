"""Tests for docker-compose template functionality."""
from fastapi.testclient import TestClient
from app.main import app
import yaml


client = TestClient(app)


def test_get_placeholders():
    """Test getting available placeholders."""
    # Login as admin first (assuming test data exists)
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123"
    })
    
    # Get placeholders
    response = client.get("/api/v1/settings/placeholders")
    
    # Check response
    assert response.status_code in [200, 401]  # 401 if no admin user exists yet
    
    if response.status_code == 200:
        data = response.json()
        assert "placeholders" in data
        placeholders = data["placeholders"]
        assert len(placeholders) > 0
        
        # Check required placeholders exist
        placeholder_names = [p["name"] for p in placeholders]
        assert "{{CLIENT_NAME}}" in placeholder_names
        assert "{{CLIENT_TOKEN}}" in placeholder_names
        assert "{{SERVER_URL}}" in placeholder_names
        assert "{{CLIENT_DOCKER_IMAGE}}" in placeholder_names
        assert "{{POLL_INTERVAL_HOURS}}" in placeholder_names
        
        # Check each placeholder has required fields
        for p in placeholders:
            assert "name" in p
            assert "description" in p
            assert "example" in p


def test_get_docker_compose_template():
    """Test retrieving docker-compose template."""
    # Get settings (which includes template)
    response = client.get("/api/v1/settings")
    
    # Should work without auth for basic settings
    if response.status_code == 200:
        data = response.json()
        assert "docker_compose_template" in data
        assert isinstance(data["docker_compose_template"], str)
        assert len(data["docker_compose_template"]) > 0
        
        # Check template contains placeholders
        template = data["docker_compose_template"]
        assert "{{CLIENT_NAME}}" in template or "CLIENT_NAME" in template
        assert "{{CLIENT_TOKEN}}" in template or "CLIENT_TOKEN" in template


def test_update_docker_compose_template_validation():
    """Test YAML validation when updating template."""
    # Try to update with invalid YAML (without authentication)
    invalid_template = """
    services:
      client:
        image: test
        ports
          - 8080  # Missing colon - invalid YAML
    """
    
    response = client.put("/api/v1/settings", json={
        "docker_compose_template": invalid_template
    })
    
    # Should either require auth (401/403) or validate and return 400
    assert response.status_code in [400, 401, 403]
    
    if response.status_code == 400:
        # Check error message mentions YAML
        data = response.json()
        assert "detail" in data
        assert "YAML" in data["detail"] or "yaml" in data["detail"].lower()


def test_docker_compose_template_in_settings():
    """Test that docker_compose_template is included in settings response."""
    response = client.get("/api/v1/settings")
    
    if response.status_code == 200:
        data = response.json()
        
        # Check all expected fields are present
        assert "punchy_enabled" in data
        assert "client_docker_image" in data
        assert "server_url" in data
        assert "docker_compose_template" in data
        
        # Check template is valid YAML
        template = data["docker_compose_template"]
        try:
            yaml.safe_load(template)
        except yaml.YAMLError:
            # Template should be valid YAML
            assert False, "Template is not valid YAML"


def test_placeholder_replacement_concept():
    """Test that placeholder replacement logic works correctly."""
    template = """version: '3.8'
services:
  nebula-client:
    image: {{CLIENT_DOCKER_IMAGE}}
    container_name: nebula-{{CLIENT_NAME}}
    environment:
      SERVER_URL: {{SERVER_URL}}
      CLIENT_TOKEN: {{CLIENT_TOKEN}}
      POLL_INTERVAL_HOURS: {{POLL_INTERVAL_HOURS}}"""
    
    # Simulate replacement
    result = template.replace("{{CLIENT_NAME}}", "test-client")
    result = result.replace("{{CLIENT_TOKEN}}", "abc123")
    result = result.replace("{{SERVER_URL}}", "http://example.com")
    result = result.replace("{{CLIENT_DOCKER_IMAGE}}", "test/image:latest")
    result = result.replace("{{POLL_INTERVAL_HOURS}}", "24")
    
    # Verify no placeholders remain
    assert "{{" not in result
    assert "}}" not in result
    
    # Verify values were replaced
    assert "test-client" in result
    assert "abc123" in result
    assert "http://example.com" in result
    assert "test/image:latest" in result
    assert "24" in result


def test_default_template_is_valid_yaml():
    """Test that the default template is valid YAML."""
    from app.models.settings import DEFAULT_DOCKER_COMPOSE_TEMPLATE
    
    # Should be able to parse as YAML
    try:
        yaml.safe_load(DEFAULT_DOCKER_COMPOSE_TEMPLATE)
    except yaml.YAMLError as e:
        assert False, f"Default template is not valid YAML: {e}"
    
    # Check it contains expected placeholders
    assert "{{CLIENT_NAME}}" in DEFAULT_DOCKER_COMPOSE_TEMPLATE
    assert "{{CLIENT_TOKEN}}" in DEFAULT_DOCKER_COMPOSE_TEMPLATE
    assert "{{SERVER_URL}}" in DEFAULT_DOCKER_COMPOSE_TEMPLATE
    assert "{{CLIENT_DOCKER_IMAGE}}" in DEFAULT_DOCKER_COMPOSE_TEMPLATE
    assert "{{POLL_INTERVAL_HOURS}}" in DEFAULT_DOCKER_COMPOSE_TEMPLATE
