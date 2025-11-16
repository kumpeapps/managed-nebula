"""Tests for config_builder service - specifically punchy settings."""
from unittest.mock import Mock
from app.services.config_builder import build_nebula_config
import yaml


def test_punchy_disabled_by_default():
    """Test that punchy is not included when disabled in settings."""
    # Create mock client
    client = Mock()
    client.name = "test-client"
    client.is_lighthouse = False
    client.is_blocked = False
    client.firewall_rulesets = []
    
    # Create mock settings with punchy disabled
    settings = Mock()
    settings.punchy_enabled = False
    settings.lighthouse_port = 4242
    settings.lighthouse_hosts = "[]"
    
    config_yaml = build_nebula_config(
        client=client,
        client_ip_cidr="10.100.0.1/16",
        settings=settings,
        static_host_map={},
        lighthouse_host_ips=[]
    )
    
    config = yaml.safe_load(config_yaml)
    assert "punchy" not in config


def test_punchy_enabled_includes_all_settings():
    """Test that punchy includes punch, punch_back, and respond when enabled."""
    # Create mock client
    client = Mock()
    client.name = "test-client"
    client.is_lighthouse = False
    client.is_blocked = False
    client.firewall_rulesets = []
    
    # Create mock settings with punchy enabled
    settings = Mock()
    settings.punchy_enabled = True
    settings.lighthouse_port = 4242
    settings.lighthouse_hosts = "[]"
    
    config_yaml = build_nebula_config(
        client=client,
        client_ip_cidr="10.100.0.1/16",
        settings=settings,
        static_host_map={},
        lighthouse_host_ips=[]
    )
    
    config = yaml.safe_load(config_yaml)
    
    # Verify punchy block exists
    assert "punchy" in config
    
    # Verify all three settings are present and set to True
    assert config["punchy"]["punch"] is True
    assert config["punchy"]["punch_back"] is True
    assert config["punchy"]["respond"] is True


def test_punchy_settings_none():
    """Test that punchy is not included when settings is None."""
    # Create mock client
    client = Mock()
    client.name = "test-client"
    client.is_lighthouse = False
    client.is_blocked = False
    client.firewall_rulesets = []
    
    config_yaml = build_nebula_config(
        client=client,
        client_ip_cidr="10.100.0.1/16",
        settings=None,
        static_host_map={},
        lighthouse_host_ips=[]
    )
    
    config = yaml.safe_load(config_yaml)
    assert "punchy" not in config
