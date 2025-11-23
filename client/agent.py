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


def fetch_config(token: str, server_url: str, public_key: str) -> dict:
    url = server_url.rstrip("/") + "/v1/client/config"
    with httpx.Client(timeout=30) as client:
        r = client.post(url, json={"token": token, "public_key": public_key})
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
