import argparse
import os
import time
import signal
import hashlib
import json
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import httpx
import subprocess

__version__ = "1.0.0"

STATE_DIR = Path(os.getenv("NEBULA_STATE_DIR", "/var/lib/nebula"))
CONFIG_PATH = Path("/etc/nebula/config.yml")
KEY_PATH = STATE_DIR / "host.key"
PUB_PATH = STATE_DIR / "host.pub"
PIDFILE = STATE_DIR / "nebula.pid"
METRICS_FILE = STATE_DIR / "metrics.json"
CACHED_CONFIG_FILE = STATE_DIR / "cached_config.json"

# Configuration with environment variable defaults
PROCESS_CHECK_INTERVAL = int(os.getenv("PROCESS_CHECK_INTERVAL", "10"))  # seconds
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))  # seconds
CONFIG_FETCH_TIMEOUT = int(os.getenv("CONFIG_FETCH_TIMEOUT", "30"))  # seconds
MAX_RESTART_ATTEMPTS = int(os.getenv("MAX_RESTART_ATTEMPTS", "5"))
MAX_FETCH_RETRIES = int(os.getenv("MAX_FETCH_RETRIES", "5"))
POST_RESTART_WAIT = int(os.getenv("POST_RESTART_WAIT", "10"))  # seconds
RESTART_INIT_TIMEOUT = int(os.getenv("RESTART_INIT_TIMEOUT", "30"))  # seconds

# Metrics tracking
class Metrics:
    def __init__(self):
        self.crash_count = 0
        self.disconnect_count = 0
        self.restart_count = 0
        self.config_fetch_failures = 0
        self.last_crash_time = None
        self.last_successful_restart = None
        self.consecutive_failures = 0
        
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
    def from_dict(cls, data):
        m = cls()
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
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            METRICS_FILE.write_text(json.dumps(self.to_dict(), indent=2))
        except Exception as e:
            # Use print for consistency across platforms (no logger dependency)
            print(f"[agent] Warning: Failed to save metrics: {e}")
    
    @classmethod
    def load(cls):
        """Load metrics from file"""
        try:
            if METRICS_FILE.exists():
                data = json.loads(METRICS_FILE.read_text())
                return cls.from_dict(data)
        except Exception as e:
            # Use print for consistency across platforms (no logger dependency)
            print(f"[agent] Warning: Failed to load metrics: {e}")
        return cls()

metrics = Metrics.load()

# Thread-safe access to metrics from both main loop and monitor thread
metrics_lock = threading.Lock()


def compute_backoff(attempt: int, base: int = 1, cap: int = 60) -> int:
    """
    Compute exponential backoff delay in seconds.
    attempt is 0-based: attempt 0 -> 1s, attempt 1 -> 2s, attempt 2 -> 4s, etc.
    Returns min(base * 2^attempt, cap)
    """
    return min(base * (2 ** attempt), cap)


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


def save_cached_config(config_data: dict):
    """Cache config for fallback when server is unavailable"""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        CACHED_CONFIG_FILE.write_text(json.dumps(config_data, indent=2))
        print("[agent] Config cached successfully")
    except Exception as e:
        print(f"[agent] Warning: Failed to cache config: {e}")


def load_cached_config() -> Optional[dict]:
    """Load cached config as fallback"""
    try:
        if CACHED_CONFIG_FILE.exists():
            return json.loads(CACHED_CONFIG_FILE.read_text())
    except Exception as e:
        print(f"[agent] Warning: Failed to load cached config: {e}")
    return None


def fetch_config_with_retry(token: str, server_url: str, public_key: str) -> Optional[dict]:
    """Fetch config with exponential backoff retry logic"""
    global metrics
    
    url = server_url.rstrip("/") + "/v1/client/config"
    payload = {
        "token": token,
        "public_key": public_key,
        "client_version": os.getenv("CLIENT_VERSION_OVERRIDE", __version__),
        "nebula_version": os.getenv("NEBULA_VERSION_OVERRIDE", get_nebula_version())
    }
    verify_ssl = os.getenv("ALLOW_SELF_SIGNED_CERT", "false").lower() != "true"
    
    for attempt in range(MAX_FETCH_RETRIES):
        try:
            print(f"[agent] Fetching config (attempt {attempt + 1}/{MAX_FETCH_RETRIES})...")
            with httpx.Client(timeout=CONFIG_FETCH_TIMEOUT, verify=verify_ssl) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
                config_data = r.json()
                
                # Cache successful config
                save_cached_config(config_data)
                
                # Reset failure counter on success
                with metrics_lock:
                    metrics.config_fetch_failures = 0
                    metrics.save()
                
                return config_data
                
        except httpx.TimeoutException:
            with metrics_lock:
                metrics.config_fetch_failures += 1
            print(f"[agent] Config fetch timeout (attempt {attempt + 1}/{MAX_FETCH_RETRIES})")
            
        except httpx.HTTPError as e:
            with metrics_lock:
                metrics.config_fetch_failures += 1
            print(f"[agent] HTTP error during config fetch: {e} (attempt {attempt + 1}/{MAX_FETCH_RETRIES})")
            
        except Exception as e:
            with metrics_lock:
                metrics.config_fetch_failures += 1
            print(f"[agent] Error fetching config: {e} (attempt {attempt + 1}/{MAX_FETCH_RETRIES})")
        
        # Exponential backoff: 1s, 2s, 4s, 8s, max 60s
        if attempt < MAX_FETCH_RETRIES - 1:
            wait_time = min(2 ** attempt, 60)
            print(f"[agent] Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    
    # All retries failed
    with metrics_lock:
        metrics.save()
    print("[agent] All config fetch attempts failed, trying cached config...")
    cached = load_cached_config()
    if cached:
        print("[agent] Using cached config as fallback")
        return cached
    
    print("[agent] ERROR: No cached config available")
    return None


def fetch_config(token: str, server_url: str, public_key: str) -> dict:
    """Fetch config (backwards compatible wrapper)"""
    result = fetch_config_with_retry(token, server_url, public_key)
    if result is None:
        raise Exception("Failed to fetch config after all retries and no cache available")
    return result


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
    """Get Nebula process PID from pidfile or /proc filesystem"""
    # First try pidfile
    if PIDFILE.exists():
        try:
            pid = int(PIDFILE.read_text().strip())
            # Check if process still exists
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError):
            PIDFILE.unlink(missing_ok=True)
    
    # Fallback: scan /proc for nebula process by checking command lines
    try:
        for proc_dir in Path("/proc").iterdir():
            if not proc_dir.is_dir():
                continue
            try:
                pid = int(proc_dir.name)
                cmdline_file = proc_dir / "cmdline"
                if cmdline_file.exists():
                    cmdline = cmdline_file.read_text()
                    # /proc/[pid]/cmdline uses null bytes as separators
                    if "nebula" in cmdline and "config.yml" in cmdline:
                        # Verify process still exists
                        os.kill(pid, 0)
                        # Write to pidfile for future use
                        PIDFILE.write_text(str(pid))
                        return pid
            except (ValueError, OSError):
                # Not a valid pid directory or process is gone
                continue
    except (OSError, FileNotFoundError, PermissionError, UnicodeError):
        # /proc might not be available or readable on some systems
        pass
    
    return 0


def is_nebula_running() -> bool:
    """Check if Nebula process is currently running"""
    pid = get_nebula_pid()
    if pid == 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def validate_config() -> bool:
    """Validate Nebula config syntax before starting"""
    if not CONFIG_PATH.exists():
        print("[agent] Config file does not exist")
        return False
    
    try:
        # Security note: nebula binary and CONFIG_PATH are trusted system paths, not user-controlled
        result = subprocess.run(
            ["nebula", "-test", "-config", str(CONFIG_PATH)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True
        else:
            print(f"[agent] Config validation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[agent] Error validating config: {e}")
        return False


def restart_nebula_with_backoff() -> bool:
    """Restart Nebula with exponential backoff and failure tracking"""
    global metrics
    
    # Validate config before attempting restart
    if not validate_config():
        print("[agent] Skipping restart due to invalid config")
        return False
    
    attempts = 0
    while attempts < MAX_RESTART_ATTEMPTS:
        attempts += 1
        
        # Log restart attempt
        timestamp = datetime.now().isoformat()
        print(f"[agent] [{timestamp}] Restart attempt {attempts}/{MAX_RESTART_ATTEMPTS}")
        
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
        
        # Only restart if we're running in daemon mode
        if os.environ.get("START_NEBULA", "true") != "true":
            print("[agent] START_NEBULA=false, not restarting")
            return False
        
        # Start nebula as background process
        # Security note: nebula binary and CONFIG_PATH are trusted system paths, not user-controlled
        print("[agent] Starting new Nebula process...")
        proc = subprocess.Popen(
            ["nebula", "-config", str(CONFIG_PATH)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Write new PID
        PIDFILE.write_text(str(proc.pid))
        print(f"[agent] Started Nebula process {proc.pid}")
        
        # Wait for Nebula to initialize (up to RESTART_INIT_TIMEOUT seconds)
        print(f"[agent] Waiting {RESTART_INIT_TIMEOUT}s for Nebula to initialize...")
        start_time = time.time()
        initialized = False
        
        while (time.time() - start_time) < RESTART_INIT_TIMEOUT:
            time.sleep(1)
            if is_nebula_running():
                # Check if process is actually the one we started
                current_pid = get_nebula_pid()
                if current_pid == proc.pid:
                    initialized = True
                    break
        
        if initialized:
            # Restart successful
            with metrics_lock:
                metrics.restart_count += 1
                metrics.consecutive_failures = 0
                metrics.last_successful_restart = datetime.now()
                metrics.save()
            
            timestamp = datetime.now().isoformat()
            print(f"[agent] [{timestamp}] Nebula restarted successfully (PID: {proc.pid})")
            return True
        else:
            # Restart failed - check if process exited with error
            try:
                exit_code = proc.poll()
                if exit_code is not None:
                    # Process already exited, try to get output
                    try:
                        stdout, stderr = proc.communicate(timeout=1)
                        if stderr:
                            print(f"[agent] Nebula stderr: {stderr.decode().strip()}")
                        if stdout:
                            print(f"[agent] Nebula stdout: {stdout.decode().strip()}")
                    except:
                        pass
                    print(f"[agent] Nebula process exited with code {exit_code}")
            except:
                pass
            
            with metrics_lock:
                metrics.consecutive_failures += 1
            print(f"[agent] Restart attempt {attempts} failed - Nebula did not start within {RESTART_INIT_TIMEOUT}s")
            
            # Exponential backoff: 1s, 2s, 4s, max 30s
            if attempts < MAX_RESTART_ATTEMPTS:
                wait_time = min(2 ** (attempts - 1), 30)
                print(f"[agent] Waiting {wait_time}s before next attempt...")
                time.sleep(wait_time)
    
    # All restart attempts failed
    with metrics_lock:
        metrics.save()
    timestamp = datetime.now().isoformat()
    print(f"[agent] [{timestamp}] ERROR: Failed to restart Nebula after {MAX_RESTART_ATTEMPTS} attempts")
    with metrics_lock:
        print(f"[agent] Consecutive failures: {metrics.consecutive_failures}")
    print(f"[agent] ALERT: Administrator intervention required!")
    return False


def restart_nebula():
    """Restart the Nebula daemon (legacy function for compatibility)"""
    restart_nebula_with_backoff()


def run_once(restart_on_change: bool = False):
    token = os.environ.get("CLIENT_TOKEN")
    if not token:
        raise ValueError("CLIENT_TOKEN environment variable is required")
    server_url = os.environ.get("SERVER_URL", "http://localhost:8080")
    
    # Check for Nebula version updates first
    nebula_updated = False
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
    
    # Restart Nebula if config changed or if binary was updated
    if restart_on_change and (config_changed or nebula_updated):
        timestamp = datetime.now().isoformat()
        print(f"[agent] [{timestamp}] Coordinated recovery: restarting Nebula")
        
        if restart_nebula_with_backoff():
            # Wait after restart, then fetch fresh config
            print(f"[agent] Waiting {POST_RESTART_WAIT}s before fetching fresh config...")
            time.sleep(POST_RESTART_WAIT)
            
            try:
                print("[agent] Fetching fresh config after restart...")
                fresh_data = fetch_config(token, server_url, pub)
                fresh_cfg = fresh_data["config"]
                fresh_cert_pem = fresh_data.get("client_cert_pem", "")
                fresh_ca_pems = fresh_data.get("ca_chain_pems", [])
                
                # Check if fresh config differs from what we just wrote
                fresh_changed = write_config_and_pki(fresh_cfg, fresh_cert_pem, fresh_ca_pems)
                if fresh_changed:
                    print("[agent] Fresh config differs, restarting again...")
                    restart_nebula_with_backoff()
            except Exception as e:
                print(f"[agent] Failed to fetch fresh config after restart: {e}")
                print("[agent] Continuing with existing config")
        else:
            print("[agent] Failed to restart Nebula")


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
    # - Check lighthouse connectivity via nebula stats/info endpoint
    # - Verify neighbor handshakes
    # For now, if process is running, consider it healthy
    return True


def monitor_nebula_process():
    """
    Continuously monitor Nebula process and restart on crash.
    This runs in the background during run_loop_with_monitoring.
    """
    global metrics
    
    print(f"[agent] Starting process monitor (check interval: {PROCESS_CHECK_INTERVAL}s)")
    
    last_health_check = time.time()
    
    while True:
        try:
            # Check if process is running
            if not is_nebula_running():
                # Process crashed!
                timestamp = datetime.now().isoformat()
                print(f"[agent] [{timestamp}] CRASH DETECTED: Nebula process not running")
                
                with metrics_lock:
                    metrics.crash_count += 1
                    metrics.last_crash_time = datetime.now()
                    metrics.consecutive_failures += 1
                    metrics.save()
                
                # Check if we've exceeded max consecutive failures
                with metrics_lock:
                    consecutive_fails = metrics.consecutive_failures
                if consecutive_fails >= MAX_RESTART_ATTEMPTS:
                    timestamp = datetime.now().isoformat()
                    print(f"[agent] [{timestamp}] ALERT: Too many consecutive failures ({consecutive_fails})")
                    print(f"[agent] Stopping automatic restarts. Administrator intervention required.")
                    with metrics_lock:
                        print(f"[agent] Metrics: {metrics.to_dict()}")
                    # Sleep longer before checking again
                    time.sleep(300)  # 5 minutes
                    continue
                
                # Attempt recovery
                print(f"[agent] Attempting automatic recovery...")
                if restart_nebula_with_backoff():
                    print(f"[agent] Recovery successful")
                else:
                    print(f"[agent] Recovery failed")
            
            # Periodic health check (in addition to process check)
            current_time = time.time()
            if current_time - last_health_check >= HEALTH_CHECK_INTERVAL:
                last_health_check = current_time
                
                if is_nebula_running() and not check_nebula_health():
                    # Process is running but unhealthy
                    timestamp = datetime.now().isoformat()
                    print(f"[agent] [{timestamp}] Health check failed, restarting Nebula")
                    
                    with metrics_lock:
                        metrics.disconnect_count += 1
                    metrics.save()
                    
                    restart_nebula_with_backoff()
        
        except Exception as e:
            print(f"[agent] Error in process monitor: {e}")
        
        # Sleep before next check
        time.sleep(PROCESS_CHECK_INTERVAL)


def run_loop():
    interval_hours = int(os.environ.get("POLL_INTERVAL_HOURS", "24"))
    while True:
        try:
            # In loop mode, always restart on config changes
            run_once(restart_on_change=True)
        except Exception as e:
            print(f"[agent] refresh failed: {e}")
        time.sleep(interval_hours * 3600)


def run_loop_with_monitoring():
    """
    Run in continuous polling loop with process monitoring.
    This is the enhanced mode with resilient recovery.
    """
    import threading
    import sys
    
    # Force flush to ensure we see output immediately
    sys.stdout.flush()
    sys.stderr.flush()
    
    print("[agent] Starting enhanced mode with process monitoring and resilient recovery", flush=True)
    print(f"[agent] Configuration:")
    print(f"  - Process check interval: {PROCESS_CHECK_INTERVAL}s")
    print(f"  - Health check interval: {HEALTH_CHECK_INTERVAL}s")
    print(f"  - Config fetch timeout: {CONFIG_FETCH_TIMEOUT}s")
    print(f"  - Max restart attempts: {MAX_RESTART_ATTEMPTS}")
    print(f"  - Max fetch retries: {MAX_FETCH_RETRIES}")
    print(f"  - Post-restart wait: {POST_RESTART_WAIT}s")
    
    # Ensure Nebula is started initially before beginning monitoring
    print("[agent] Performing initial startup check...")
    if not is_nebula_running():
        print("[agent] Nebula not running, performing initial startup...")
        if not restart_nebula_with_backoff():
            print("[agent] ERROR: Failed to start Nebula during initial startup")
            print("[agent] Will retry via monitoring loop...")
    else:
        print("[agent] Nebula already running")
    
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
            print(f"[agent] Config refresh failed: {e}")
            # Don't crash the loop, just log and continue
        
        # Sleep for the poll interval
        time.sleep(interval_hours * 3600)


if __name__ == "__main__":
    import sys
    # Ensure unbuffered output for immediate logging visibility
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)
    
    print(f"[agent] Python agent starting (PID: {os.getpid()})", flush=True)
    
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--once", action="store_true", help="Run once and exit")
        parser.add_argument("--loop", action="store_true", help="Run in polling loop")
        parser.add_argument("--monitor", action="store_true", help="Run in enhanced monitoring mode (recommended)")
        parser.add_argument("--restart", action="store_true", help="Restart Nebula if config changes (only with --once)")
        args = parser.parse_args()
        
        print(f"[agent] Parsed args: once={args.once}, monitor={args.monitor}, loop={args.loop}", flush=True)

        if args.once:
            run_once(restart_on_change=args.restart)
        elif args.monitor:
            print("[agent] Entering monitor mode...", flush=True)
            run_loop_with_monitoring()
        elif args.loop:
            run_loop()
        else:
            run_once()
    except KeyboardInterrupt:
        print("[agent] Received interrupt signal, exiting...", flush=True)
    except Exception as e:
        print(f"[agent] FATAL ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
