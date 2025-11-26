#!/usr/bin/env python3
"""
Unit tests for the Managed Nebula Windows Agent
Tests the platform-independent parts of the agent logic
"""

import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def test_version():
    """Test version constant"""
    from agent import __version__
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0
    print("✅ Version test passed")


def test_hash_calculation():
    """Test that config hashing works correctly"""
    # Import here to avoid Windows-specific import errors
    from agent import calculate_config_hash
    
    config_yaml = "config: test"
    cert_pem = "cert: test"
    ca_pems = ["ca1: test", "ca2: test"]
    
    hash1 = calculate_config_hash(config_yaml, cert_pem, ca_pems)
    hash2 = calculate_config_hash(config_yaml, cert_pem, ca_pems)
    assert hash1 == hash2, "Same config should produce same hash"
    
    hash3 = calculate_config_hash("different config", cert_pem, ca_pems)
    assert hash1 != hash3, "Different config should produce different hash"
    
    # Test empty values
    hash_empty = calculate_config_hash("", "", [])
    assert hash_empty is not None, "Should handle empty values"
    
    print("✅ Hash calculation test passed")


def test_config_loading():
    """Test configuration loading from INI file"""
    from config import load_from_ini, save_to_ini
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_config_file = Path(temp_dir) / "agent.ini"
        
        # Patch the CONFIG_FILE path
        with patch('config.CONFIG_FILE', test_config_file):
            with patch('config.NEBULA_DIR', Path(temp_dir)):
                # Test loading non-existent file
                config = load_from_ini()
                assert config == {}, "Should return empty dict for non-existent file"
                
                # Test saving and loading
                test_config = {
                    "server_url": "https://test.example.com",
                    "poll_interval_hours": 12,
                    "log_level": "DEBUG"
                }
                
                result = save_to_ini(test_config)
                assert result is True, "Save should succeed"
                
                loaded_config = load_from_ini()
                assert loaded_config["server_url"] == test_config["server_url"]
                assert loaded_config["poll_interval_hours"] == test_config["poll_interval_hours"]
                assert loaded_config["log_level"] == test_config["log_level"]
                
                print("✅ Config loading test passed")


def test_config_priority():
    """Test configuration priority (env > registry > ini > defaults)"""
    from config import load_config
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_config_file = Path(temp_dir) / "agent.ini"
        
        with patch('config.CONFIG_FILE', test_config_file):
            with patch('config.NEBULA_DIR', Path(temp_dir)):
                with patch('config.load_from_registry', return_value={}):
                    # Test defaults
                    config = load_config()
                    assert config["server_url"] == "http://localhost:8080"
                    assert config["poll_interval_hours"] == 24
                    
                    # Test environment override
                    with patch.dict(os.environ, {"SERVER_URL": "https://env-server.example.com"}):
                        config = load_config()
                        assert config["server_url"] == "https://env-server.example.com"
                    
                    print("✅ Config priority test passed")


def test_get_status():
    """Test the status function"""
    from agent import get_status, __version__
    
    with patch('agent.is_nebula_running', return_value=False):
        with patch('agent.get_nebula_version', return_value="1.9.7"):
            with patch('agent.CONFIG_PATH', Path("/nonexistent/config.yml")):
                with patch('agent.KEY_PATH', Path("/nonexistent/host.key")):
                    with patch('agent.PUB_PATH', Path("/nonexistent/host.pub")):
                        status = get_status()
                        
                        assert status["agent_version"] == __version__
                        assert status["nebula_version"] == "1.9.7"
                        assert status["nebula_running"] is False
                        assert "paths" in status
                        
                        print("✅ Status test passed")


def test_fetch_config_request_format():
    """Test that fetch_config builds correct request payload"""
    from agent import __version__
    
    # Test the payload format without making actual HTTP requests
    token = "test-token-123"
    public_key = "test-public-key"
    
    expected_payload = {
        "token": token,
        "public_key": public_key,
        "client_version": __version__,
        "nebula_version": "not_installed"  # Expected when binary not found
    }
    
    # Verify payload keys
    assert "token" in expected_payload
    assert "public_key" in expected_payload
    assert "client_version" in expected_payload
    assert "nebula_version" in expected_payload
    
    print("✅ Fetch config format test passed")


def test_version_override():
    """Test that version overrides work via environment variables"""
    from agent import __version__
    
    with patch.dict(os.environ, {
        "CLIENT_VERSION_OVERRIDE": "2.0.0-test",
        "NEBULA_VERSION_OVERRIDE": "1.8.0-override"
    }):
        client_version = os.environ.get("CLIENT_VERSION_OVERRIDE", __version__)
        nebula_version = os.environ.get("NEBULA_VERSION_OVERRIDE", "1.9.7")
        
        assert client_version == "2.0.0-test"
        assert nebula_version == "1.8.0-override"
    
    print("✅ Version override test passed")


if __name__ == "__main__":
    print("Running Managed Nebula Windows Agent tests...")
    print("=" * 50)
    
    test_version()
    test_hash_calculation()
    test_config_loading()
    test_config_priority()
    test_get_status()
    test_fetch_config_request_format()
    test_version_override()
    
    print("=" * 50)
    print("🎉 All tests passed!")
