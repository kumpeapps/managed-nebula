"""
Managed Nebula Windows Agent
Main agent logic for fetching configuration and managing Nebula daemon on Windows
"""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import httpx

__version__ = "1.0.0"

# Windows-specific paths
PROGRAM_DATA = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData"))
NEBULA_DIR = PROGRAM_DATA / "Nebula"
CONFIG_PATH = NEBULA_DIR / "config.yml"
KEY_PATH = NEBULA_DIR / "host.key"
PUB_PATH = NEBULA_DIR / "host.pub"
CERT_PATH = NEBULA_DIR / "host.crt"
CA_PATH = NEBULA_DIR / "ca.crt"
LOG_DIR = NEBULA_DIR / "logs"
AGENT_LOG = LOG_DIR / "agent.log"
NEBULA_BIN = NEBULA_DIR / "nebula.exe"
NEBULA_CERT_BIN = NEBULA_DIR / "nebula-cert.exe"
WINTUN_DLL = NEBULA_DIR / "wintun.dll"
# Nebula also looks for wintun.dll in this nested path structure
WINTUN_DLL_NESTED = NEBULA_DIR / "dist" / "windows" / "wintun" / "bin" / "amd64" / "wintun.dll"

# Metrics and cache files
METRICS_FILE = NEBULA_DIR / "metrics.json"
CACHED_CONFIG_FILE = NEBULA_DIR / "cached_config.json"

# Configuration with environment variable defaults
PROCESS_CHECK_INTERVAL = int(os.getenv("PROCESS_CHECK_INTERVAL", "10"))  # seconds
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))  # seconds
CONFIG_FETCH_TIMEOUT = int(os.getenv("CONFIG_FETCH_TIMEOUT", "30"))  # seconds
MAX_RESTART_ATTEMPTS = int(os.getenv("MAX_RESTART_ATTEMPTS", "5"))
MAX_FETCH_RETRIES = int(os.getenv("MAX_FETCH_RETRIES", "5"))
POST_RESTART_WAIT = int(os.getenv("POST_RESTART_WAIT", "10"))  # seconds
RESTART_INIT_TIMEOUT = int(os.getenv("RESTART_INIT_TIMEOUT", "30"))  # seconds


# Metrics tracking class
class Metrics:
    def __init__(self, logger=None):
        self.crash_count = 0
        self.disconnect_count = 0
        self.restart_count = 0
        self.config_fetch_failures = 0
        self.last_crash_time = None
        self.last_successful_restart = None
        self.consecutive_failures = 0
        self.logger = logger
        
    def to_dict(self):
        return {
            "crash_count": self.crash_count,
            "disconnect_count": self.disconnect_count,
            "restart_count": self.restart_count,
            "config_fetch_failures": self.config_fetch_failures,
            "last_crash_time": self.last_crash_time.isoformat() if self.last_crash_time else None,
            "last_successful_restart": self.last_successful_restart.isoformat() if self.last_successful_restart else None,
            "consecutive_failures": self.consecutive_failures
        }
    
    @classmethod
    def from_dict(cls, data, logger=None):
        m = cls(logger)
        m.crash_count = data.get("crash_count", 0)
        m.disconnect_count = data.get("disconnect_count", 0)
        m.restart_count = data.get("restart_count", 0)
        m.config_fetch_failures = data.get("config_fetch_failures", 0)
        m.consecutive_failures = data.get("consecutive_failures", 0)
        if data.get("last_crash_time"):
            m.last_crash_time = datetime.fromisoformat(data["last_crash_time"])
        if data.get("last_successful_restart"):
            m.last_successful_restart = datetime.fromisoformat(data["last_successful_restart"])
        return m
    
    def save(self):
        """Save metrics to file"""
        try:
            NEBULA_DIR.mkdir(parents=True, exist_ok=True)
            METRICS_FILE.write_text(json.dumps(self.to_dict(), indent=2))
        except Exception as e:
            if self.logger:
                self.logger.warning("Failed to save metrics: %s", e)
            else:
                print(f"Warning: Failed to save metrics: {e}")
    
    @classmethod
    def load(cls, logger=None):
        """Load metrics from file"""
        try:
            if METRICS_FILE.exists():
                data = json.loads(METRICS_FILE.read_text())
                return cls.from_dict(data, logger)
        except Exception as e:
            if logger:
                logger.warning("Failed to load metrics: %s", e)
            else:
                print(f"Warning: Failed to load metrics: {e}")
        return cls(logger)


def _inject_windows_tun_dev(config_path: Path) -> None:
    """Inject 'dev: Nebula' into the tun section if missing (Windows only).
    Avoids Wintun empty adapter name errors when server provided older configs.
    Safe, idempotent: only writes if dev key absent.
    """
    if sys.platform.startswith("win") and config_path.exists():
        try:
            text = config_path.read_text().splitlines()
            modified = False
            for i, line in enumerate(text):
                if line.strip() == "tun:":
                    # Look ahead for dev key until blank or next top-level key (no leading spaces)
                    j = i + 1
                    saw_dev = False
                    while j < len(text):
                        nxt = text[j]
                        if nxt.strip() == "":
                            j += 1
                            continue
                        # new top-level section (no indent or starts without two spaces)
                        if not nxt.startswith(" "):
                            break
                        if nxt.strip().startswith("dev:"):
                            saw_dev = True
                            break
                        j += 1
                    if not saw_dev:
                        # Insert after 'tun:' line with two-space indent
                        text.insert(i + 1, "  dev: Nebula")
                        modified = True
                    break
            if modified:
                config_path.write_text("\n".join(text) + "\n")
                logger.info("Injected missing tun.dev into config for Windows")
        except Exception as e:
            logger.warning("Failed to inject tun.dev: %s", e)

# Setup logging
def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure logging for the agent"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("NebulaAgent")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # File handler
    file_handler = logging.FileHandler(AGENT_LOG, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)
    
    # Console handler (for debugging)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logging()

# Initialize metrics after logger is setup
metrics = Metrics.load(logger)

def ensure_directories() -> None:
    """Ensure all required directories exist with proper permissions"""
    try:
        NEBULA_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create Nebula directory {NEBULA_DIR}: {e}")
        raise
    if not NEBULA_DIR.exists():
        logger.critical(f"Nebula directory {NEBULA_DIR} does not exist after mkdir. Check permissions!")
        raise RuntimeError(f"Nebula directory {NEBULA_DIR} does not exist after mkdir.")
    
    # Set restrictive permissions on the nebula directory (Windows ACLs)
    try:
        import win32security
        import ntsecuritycon as con
        
        # Get the security descriptor
        sd = win32security.GetFileSecurity(
            str(NEBULA_DIR),
            win32security.DACL_SECURITY_INFORMATION
        )
        
        # Get SIDs for SYSTEM and Administrators
        system_sid = win32security.LookupAccountName(None, "SYSTEM")[0]
        admins_sid = win32security.LookupAccountName(None, "Administrators")[0]
        
        # Create a new DACL
        dacl = win32security.ACL()
        
        # Add ACEs for SYSTEM and Administrators with full control
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            con.FILE_ALL_ACCESS,
            system_sid
        )
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            con.FILE_ALL_ACCESS,
            admins_sid
        )
        
        # Set the new DACL
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(
            str(NEBULA_DIR),
            win32security.DACL_SECURITY_INFORMATION,
            sd
        )
        logger.debug("Set restrictive permissions on %s", NEBULA_DIR)
    except ImportError:
        logger.warning("pywin32 not available, skipping ACL configuration")
    except Exception as e:
        logger.warning("Failed to set directory permissions: %s", e)


def find_nebula_binary() -> Optional[Path]:
    """Find the nebula.exe binary"""
    # Check in our directory first
    if NEBULA_BIN.exists():
        return NEBULA_BIN
    
    # Check in PATH
    import shutil
    nebula_in_path = shutil.which("nebula.exe") or shutil.which("nebula")
    if nebula_in_path:
        return Path(nebula_in_path)
    
    # Check common install locations and registry App Paths
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\NebulaAgentGUI.exe") as key:
            gui_path, _ = winreg.QueryValueEx(key, "")
            install_dir = Path(gui_path).parent
            candidate = install_dir / "nebula.exe"
            if candidate.exists():
                return candidate
    except Exception:
        pass
    
    for base in [Path(os.environ.get("ProgramFiles", r"C:\Program Files")), Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))]:
        for name in ["ManagedNebula", "Managed Nebula"]:
            candidate = base / name / "nebula.exe"
            if candidate.exists():
                return candidate
    
    return None


def find_nebula_cert_binary() -> Optional[Path]:
    """Find the nebula-cert.exe binary"""
    # Check in our directory first
    if NEBULA_CERT_BIN.exists():
        return NEBULA_CERT_BIN
    
    # Check in PATH
    import shutil
    cert_in_path = shutil.which("nebula-cert.exe") or shutil.which("nebula-cert")
    if cert_in_path:
        return Path(cert_in_path)
    
    # Check common install locations and registry App Paths
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\NebulaAgentGUI.exe") as key:
            gui_path, _ = winreg.QueryValueEx(key, "")
            install_dir = Path(gui_path).parent
            candidate = install_dir / "nebula-cert.exe"
            if candidate.exists():
                return candidate
    except Exception:
        pass
    
    for base in [Path(os.environ.get("ProgramFiles", r"C:\Program Files")), Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))]:
        for name in ["ManagedNebula", "Managed Nebula"]:
            candidate = base / name / "nebula-cert.exe"
            if candidate.exists():
                return candidate
    
    return None


def ensure_keypair() -> Tuple[str, str]:
    """Generate or load Nebula keypair"""
    ensure_directories()
    
    if not KEY_PATH.exists() or not PUB_PATH.exists():
        logger.info("Generating new Nebula keypair...")
        
        nebula_cert = find_nebula_cert_binary()
        if not nebula_cert:
            raise RuntimeError(
                "nebula-cert.exe not found. Please install Nebula binaries."
            )
        
        cmd = [
            str(nebula_cert), "keygen",
            "-out-key", str(KEY_PATH),
            "-out-pub", str(PUB_PATH),
        ]
        
        try:
            subprocess.check_call(cmd, shell=False)
            logger.info("Keypair generated successfully")
            
            # Set restrictive permissions on private key
            set_key_permissions(KEY_PATH)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to generate keypair: %s", e)
            raise
    
    private_key_pem = KEY_PATH.read_text()
    public_key = PUB_PATH.read_text()
    return private_key_pem, public_key


def set_key_permissions(key_path: Path) -> None:
    """Set restrictive permissions on private key file"""
    try:
        import win32security
        import ntsecuritycon as con
        
        # Get SIDs
        system_sid = win32security.LookupAccountName(None, "SYSTEM")[0]
        admins_sid = win32security.LookupAccountName(None, "Administrators")[0]
        
        # Create a new security descriptor
        sd = win32security.SECURITY_DESCRIPTOR()
        dacl = win32security.ACL()
        
        # Only SYSTEM and Administrators can read
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            con.FILE_GENERIC_READ | con.FILE_GENERIC_WRITE,
            system_sid
        )
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            con.FILE_GENERIC_READ | con.FILE_GENERIC_WRITE,
            admins_sid
        )
        
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(
            str(key_path),
            win32security.DACL_SECURITY_INFORMATION,
            sd
        )
        logger.debug("Set restrictive permissions on %s", key_path)
    except ImportError:
        logger.warning("pywin32 not available, skipping key ACL configuration")
    except Exception as e:
        logger.warning("Failed to set key permissions: %s", e)


def get_nebula_version() -> str:
    """Get nebula binary version"""
    nebula = find_nebula_binary()
    if not nebula:
        return "not_installed"
    
    try:
        result = subprocess.run(
            [str(nebula), "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Parse output like "Version: 1.9.7"
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
        return "unknown"
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception as e:
        logger.warning("Failed to get Nebula version: %s", e)
        return "error"


# Helper functions for check_and_update_nebula

def _resolve_verify_ssl(config: dict = None) -> bool:
    """Resolve SSL verification setting from config or environment"""
    if config and "allow_self_signed_cert" in config:
        return not config["allow_self_signed_cert"]
    return os.environ.get("ALLOW_SELF_SIGNED_CERT", "false").lower() != "true"


def _fetch_server_nebula_version(server_url: str, verify_ssl: bool) -> str:
    """Fetch Nebula version from server"""
    version_url = server_url.rstrip("/") + "/v1/version"
    with httpx.Client(timeout=10, verify=verify_ssl) as client:
        r = client.get(version_url)
        r.raise_for_status()
        version_info = r.json()
    return version_info.get("nebula_version", "").lstrip('v')


def _effective_local_nebula_version() -> Optional[str]:
    """Get local Nebula version, returning None if unknown/unavailable"""
    raw = get_nebula_version()
    if raw in {"unknown", "error", "timeout", "not_installed"}:
        return None
    return raw.lstrip('v')


def _download_and_install_nebula(server_version: str, local_version: str, verify_ssl: bool) -> bool:
    """Download and install new Nebula binaries"""
    download_url = f"https://github.com/slackhq/nebula/releases/download/v{server_version}/nebula-windows-amd64.zip"
    logger.info(f"Downloading Nebula {server_version} from {download_url}")
    
    import zipfile
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        zip_path = tmpdir_path / "nebula.zip"
        
        # Download zip (follow redirects for GitHub releases)
        # Reuse the same SSL verification configuration as the version check
        with httpx.Client(timeout=120, verify=verify_ssl, follow_redirects=True) as dl_client:
            with dl_client.stream("GET", download_url) as response:
                response.raise_for_status()
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
        
        logger.info("Download complete, extracting...")
        
        # Extract zip
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir_path)
        
        # Verify extracted files exist
        new_nebula = tmpdir_path / "nebula.exe"
        new_nebula_cert = tmpdir_path / "nebula-cert.exe"
        
        if not new_nebula.exists():
            raise FileNotFoundError(f"nebula.exe not found in downloaded archive")
        if not new_nebula_cert.exists():
            raise FileNotFoundError(f"nebula-cert.exe not found in downloaded archive")
        
        # Verify new version - The subprocess call is safe here because:
        # - new_nebula is a Path object we created from our controlled temporary directory
        # - It's not derived from user input or external data
        # - The path is fully controlled by tempfile.TemporaryDirectory()
        result = subprocess.run(
            [str(new_nebula), "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        new_version = "unknown"
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                new_version = line.split(":", 1)[1].strip().lstrip('v')
        
        if new_version != server_version:
            logger.error(f"Downloaded version {new_version} doesn't match expected {server_version}")
            return False
        
        logger.info(f"Verified downloaded Nebula version: {new_version}")
        
        # Stop Nebula if running (we'll restart it later)
        stop_nebula()
        time.sleep(2)  # Wait for process to fully stop
        
        # Replace binaries
        logger.info("Replacing Nebula binaries...")
        
        # Backup existing binaries
        if NEBULA_BIN.exists():
            backup_path = NEBULA_BIN.parent / f"nebula.exe.backup.{int(time.time())}"
            NEBULA_BIN.rename(backup_path)
            logger.info(f"Backed up old nebula.exe to {backup_path}")
        
        if NEBULA_CERT_BIN.exists():
            backup_path = NEBULA_CERT_BIN.parent / f"nebula-cert.exe.backup.{int(time.time())}"
            NEBULA_CERT_BIN.rename(backup_path)
            logger.info(f"Backed up old nebula-cert.exe to {backup_path}")
        
        # Copy new binaries
        shutil.copy2(new_nebula, NEBULA_BIN)
        shutil.copy2(new_nebula_cert, NEBULA_CERT_BIN)
        
        logger.info(f"Successfully updated Nebula from {local_version} to {server_version}")
        return True


def _install_wintun_from_src(src: Path) -> bool:
    """Install wintun.dll from source to both root and nested locations"""
    import shutil
    try:
        # root
        shutil.copy2(src, WINTUN_DLL)
        logger.info(f"Installed wintun.dll to {WINTUN_DLL}")
        
        # nested
        WINTUN_DLL_NESTED.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, WINTUN_DLL_NESTED)
        logger.info(f"Installed wintun.dll to {WINTUN_DLL_NESTED}")
        return True
    except Exception as e:
        logger.error(f"Failed to install wintun.dll: {e}", exc_info=True)
        return False


def ensure_wintun_dll() -> bool:
    """
    Ensure wintun.dll is present for Nebula to create tunnel interface.
    Downloads from wintun.net if missing.
    Places wintun.dll in multiple locations for compatibility.
    
    Returns True if wintun.dll is present or was successfully downloaded.
    """
    import shutil
    import platform
    
    # If nested path exists, we're good
    if WINTUN_DLL_NESTED.exists():
        logger.debug("wintun.dll already exists in nested path")
        return True
    
    # Check if we have wintun.dll in root and can copy it to nested path
    if WINTUN_DLL.exists():
        logger.info("wintun.dll found in root, copying to nested path...")
        try:
            WINTUN_DLL_NESTED.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(WINTUN_DLL, WINTUN_DLL_NESTED)
            logger.info(f"Copied wintun.dll to {WINTUN_DLL_NESTED}")
            return True
        except Exception as e:
            logger.warning(f"Failed to copy wintun.dll to nested path: {e}")
            # Continue to download fresh copy
    
    # Need to download wintun.dll
    logger.info("wintun.dll not found, downloading...")
    
    try:
        import tempfile
        import zipfile
        
        wintun_url = "https://www.wintun.net/builds/wintun-0.14.1.zip"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            wintun_zip = tmpdir_path / "wintun.zip"
            
            # Download wintun zip
            with httpx.Client(timeout=60, verify=True, follow_redirects=True) as client:
                r = client.get(wintun_url)
                r.raise_for_status()
                wintun_zip.write_bytes(r.content)
            
            # Extract zip
            with zipfile.ZipFile(wintun_zip, 'r') as zip_ref:
                zip_ref.extractall(tmpdir_path / "wintun_extract")
            
            # Copy appropriate architecture DLL
            arch = "amd64" if platform.machine().endswith('64') else "x86"
            wintun_dll_src = tmpdir_path / "wintun_extract" / "wintun" / "bin" / arch / "wintun.dll"
            
            if wintun_dll_src.exists():
                return _install_wintun_from_src(wintun_dll_src)
            else:
                logger.error(f"wintun.dll not found in archive at expected path: {wintun_dll_src}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to download wintun.dll: {e}", exc_info=True)
        return False


def check_and_update_nebula(server_url: str, config: dict = None) -> bool:
    """
    Check server's Nebula version and auto-update if different.
    
    Returns True if update was performed (and might need restart).
    """
    logger.info("Checking for Nebula version updates...")
    verify_ssl = _resolve_verify_ssl(config)
    
    try:
        server_version = _fetch_server_nebula_version(server_url, verify_ssl)
        local_version = _effective_local_nebula_version()
        
        logger.info(f"Nebula version check: local={local_version}, server={server_version}")
        
        if local_version is None:
            logger.warning("Cannot determine local Nebula version")
            return False
        
        if local_version == server_version:
            logger.info("Nebula version matches server, no update needed")
            return False
        
        logger.warning(
            f"Nebula version mismatch detected. Upgrading from {local_version} to {server_version}"
        )
        return _download_and_install_nebula(server_version, local_version, verify_ssl)
        
    except httpx.HTTPStatusError as e:
        logger.warning(f"Failed to check server version: HTTP {e.response.status_code}")
        return False
    except Exception as e:
        logger.error(f"Failed to auto-update Nebula: {e}", exc_info=True)
        return False


def save_cached_config(config_data: dict):
    """Cache config for fallback when server is unavailable"""
    try:
        NEBULA_DIR.mkdir(parents=True, exist_ok=True)
        CACHED_CONFIG_FILE.write_text(json.dumps(config_data, indent=2))
        logger.info("Config cached successfully")
    except Exception as e:
        logger.warning("Failed to cache config: %s", e)


def load_cached_config() -> Optional[dict]:
    """Load cached config as fallback"""
    try:
        if CACHED_CONFIG_FILE.exists():
            return json.loads(CACHED_CONFIG_FILE.read_text())
    except Exception as e:
        logger.warning("Failed to load cached config: %s", e)
    return None


def fetch_config_with_retry(token: str, server_url: str, public_key: str, config: dict = None) -> Optional[dict]:
    """Fetch config with exponential backoff retry logic"""
    global metrics
    
    url = server_url.rstrip("/") + "/v1/client/config"
    
    payload = {
        "token": token,
        "public_key": public_key,
        "client_version": os.environ.get("CLIENT_VERSION_OVERRIDE", __version__),
        "nebula_version": os.environ.get("NEBULA_VERSION_OVERRIDE", get_nebula_version()),
        "os_type": "windows"  # Identify this as a Windows client
    }
    
    # SSL verification (disable for self-signed certs if configured)
    if config and "allow_self_signed_cert" in config:
        verify_ssl = not config["allow_self_signed_cert"]
    else:
        verify_ssl = os.environ.get("ALLOW_SELF_SIGNED_CERT", "false").lower() != "true"
    
    if not verify_ssl:
        logger.warning("SSL certificate verification disabled - using self-signed certificates")
    
    for attempt in range(MAX_FETCH_RETRIES):
        try:
            logger.info("Fetching config (attempt %d/%d)...", attempt + 1, MAX_FETCH_RETRIES)
            logger.debug("Client version: %s, Nebula version: %s, OS: windows",
                        payload["client_version"], payload["nebula_version"])
            
            with httpx.Client(timeout=CONFIG_FETCH_TIMEOUT, verify=verify_ssl) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
                config_data = r.json()
                
                # Cache successful config
                save_cached_config(config_data)
                
                # Reset failure counter on success
                metrics.config_fetch_failures = 0
                metrics.save()
                
                return config_data
                
        except httpx.TimeoutException:
            metrics.config_fetch_failures += 1
            logger.warning("Config fetch timeout (attempt %d/%d)", attempt + 1, MAX_FETCH_RETRIES)
            
        except httpx.HTTPStatusError as e:
            metrics.config_fetch_failures += 1
            logger.error("HTTP error fetching config: %s - %s (attempt %d/%d)", 
                        e.response.status_code, e.response.text, attempt + 1, MAX_FETCH_RETRIES)
            
        except Exception as e:
            metrics.config_fetch_failures += 1
            logger.error("Error fetching config: %s (attempt %d/%d)", e, attempt + 1, MAX_FETCH_RETRIES)
        
        # Exponential backoff: 1s, 2s, 4s, 8s, max 60s
        if attempt < MAX_FETCH_RETRIES - 1:
            wait_time = min(2 ** attempt, 60)
            logger.info("Retrying in %d seconds...", wait_time)
            time.sleep(wait_time)
    
    # All retries failed
    metrics.save()
    logger.warning("All config fetch attempts failed, trying cached config...")
    cached = load_cached_config()
    if cached:
        logger.info("Using cached config as fallback")
        return cached
    
    logger.error("ERROR: No cached config available")
    return None


def fetch_config(token: str, server_url: str, public_key: str, config: dict = None) -> dict:
    """Fetch configuration from server (backwards compatible wrapper)"""
    result = fetch_config_with_retry(token, server_url, public_key, config)
    if result is None:
        raise Exception("Failed to fetch config after all retries and no cache available")
    return result


def calculate_config_hash(
    config_yaml: str,
    client_cert_pem: str,
    ca_chain_pems: list
) -> str:
    """Calculate hash of the complete config including certs"""
    hasher = hashlib.sha256()
    hasher.update(config_yaml.encode())
    hasher.update(client_cert_pem.encode())
    hasher.update("".join(ca_chain_pems).encode())
    return hasher.hexdigest()


def get_current_config_hash() -> str:
    """Get hash of currently written config files"""
    if not CONFIG_PATH.exists():
        return ""
    
    config_yaml = CONFIG_PATH.read_text()
    ca_content = CA_PATH.read_text() if CA_PATH.exists() else ""
    cert_content = CERT_PATH.read_text() if CERT_PATH.exists() else ""
    
    hasher = hashlib.sha256()
    hasher.update(config_yaml.encode())
    hasher.update(cert_content.encode())
    hasher.update(ca_content.encode())
    return hasher.hexdigest()


def write_config_and_pki(
    config_yaml: str,
    client_cert_pem: str,
    ca_chain_pems: list
) -> bool:
    """Write config and PKI files. Returns True if files changed."""
    # Check if config would actually change
    new_hash = calculate_config_hash(config_yaml, client_cert_pem, ca_chain_pems)
    current_hash = get_current_config_hash()
    
    if new_hash == current_hash:
        logger.info("Config unchanged, no restart needed")
        return False
    
    logger.info("Config changed, writing new files")
    logger.debug("Config file size: %d bytes", len(config_yaml))
    logger.debug("Client cert size: %d bytes", len(client_cert_pem))
    logger.debug("CA chain certs: %d", len(ca_chain_pems))
    ensure_directories()
    
    # Write config (server now sends OS-specific paths)
    CONFIG_PATH.write_text(config_yaml)
    logger.info("Config written to: %s", CONFIG_PATH)
    
    # Write certificates
    CA_PATH.write_text("".join(ca_chain_pems))
    logger.debug("CA chain written to: %s", CA_PATH)
    CERT_PATH.write_text(client_cert_pem)
    logger.debug("Client cert written to: %s", CERT_PATH)
    
    # Set restrictive permissions on key file if it exists
    if KEY_PATH.exists():
        set_key_permissions(KEY_PATH)
        logger.debug("Key permissions set on: %s", KEY_PATH)
    else:
        logger.warning("Key file does not exist at: %s", KEY_PATH)
    
    return True


def is_nebula_running() -> bool:
    """Check if Nebula process is running"""
    try:
        # Use tasklist to check for nebula.exe
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq nebula.exe", "/NH"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return "nebula.exe" in result.stdout
    except Exception as e:
        logger.warning("Failed to check Nebula status: %s", e)
        return False


def stop_nebula() -> None:
    """Stop the Nebula process"""
    logger.info("Stopping Nebula...")
    
    try:
        # Use taskkill to stop nebula.exe gracefully
        subprocess.run(
            ["taskkill", "/IM", "nebula.exe", "/T"],
            capture_output=True,
            timeout=10
        )
        time.sleep(2)
        
        # Force kill if still running
        if is_nebula_running():
            logger.warning("Nebula still running, forcing termination")
            subprocess.run(
                ["taskkill", "/IM", "nebula.exe", "/F", "/T"],
                capture_output=True,
                timeout=10
            )
            time.sleep(1)
    except subprocess.TimeoutExpired:
        logger.error("Timeout stopping Nebula")
    except Exception as e:
        logger.error("Error stopping Nebula: %s", e)


def start_nebula() -> bool:
    """Start the Nebula daemon"""
    nebula = find_nebula_binary()
    if not nebula:
        logger.error("Nebula binary not found")
        return False
    
    if not CONFIG_PATH.exists():
        logger.error("Config file not found: %s", CONFIG_PATH)
        return False
    
    logger.info("Starting Nebula daemon...")

    # Ensure Windows adapter name present to avoid empty-name Wintun failure
    _inject_windows_tun_dev(CONFIG_PATH)

    # Preflight: check for Wintun driver DLL presence (required on Windows)
    # Nebula looks in multiple locations: next to nebula.exe, in NEBULA_DIR, or in nested dist/ path
    wintun_candidate = Path(nebula).parent / "wintun.dll"
    if not WINTUN_DLL.exists() and not wintun_candidate.exists() and not WINTUN_DLL_NESTED.exists():
        logger.warning(
            "wintun.dll not found in any expected location. Nebula may fail to create the tunnel."
        )
        logger.warning(
            "Expected locations: %s, %s, %s", 
            WINTUN_DLL, wintun_candidate, WINTUN_DLL_NESTED
        )
        logger.warning(
            "Ensure wintun.dll is present or WireGuard is installed. See https://www.wintun.net/."
        )
    
    try:
        # Validate config first
        result = subprocess.run(
            [str(nebula), "-config", str(CONFIG_PATH), "-test"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            logger.error("Config validation failed (exit code %d): %s", result.returncode, error_msg)
            logger.debug("Config path: %s", CONFIG_PATH)
            logger.debug("Nebula binary: %s", nebula)
            return False
        
        logger.info("Config validation passed")
        
        # Start Nebula in the background
        # On Windows, we use CREATE_NEW_PROCESS_GROUP to detach
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008

        # Write nebula runtime logs to file to aid diagnosis
        runtime_log_path = LOG_DIR / "nebula.log"
        runtime_log = open(runtime_log_path, "ab")

        process = subprocess.Popen(
            [str(nebula), "-config", str(CONFIG_PATH)],
            stdout=runtime_log,
            stderr=runtime_log,
            creationflags=CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
        )

        logger.info("Started Nebula process (PID: %d)", process.pid)

        # Give it a moment and verify it's running
        time.sleep(1.5)
        if not is_nebula_running():
            logger.error("Nebula process is not running after start. See %s for details.", runtime_log_path)
            return False

        return True
    except Exception as e:
        logger.error("Failed to start Nebula: %s", e)
        return False


def restart_nebula() -> bool:
    """Restart the Nebula daemon (legacy function for compatibility)"""
    return restart_nebula_with_backoff()


def restart_nebula_with_backoff() -> bool:
    """Restart Nebula with exponential backoff and failure tracking"""
    global metrics
    
    # Validate config before attempting restart
    nebula = find_nebula_binary()
    if not nebula:
        logger.error("Skipping restart - nebula binary not found")
        return False
    
    if not CONFIG_PATH.exists():
        logger.error("Skipping restart - config file not found")
        return False
    
    # Validate config syntax
    try:
        result = subprocess.run(
            [str(nebula), "-config", str(CONFIG_PATH), "-test"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            logger.error("Skipping restart - config validation failed")
            return False
    except Exception as e:
        logger.error("Config validation error: %s", e)
        return False
    
    attempts = 0
    while attempts < MAX_RESTART_ATTEMPTS:
        attempts += 1
        
        # Log restart attempt
        timestamp = datetime.now().isoformat()
        logger.info("[%s] Restart attempt %d/%d", timestamp, attempts, MAX_RESTART_ATTEMPTS)
        
        # Stop current process
        stop_nebula()
        
        # Start new process
        if start_nebula():
            # Wait for Nebula to initialize
            logger.info("Waiting %ds for Nebula to initialize...", RESTART_INIT_TIMEOUT)
            start_time = time.time()
            initialized = False
            
            while (time.time() - start_time) < RESTART_INIT_TIMEOUT:
                time.sleep(1)
                if is_nebula_running():
                    initialized = True
                    break
            
            if initialized:
                # Restart successful
                metrics.restart_count += 1
                metrics.consecutive_failures = 0
                metrics.last_successful_restart = datetime.now()
                metrics.save()
                
                timestamp = datetime.now().isoformat()
                logger.info("[%s] Nebula restarted successfully", timestamp)
                return True
            else:
                # Process didn't start properly
                metrics.consecutive_failures += 1
                logger.warning("Restart attempt %d failed - Nebula did not start within %ds",
                             attempts, RESTART_INIT_TIMEOUT)
        else:
            metrics.consecutive_failures += 1
            logger.warning("Restart attempt %d failed - start_nebula returned False", attempts)
        
        # Exponential backoff: 1s, 2s, 4s, max 30s
        if attempts < MAX_RESTART_ATTEMPTS:
            wait_time = min(2 ** (attempts - 1), 30)
            logger.info("Waiting %ds before next attempt...", wait_time)
            time.sleep(wait_time)
    
    # All restart attempts failed
    metrics.save()
    timestamp = datetime.now().isoformat()
    logger.error("[%s] ERROR: Failed to restart Nebula after %d attempts", timestamp, MAX_RESTART_ATTEMPTS)
    logger.error("Consecutive failures: %d", metrics.consecutive_failures)
    logger.error("ALERT: Administrator intervention required!")
    return False


def check_nebula_health() -> bool:
    """
    Check if Nebula is healthy by examining its state.
    Returns True if healthy, False if unhealthy and needs restart.
    """
    # Basic check: is process running?
    if not is_nebula_running():
        return False
    
    # TODO: Advanced health checks could include:
    # - Parse nebula logs for errors
    # - Check adapter status
    # - Verify connectivity
    # For now, if process is running, consider it healthy
    return True


def monitor_nebula_process():
    """
    Continuously monitor Nebula process and restart on crash.
    This runs in the background during run_loop_with_monitoring.
    """
    global metrics
    
    logger.info("Starting process monitor (check interval: %ds)", PROCESS_CHECK_INTERVAL)
    
    last_health_check = time.time()
    
    while True:
        try:
            # Check if process is running
            if not is_nebula_running():
                # Process crashed!
                timestamp = datetime.now().isoformat()
                logger.warning("[%s] CRASH DETECTED: Nebula process not running", timestamp)
                
                metrics.crash_count += 1
                metrics.last_crash_time = datetime.now()
                metrics.consecutive_failures += 1
                metrics.save()
                
                # Check if we've exceeded max consecutive failures
                if metrics.consecutive_failures >= MAX_RESTART_ATTEMPTS:
                    timestamp = datetime.now().isoformat()
                    logger.error("[%s] ALERT: Too many consecutive failures (%d)",
                               timestamp, metrics.consecutive_failures)
                    logger.error("Stopping automatic restarts. Administrator intervention required.")
                    logger.error("Metrics: %s", metrics.to_dict())
                    # Sleep longer before checking again
                    time.sleep(300)  # 5 minutes
                    continue
                
                # Attempt recovery
                logger.info("Attempting automatic recovery...")
                if restart_nebula_with_backoff():
                    logger.info("Recovery successful")
                else:
                    logger.error("Recovery failed")
            
            # Periodic health check (in addition to process check)
            current_time = time.time()
            if current_time - last_health_check >= HEALTH_CHECK_INTERVAL:
                last_health_check = current_time
                
                if is_nebula_running() and not check_nebula_health():
                    # Process is running but unhealthy
                    timestamp = datetime.now().isoformat()
                    logger.warning("[%s] Health check failed, restarting Nebula", timestamp)
                    
                    metrics.disconnect_count += 1
                    metrics.save()
                    
                    restart_nebula_with_backoff()
        
        except Exception as e:
            logger.error("Error in process monitor: %s", e)
        
        # Sleep before next check
        time.sleep(PROCESS_CHECK_INTERVAL)


def run_once(restart_on_change: bool = False) -> bool:
    """Run single configuration fetch and update cycle"""
    # Load full config
    from config import load_config
    cfg = load_config()
    
    token = os.environ.get("CLIENT_TOKEN")
    if not token:
        token = cfg.get("client_token")
    
    if not token:
        logger.error("CLIENT_TOKEN environment variable or config not set")
        return False
    
    server_url = os.environ.get("SERVER_URL")
    if not server_url:
        server_url = cfg.get("server_url", "http://localhost:8080")
    
    nebula_updated = False
    try:
        # Check and auto-update Nebula version to match server
        nebula_updated = check_and_update_nebula(server_url, config=cfg)
        if nebula_updated:
            logger.info("Nebula was updated - configuration fetch will use new version")
            restart_on_change = True  # Force restart after upgrade
        
        # Always ensure wintun.dll is present (required for Nebula to work on Windows)
        wintun_ok = ensure_wintun_dll()
        if not wintun_ok:
            logger.error(
                "Failed to ensure wintun.dll is present; Nebula cannot be started on Windows. "
                "Aborting this run and leaving existing state unchanged."
            )
            return False
        
        _priv, pub = ensure_keypair()
        data = fetch_config(token, server_url, pub, config=cfg)
        
        config_yaml = data["config"]
        client_cert_pem = data.get("client_cert_pem", "")
        ca_chain_pems = data.get("ca_chain_pems", [])
        
        config_changed = write_config_and_pki(config_yaml, client_cert_pem, ca_chain_pems)
        
        # Restart Nebula if config changed or if binary was updated
        if restart_on_change and (config_changed or nebula_updated):
            timestamp = datetime.now().isoformat()
            logger.info("[%s] Coordinated recovery: restarting Nebula", timestamp)
            
            if nebula_updated and not config_changed:
                logger.info("Restarting Nebula to use updated binary")
            
            if restart_nebula_with_backoff():
                # Wait after restart, then fetch fresh config
                logger.info("Waiting %ds before fetching fresh config...", POST_RESTART_WAIT)
                time.sleep(POST_RESTART_WAIT)
                
                try:
                    logger.info("Fetching fresh config after restart...")
                    fresh_data = fetch_config(token, server_url, pub, config=cfg)
                    fresh_cfg = fresh_data["config"]
                    fresh_cert_pem = fresh_data.get("client_cert_pem", "")
                    fresh_ca_pems = fresh_data.get("ca_chain_pems", [])
                    
                    # Check if fresh config differs from what we just wrote
                    fresh_changed = write_config_and_pki(fresh_cfg, fresh_cert_pem, fresh_ca_pems)
                    if fresh_changed:
                        logger.info("Fresh config differs, restarting again...")
                        restart_nebula_with_backoff()
                except Exception as e:
                    logger.error("Failed to fetch fresh config after restart: %s", e)
                    logger.info("Continuing with existing config")
            else:
                logger.error("Failed to restart Nebula")
        
        return True
    except Exception as e:
        logger.error("Configuration fetch failed: %s", e)
        return False


def run_loop() -> None:
    """Run in continuous polling loop"""
    interval_hours = int(os.environ.get("POLL_INTERVAL_HOURS", "24"))
    logger.info("Starting polling loop (interval: %d hours)", interval_hours)
    
    while True:
        try:
            run_once(restart_on_change=True)
        except Exception as e:
            logger.error("Refresh failed: %s", e)
        
        # Sleep for the interval
        time.sleep(interval_hours * 3600)


def run_loop_with_monitoring() -> None:
    """
    Run in continuous polling loop with process monitoring.
    This is the enhanced mode with resilient recovery.
    """
    logger.info("Starting enhanced mode with process monitoring and resilient recovery")
    logger.info("Configuration:")
    logger.info("  - Process check interval: %ds", PROCESS_CHECK_INTERVAL)
    logger.info("  - Health check interval: %ds", HEALTH_CHECK_INTERVAL)
    logger.info("  - Config fetch timeout: %ds", CONFIG_FETCH_TIMEOUT)
    logger.info("  - Max restart attempts: %d", MAX_RESTART_ATTEMPTS)
    logger.info("  - Max fetch retries: %d", MAX_FETCH_RETRIES)
    logger.info("  - Post-restart wait: %ds", POST_RESTART_WAIT)
    
    # Start process monitoring in background thread
    monitor_thread = threading.Thread(target=monitor_nebula_process, daemon=True)
    monitor_thread.start()
    
    # Run normal polling loop in main thread
    interval_hours = int(os.environ.get("POLL_INTERVAL_HOURS", "24"))
    
    while True:
        try:
            # In loop mode, always restart on config changes
            run_once(restart_on_change=True)
        except Exception as e:
            logger.error("Config refresh failed: %s", e)
            # Don't crash the loop, just log and continue
        
        # Sleep for the poll interval
        time.sleep(interval_hours * 3600)


def get_status() -> dict:
    """Get current agent and Nebula status"""
    nebula_running = is_nebula_running()
    nebula_version = get_nebula_version()
    
    status = {
        "agent_version": __version__,
        "nebula_version": nebula_version,
        "nebula_running": nebula_running,
        "config_exists": CONFIG_PATH.exists(),
        "keypair_exists": KEY_PATH.exists() and PUB_PATH.exists(),
        "paths": {
            "config": str(CONFIG_PATH),
            "key": str(KEY_PATH),
            "log": str(AGENT_LOG),
            "nebula_log": str(LOG_DIR / "nebula.log"),
            "nebula_bin": str(NEBULA_BIN),
            "wintun_dll": str(WINTUN_DLL),
        }
    }
    
    return status


def diagnose() -> None:
    """Print diagnostics: file presence, adapter status, last logs."""
    try:
        status = get_status()
        print("Agent/Nebula status:")
        print(f"- agent_version: {status['agent_version']}")
        print(f"- nebula_version: {status['nebula_version']}")
        print(f"- nebula_running: {status['nebula_running']}")
        print(f"- config_exists: {status['config_exists']}")
        print(f"- keypair_exists: {status['keypair_exists']}")
        print("Paths:")
        for k, v in status["paths"].items():
            print(f"  - {k}: {v}")

        # Quick file existence checks
        print("\nFile existence checks:")
        for k, v in status["paths"].items():
            if k in ("log", "nebula_log", "config", "key", "nebula_bin", "wintun_dll"):
                exists = Path(v).exists()
                print(f"  - {k} exists: {exists}")

        # Show last lines of agent and nebula logs
        def tail(path: Path, lines: int = 50) -> str:
            try:
                with open(path, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    block = 1024
                    data = b""
                    while size > 0 and data.count(b"\n") <= lines:
                        size = max(0, size - block)
                        f.seek(size)
                        data = f.read(block) + data
                    return data.decode(errors="replace").splitlines()[-lines:]
            except Exception:
                return []

        print("\nLast agent.log lines:")
        for line in tail(AGENT_LOG):
            print(line)

        nebula_log = LOG_DIR / "nebula.log"
        print("\nLast nebula.log lines:")
        for line in tail(nebula_log):
            print(line)
    except Exception as e:
        print(f"Diagnostics failed: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Managed Nebula Windows Agent"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run in polling loop"
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Run in enhanced monitoring mode (recommended)"
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Restart Nebula if config changes (only with --once)"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current status"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information"
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Print diagnostics for troubleshooting"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set log level"
    )
    
    args = parser.parse_args()
    
    # Reconfigure logging with requested level
    global logger
    logger = setup_logging(args.log_level)
    
    if args.version:
        print(f"Managed Nebula Agent v{__version__}")
        print(f"Nebula: {get_nebula_version()}")
        sys.exit(0)
    if args.diagnose:
        diagnose()
        sys.exit(0)
    
    if args.status:
        import json
        status = get_status()
        print(json.dumps(status, indent=2))
        sys.exit(0)
    
    if args.once:
        success = run_once(restart_on_change=args.restart)
        sys.exit(0 if success else 1)
    elif args.monitor:
        run_loop_with_monitoring()
    elif args.loop:
        run_loop()
    else:
        # Default: run once without restart
        success = run_once()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
