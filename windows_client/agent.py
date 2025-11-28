"""
Managed Nebula Windows Agent
Main agent logic for fetching configuration and managing Nebula daemon on Windows
"""

import argparse
import hashlib
import logging
import os
import subprocess
import sys
import time
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


def fetch_config(token: str, server_url: str, public_key: str, config: dict = None) -> dict:
    """Fetch configuration from server"""
    url = server_url.rstrip("/") + "/v1/client/config"
    
    payload = {
        "token": token,
        "public_key": public_key,
        "client_version": os.environ.get("CLIENT_VERSION_OVERRIDE", __version__),
        "nebula_version": os.environ.get("NEBULA_VERSION_OVERRIDE", get_nebula_version()),
        "os_type": "windows"  # Identify this as a Windows client
    }
    
    logger.info("Fetching config from %s", url)
    logger.debug("Client version: %s, Nebula version: %s, OS: windows",
                 payload["client_version"], payload["nebula_version"])
    
    # SSL verification (disable for self-signed certs if configured)
    # Check config first, then fall back to env var
    if config and "allow_self_signed_cert" in config:
        verify_ssl = not config["allow_self_signed_cert"]
    else:
        verify_ssl = os.environ.get("ALLOW_SELF_SIGNED_CERT", "false").lower() != "true"
    
    if not verify_ssl:
        logger.warning("SSL certificate verification disabled - using self-signed certificates")
    
    try:
        with httpx.Client(timeout=30, verify=verify_ssl) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error fetching config: %s - %s", e.response.status_code, e.response.text)
        raise
    except Exception as e:
        logger.error("Failed to fetch config: %s", e)
        raise


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
    # Usually placed alongside nebula.exe as wintun.dll
    wintun_candidate = Path(nebula).parent / "wintun.dll"
    if not WINTUN_DLL.exists() and not wintun_candidate.exists():
        logger.warning(
            "wintun.dll not found next to nebula.exe or in %s. Nebula may fail to create the tunnel.",
            NEBULA_DIR,
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
    """Restart the Nebula daemon"""
    logger.info("Restarting Nebula daemon...")
    stop_nebula()
    return start_nebula()


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
    
    try:
        _priv, pub = ensure_keypair()
        data = fetch_config(token, server_url, pub, config=cfg)
        
        config_yaml = data["config"]
        client_cert_pem = data.get("client_cert_pem", "")
        ca_chain_pems = data.get("ca_chain_pems", [])
        
        config_changed = write_config_and_pki(config_yaml, client_cert_pem, ca_chain_pems)
        
        if config_changed and restart_on_change:
            restart_nebula()
        
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
    elif args.loop:
        run_loop()
    else:
        # Default: run once without restart
        success = run_once()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
