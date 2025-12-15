import argparse
import os
import time
import signal
import hashlib
from pathlib import Path
import httpx
import subprocess

__version__ = "1.0.0"

STATE_DIR = Path(os.getenv("NEBULA_STATE_DIR", "/var/lib/nebula"))
CONFIG_PATH = Path("/etc/nebula/config.yml")
KEY_PATH = STATE_DIR / "host.key"
PUB_PATH = STATE_DIR / "host.pub"
PIDFILE = STATE_DIR / "nebula.pid"


def ensure_keypair() -> tuple[str, str]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not KEY_PATH.exists() or not PUB_PATH.exists():
        # Generate keypair with nebula-cert
        cmd = [
            "nebula-cert", "keygen",
            "-out-key", str(KEY_PATH),
            "-out-pub", str(PUB_PATH),
        ]
        subprocess.check_call(cmd)
    private_key_pem = KEY_PATH.read_text()
    public_key = PUB_PATH.read_text()
    return private_key_pem, public_key


def get_nebula_version() -> str:
    """Get nebula binary version"""
    try:
        result = subprocess.run(
            ["nebula", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Parse output like "Version: 1.9.7"
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
        return "unknown"
    except Exception:
        return "unknown"


# Helper functions for check_and_update_nebula

def _resolve_arch() -> Optional[str]:
    """Resolve system architecture for Nebula downloads"""
    import platform
    machine = platform.machine().lower()
    if machine in ['x86_64', 'amd64']:
        return 'amd64'
    if machine in ['aarch64', 'arm64']:
        return 'arm64'
    if machine.startswith('arm'):
        return 'arm'
    return None


def _stop_nebula_with_timeout() -> None:
    """Stop Nebula daemon with graceful timeout"""
    pid = get_nebula_pid()
    if not pid:
        return
    try:
        os.kill(pid, 15)  # SIGTERM
        time.sleep(2)
        try:
            os.kill(pid, 0)
        except OSError:
            return  # Process exited
        print("[agent] Process still running, sending SIGKILL...")
        os.kill(pid, 9)
        time.sleep(1)
    except OSError:
        pass


def _download_and_extract_nebula(download_url: str, verify_ssl: bool) -> Optional[tuple[Path, Path]]:
    """Download and extract Nebula binaries, returning paths or None on failure"""
    import tarfile
    import tempfile
    
    tmpdir = tempfile.mkdtemp()
    tmpdir_path = Path(tmpdir)
    tar_path = tmpdir_path / "nebula.tar.gz"
    
    try:
        with httpx.Client(timeout=120, verify=verify_ssl, follow_redirects=True) as dl_client:
            with dl_client.stream("GET", download_url) as response:
                response.raise_for_status()
                with open(tar_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
        
        print(f"[agent] Downloaded {tar_path.stat().st_size} bytes")
        
        extract_dir = tmpdir_path / "nebula_extract"
        extract_dir.mkdir()
        with tarfile.open(tar_path, "r:gz") as tar_ref:
            tar_ref.extractall(extract_dir)
        
        nebula_bin = extract_dir / "nebula"
        nebula_cert_bin = extract_dir / "nebula-cert"
        if not nebula_bin.exists() or not nebula_cert_bin.exists():
            print("[agent] ERROR: Nebula binaries not found in archive")
            return None
        
        return nebula_bin, nebula_cert_bin
    except Exception as e:
        print(f"[agent] Failed to download/extract Nebula: {e}")
        return None


def _backup_and_install(nebula_bin: Path, nebula_cert_bin: Path) -> bool:
    """Backup old binaries and install new ones"""
    import shutil
    
    nebula_path = shutil.which("nebula")
    nebula_cert_path = shutil.which("nebula-cert")
    
    # Backup existing binaries
    for src in (nebula_path, nebula_cert_path):
        if not src:
            continue
        try:
            src_path = Path(src)
            backup_path = src_path.with_suffix(".bak")
            shutil.copy2(src_path, backup_path)
            print(f"[agent] Backed up {src_path.name} to {backup_path}")
        except Exception as e:
            print(f"[agent] Warning: Failed to backup {src}: {e}")
    
    install_dir = Path("/usr/local/bin")
    if not os.access(install_dir, os.W_OK):
        print(f"[agent] ERROR: No write permission to {install_dir}")
        return False
    
    try:
        shutil.copy2(nebula_bin, install_dir / "nebula")
        shutil.copy2(nebula_cert_bin, install_dir / "nebula-cert")
        (install_dir / "nebula").chmod(0o755)
        (install_dir / "nebula-cert").chmod(0o755)
        return True
    except Exception as e:
        print(f"[agent] ERROR: Failed to install binaries: {e}")
        return False


def check_and_update_nebula(server_url: str) -> bool:
    """
    Check server's Nebula version and auto-update if different.
    
    Returns True if update was performed (and might need restart).
    """
    print("[agent] Checking for Nebula version updates...")
    verify_ssl = os.getenv("ALLOW_SELF_SIGNED_CERT", "false").lower() != "true"
    
    try:
        # Get server version (public endpoint, no auth required)
        version_url = server_url.rstrip("/") + "/v1/version"
        with httpx.Client(timeout=10, verify=verify_ssl) as client:
            r = client.get(version_url)
            r.raise_for_status()
            version_info = r.json()
        
        server_version = version_info.get("nebula_version", "").lstrip('v')
        local_version = get_nebula_version().lstrip('v')
        
        print(f"[agent] Nebula version check: local={local_version}, server={server_version}")
        
        # If versions match or local version is unknown, skip update
        if local_version == "unknown":
            print("[agent] Cannot determine local Nebula version")
            return False
        
        if local_version == server_version:
            print("[agent] Nebula version matches server, no update needed")
            return False
        
        # Versions differ - download and install matching version
        print(f"[agent] Nebula version mismatch detected. Upgrading from {local_version} to {server_version}")
        
        arch = _resolve_arch()
        if not arch:
            import platform
            print(f"[agent] Unsupported architecture: {platform.machine().lower()}")
            return False
        
        download_url = (
            f"https://github.com/slackhq/nebula/releases/download/"
            f"v{server_version}/nebula-linux-{arch}.tar.gz"
        )
        print(f"[agent] Downloading Nebula {server_version} from {download_url}")
        
        result = _download_and_extract_nebula(download_url, verify_ssl)
        if not result:
            return False
        nebula_bin, nebula_cert_bin = result
        
        print("[agent] Stopping Nebula process before upgrade...")
        _stop_nebula_with_timeout()
        
        if not _backup_and_install(nebula_bin, nebula_cert_bin):
            return False
        
        # Verify new version
        new_version = get_nebula_version().lstrip('v')
        if new_version == server_version:
            print(f"[agent] ✓ Nebula successfully upgraded to {new_version}")
            return True
        
        print(
            f"[agent] WARNING: Version mismatch after upgrade. "
            f"Expected {server_version}, got {new_version}"
        )
        return False
        
    except httpx.HTTPStatusError as e:
        print(f"[agent] Failed to check version or download: HTTP {e.response.status_code}")
        return False
    except Exception as e:
        print(f"[agent] Failed to update Nebula: {e}")
        return False


def fetch_config(token: str, server_url: str, public_key: str) -> dict:
    url = server_url.rstrip("/") + "/v1/client/config"
    payload = {
        "token": token,
        "public_key": public_key,
        "client_version": os.getenv("CLIENT_VERSION_OVERRIDE", __version__),
        "nebula_version": os.getenv("NEBULA_VERSION_OVERRIDE", get_nebula_version())
    }
    # Allow self-signed certificates in development (set ALLOW_SELF_SIGNED_CERT=false in production)
    verify_ssl = os.getenv("ALLOW_SELF_SIGNED_CERT", "false").lower() != "true"
    with httpx.Client(timeout=30, verify=verify_ssl) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        return r.json()


def calculate_config_hash(config_yaml: str, client_cert_pem: str, ca_chain_pems: list[str]) -> str:
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
    ca_path = CONFIG_PATH.parent / "ca.crt"
    cert_path = CONFIG_PATH.parent / "host.crt"
    
    ca_content = ca_path.read_text() if ca_path.exists() else ""
    cert_content = cert_path.read_text() if cert_path.exists() else ""
    
    hasher = hashlib.sha256()
    hasher.update(config_yaml.encode())
    hasher.update(cert_content.encode())
    hasher.update(ca_content.encode())
    return hasher.hexdigest()


def write_config_and_pki(config_yaml: str, client_cert_pem: str, ca_chain_pems: list[str]) -> bool:
    """Write config and PKI files. Returns True if files changed."""
    # Check if config would actually change
    new_hash = calculate_config_hash(config_yaml, client_cert_pem, ca_chain_pems)
    current_hash = get_current_config_hash()
    
    if new_hash == current_hash:
        print("[agent] Config unchanged, no restart needed")
        return False
    
    print("[agent] Config changed, writing new files")
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(config_yaml)
    # Write certs as files Nebula expects
    ca_path = CONFIG_PATH.parent / "ca.crt"
    cert_path = CONFIG_PATH.parent / "host.crt"
    ca_path.write_text("".join(ca_chain_pems))
    cert_path.write_text(client_cert_pem)
    return True


def get_nebula_pid() -> int:
    """Get Nebula process PID from pidfile or process list"""
    # First try pidfile
    if PIDFILE.exists():
        try:
            pid = int(PIDFILE.read_text().strip())
            # Check if process still exists
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError):
            PIDFILE.unlink(missing_ok=True)
    
    # Fallback: find nebula process by command line
    try:
        result = subprocess.run(
            ["pgrep", "-f", "nebula.*-config.*config.yml"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            pid = int(result.stdout.strip().split('\n')[0])
            # Write to pidfile for future use
            PIDFILE.write_text(str(pid))
            return pid
    except (subprocess.SubprocessError, ValueError):
        pass
    
    return 0


def restart_nebula():
    """Restart the Nebula daemon"""
    print("[agent] Restarting Nebula daemon...")
    
    # Find and stop current nebula process
    pid = get_nebula_pid()
    if pid:
        try:
            print(f"[agent] Stopping Nebula process {pid}")
            os.kill(pid, signal.SIGTERM)
            # Give it a moment to stop gracefully
            time.sleep(2)
            # Check if it's still running
            try:
                os.kill(pid, 0)
                print(f"[agent] Process {pid} still running, sending SIGKILL")
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
            except OSError:
                pass  # Process already stopped
        except OSError as e:
            print(f"[agent] Error stopping Nebula process {pid}: {e}")
        
        # Clean up pidfile
        PIDFILE.unlink(missing_ok=True)
    
    # Only restart if we're running in daemon mode (START_NEBULA=true)
    if os.environ.get("START_NEBULA", "true") == "true":
        print("[agent] Starting new Nebula process...")
        # Start nebula as background process
        proc = subprocess.Popen(
            ["nebula", "-config", str(CONFIG_PATH)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Write new PID
        PIDFILE.write_text(str(proc.pid))
        print(f"[agent] Started Nebula process {proc.pid}")


def run_once(restart_on_change: bool = False):
    token = os.environ["CLIENT_TOKEN"]
    server_url = os.environ.get("SERVER_URL", "http://localhost:8080")
    
    # Check for Nebula version updates first
    try:
        nebula_updated = check_and_update_nebula(server_url)
        if nebula_updated:
            print("[agent] Nebula was updated, will restart with new version")
            restart_on_change = True  # Force restart after upgrade
    except Exception as e:
        print(f"[agent] Nebula update check failed: {e}")
    
    _priv, pub = ensure_keypair()
    data = fetch_config(token, server_url, pub)
    cfg = data["config"]
    client_cert_pem = data.get("client_cert_pem", "")
    ca_chain_pems = data.get("ca_chain_pems", [])
    
    config_changed = write_config_and_pki(cfg, client_cert_pem, ca_chain_pems)
    
    # Restart Nebula if config changed and we're asked to
    if config_changed and restart_on_change:
        restart_nebula()


def run_loop():
    interval_hours = int(os.environ.get("POLL_INTERVAL_HOURS", "24"))
    while True:
        try:
            # In loop mode, always restart on config changes
            run_once(restart_on_change=True)
        except Exception as e:
            print(f"[agent] refresh failed: {e}")
        time.sleep(interval_hours * 3600)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--loop", action="store_true", help="Run in polling loop")
    parser.add_argument("--restart", action="store_true", help="Restart Nebula if config changes (only with --once)")
    args = parser.parse_args()

    if args.once:
        run_once(restart_on_change=args.restart)
    elif args.loop:
        run_loop()
    else:
        run_once()
