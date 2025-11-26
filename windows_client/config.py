"""
Managed Nebula Windows Configuration Manager
Handles reading/writing configuration from registry and INI files
"""

import configparser
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("NebulaAgent")

# Windows-specific paths
PROGRAM_DATA = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData"))
NEBULA_DIR = PROGRAM_DATA / "Nebula"
CONFIG_FILE = NEBULA_DIR / "agent.ini"

# Registry path for configuration
REGISTRY_KEY = r"SOFTWARE\ManagedNebula"


def load_from_registry() -> Dict[str, Any]:
    """Load configuration from Windows Registry"""
    config = {}
    
    try:
        import winreg
        
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                REGISTRY_KEY,
                0,
                winreg.KEY_READ
            )
            
            # Read all values
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    config[name.lower()] = value
                    i += 1
                except OSError:
                    break
            
            winreg.CloseKey(key)
        except FileNotFoundError:
            logger.debug("Registry key not found: %s", REGISTRY_KEY)
    except ImportError:
        logger.warning("winreg not available (not on Windows)")
    
    return config


def save_to_registry(config: Dict[str, Any]) -> bool:
    """Save configuration to Windows Registry"""
    try:
        import winreg
        
        # Create or open key
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, REGISTRY_KEY)
        
        for name, value in config.items():
            if isinstance(value, int):
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
            elif isinstance(value, str):
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        
        winreg.CloseKey(key)
        return True
    except ImportError:
        logger.warning("winreg not available (not on Windows)")
        return False
    except PermissionError:
        logger.error("Permission denied writing to registry")
        return False
    except Exception as e:
        logger.error("Failed to write registry: %s", e)
        return False


def load_from_ini() -> Dict[str, Any]:
    """Load configuration from INI file"""
    config = {}
    
    if not CONFIG_FILE.exists():
        return config
    
    try:
        parser = configparser.ConfigParser()
        parser.read(CONFIG_FILE)
        
        if "agent" in parser:
            for key, value in parser["agent"].items():
                # Try to convert to appropriate type
                if value.lower() in ("true", "false"):
                    config[key] = value.lower() == "true"
                elif value.isdigit():
                    config[key] = int(value)
                else:
                    config[key] = value
    except Exception as e:
        logger.error("Failed to read INI file: %s", e)
    
    return config


def save_to_ini(config: Dict[str, Any]) -> bool:
    """Save configuration to INI file"""
    try:
        NEBULA_DIR.mkdir(parents=True, exist_ok=True)
        
        parser = configparser.ConfigParser()
        parser["agent"] = {k: str(v) for k, v in config.items()}
        
        with open(CONFIG_FILE, "w") as f:
            parser.write(f)
        
        return True
    except Exception as e:
        logger.error("Failed to write INI file: %s", e)
        return False


def load_config() -> Dict[str, Any]:
    """
    Load configuration from all sources.
    Priority: Environment variables > Registry > INI file > Defaults
    """
    defaults = {
        "server_url": "http://localhost:8080",
        "poll_interval_hours": 24,
        "log_level": "INFO",
        "auto_start_nebula": True,
        "allow_self_signed_cert": False,
    }
    
    # Start with defaults
    config = defaults.copy()
    
    # Load from INI file (lowest priority after defaults)
    ini_config = load_from_ini()
    config.update(ini_config)
    
    # Load from registry (higher priority)
    reg_config = load_from_registry()
    config.update(reg_config)
    
    # Environment variables have highest priority
    env_mappings = {
        "SERVER_URL": "server_url",
        "CLIENT_TOKEN": "client_token",
        "POLL_INTERVAL_HOURS": "poll_interval_hours",
        "LOG_LEVEL": "log_level",
        "AUTO_START_NEBULA": "auto_start_nebula",
        "ALLOW_SELF_SIGNED_CERT": "allow_self_signed_cert",
    }
    
    for env_name, config_name in env_mappings.items():
        env_value = os.environ.get(env_name)
        if env_value:
            # Convert to appropriate type
            if config_name in ("poll_interval_hours",):
                config[config_name] = int(env_value)
            elif config_name in ("auto_start_nebula", "allow_self_signed_cert"):
                config[config_name] = env_value.lower() in ("true", "1", "yes")
            else:
                config[config_name] = env_value
    
    return config


def save_config(config: Dict[str, Any], use_registry: bool = False) -> bool:
    """
    Save configuration.
    By default, saves to INI file. If use_registry is True, also saves to registry.
    """
    success = save_to_ini(config)
    
    if use_registry:
        reg_success = save_to_registry(config)
        success = success and reg_success
    
    return success


def get_client_token() -> Optional[str]:
    """Get client token from configuration sources"""
    # Try environment first
    token = os.environ.get("CLIENT_TOKEN")
    if token:
        return token
    
    # Try registry
    reg_config = load_from_registry()
    if "clienttoken" in reg_config:
        return reg_config["clienttoken"]
    if "client_token" in reg_config:
        return reg_config["client_token"]
    
    # Try INI file
    ini_config = load_from_ini()
    if "client_token" in ini_config:
        return ini_config["client_token"]
    
    return None


def set_client_token(token: str, use_registry: bool = True) -> bool:
    """Save client token to configuration"""
    config = load_from_ini()
    config["client_token"] = token
    
    success = save_to_ini(config)
    
    if use_registry:
        # Save token to registry for Windows Service access
        reg_success = save_to_registry({"ClientToken": token})
        success = success and reg_success
    
    return success


def create_default_config() -> bool:
    """Create default configuration file if it doesn't exist"""
    if CONFIG_FILE.exists():
        return True
    
    default_config = {
        "server_url": "http://localhost:8080",
        "poll_interval_hours": 24,
        "log_level": "INFO",
        "auto_start_nebula": True,
    }
    
    return save_to_ini(default_config)


# Example agent.ini file content
EXAMPLE_INI = """
# Managed Nebula Agent Configuration
# Location: C:\\ProgramData\\Nebula\\agent.ini

[agent]
# Server URL for the Managed Nebula API
server_url = https://your-server.example.com:8080

# Client authentication token (obtain from Managed Nebula web interface)
client_token = your-client-token-here

# How often to check for configuration updates (in hours)
poll_interval_hours = 24

# Logging level: DEBUG, INFO, WARNING, ERROR
log_level = INFO

# Automatically start Nebula when agent runs
auto_start_nebula = true
"""


if __name__ == "__main__":
    # Test configuration loading
    import json
    print("Current configuration:")
    config = load_config()
    print(json.dumps(config, indent=2))
