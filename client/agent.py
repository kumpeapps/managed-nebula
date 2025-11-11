import argparse
import os
import time
from pathlib import Path
import httpx
import subprocess


STATE_DIR = Path(os.getenv("NEBULA_STATE_DIR", "/var/lib/nebula"))
CONFIG_PATH = Path("/etc/nebula/config.yml")
KEY_PATH = STATE_DIR / "host.key"
PUB_PATH = STATE_DIR / "host.pub"


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
    url = server_url.rstrip("/") + "/api/v1/client/config"
    with httpx.Client(timeout=30) as client:
        r = client.post(url, json={"token": token, "public_key": public_key})
        r.raise_for_status()
        return r.json()


def write_config_and_pki(config_yaml: str, client_cert_pem: str, ca_chain_pems: list[str]):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(config_yaml)
    # Write certs as files Nebula expects
    ca_path = Path("/etc/nebula/ca.crt")
    cert_path = Path("/etc/nebula/host.crt")
    ca_path.write_text("".join(ca_chain_pems))
    cert_path.write_text(client_cert_pem)


def run_once():
    token = os.environ["CLIENT_TOKEN"]
    server_url = os.environ.get("SERVER_URL", "http://localhost:8080")
    _priv, pub = ensure_keypair()
    data = fetch_config(token, server_url, pub)
    cfg = data["config"]
    client_cert_pem = data.get("client_cert_pem", "")
    ca_chain_pems = data.get("ca_chain_pems", [])
    write_config_and_pki(cfg, client_cert_pem, ca_chain_pems)


def run_loop():
    interval_hours = int(os.environ.get("POLL_INTERVAL_HOURS", "24"))
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"[agent] refresh failed: {e}")
        time.sleep(interval_hours * 3600)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()

    if args.once:
        run_once()
    elif args.loop:
        run_loop()
    else:
        run_once()
