---
applies_to:
  - client/**/*
---

# Client Agent Instructions

## Overview
The client is a lightweight Python agent that runs on Nebula VPN nodes. It polls the server for configuration updates, manages certificates, and controls the local Nebula daemon.

## Tech Stack
- **Runtime**: Python 3.11+
- **HTTP Client**: httpx (async support)
- **Certificate Tool**: nebula-cert CLI
- **Deployment**: Docker container with NET_ADMIN capability

## Development Commands

### Running the Client Locally
```bash
cd client
pip install -r requirements.txt

# Set environment variables
export CLIENT_TOKEN="your-token-from-server"
export SERVER_URL="http://localhost:8080"

# Run the agent
python agent.py              # Run once and exit
python agent.py --once       # Same as above
python agent.py --once --restart  # Run once, restart Nebula if config changed
python agent.py --loop       # Continuous polling (production mode)
```

### Running in Docker
```bash
# Build image
docker build -t managed-nebula-client ./client

# Run with environment variables
docker run -d \
  --name nebula-client \
  --cap-add=NET_ADMIN \
  --device /dev/net/tun \
  -e CLIENT_TOKEN="your-token" \
  -e SERVER_URL="http://your-server:8080" \
  -e POLL_INTERVAL_HOURS=24 \
  -e START_NEBULA=true \
  managed-nebula-client
```

### Testing
```bash
cd client
pytest tests/ -v  # If tests exist
```

## Agent Workflow

### Initialization (First Run)
1. Check if keypair exists at `/var/lib/nebula/host.key` and `/var/lib/nebula/host.pub`
2. If not, generate keypair: `nebula-cert keygen -out-key host.key -out-pub host.pub`
3. Read public key from file

### Configuration Fetch
1. POST to `/api/v1/client/config` with:
   - `token`: Client authentication token
   - `public_key`: PEM-encoded public key
2. Server validates token and returns:
   - `config`: Complete Nebula YAML configuration
   - `client_cert_pem`: Signed client certificate
   - `ca_chain_pems`: List of CA certificates (current + previous during rotation)
3. Write files to:
   - `/etc/nebula/config.yml`: Nebula configuration
   - `/etc/nebula/host.crt`: Client certificate
   - `/etc/nebula/ca.crt`: CA certificate chain

### Nebula Daemon Management
1. **Hash-based change detection**: Calculate SHA256 hash of config + certificates
2. **Graceful restart**: SIGTERM → SIGKILL fallback with 2-second timeout
3. **PID tracking**: Maintain `/var/lib/nebula/nebula.pid` for process management
4. **Start Nebula**: `nebula -config /etc/nebula/config.yml` (background process)

### Polling Loop (Automatic Restart)
1. Sleep for `POLL_INTERVAL_HOURS` (default 24 hours)
2. Fetch configuration from server
3. Compare hash with current config files
4. **Auto-restart Nebula only if config actually changed**
5. Log restart events for debugging

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLIENT_TOKEN` | ✅ Yes | - | Authentication token from server |
| `SERVER_URL` | ✅ Yes | - | Server API endpoint (e.g., http://server:8080) |
| `POLL_INTERVAL_HOURS` | No | `24` | How often to check for updates |
| `START_NEBULA` | No | `true` | Whether to start Nebula daemon after config |

## Key Patterns and Conventions

### Error Handling
- Retry failed API requests with exponential backoff
- Log all errors but don't crash - retry on next poll
- Handle network failures gracefully
- Validate server responses before writing files

Example:
```python
import httpx
import time

def fetch_config_with_retry(token: str, public_key: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            response = httpx.post(
                f"{SERVER_URL}/api/v1/client/config",
                json={"token": token, "public_key": public_key},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt
            print(f"Retry {attempt + 1} in {wait_time}s: {e}")
            time.sleep(wait_time)
```

### File Operations
- **Atomic writes**: Write to temp file, then rename
- **Backup old files**: Keep backup before overwriting
- **Validate before write**: Ensure config is valid YAML
- **Proper permissions**: Ensure private keys are mode 600

Example:
```python
import os
import tempfile

def atomic_write(path: str, content: str, mode: int = 0o644):
    """Write file atomically with proper permissions."""
    dir_path = os.path.dirname(path)
    
    # Create backup if file exists
    if os.path.exists(path):
        backup_path = f"{path}.bak"
        os.rename(path, backup_path)
    
    # Write to temp file in same directory
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, text=True)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        os.chmod(tmp_path, mode)
        os.rename(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
```

### Certificate Management
- **Never expose private key**: Keep `host.key` mode 600
- **Validate certificates**: Check expiry before using
- **Handle CA rotation**: Accept multiple CA certs in chain
- **Public key format**: PEM-encoded, extracted from `host.pub` file

### Process Management
- **Clean shutdown**: Catch signals (SIGTERM, SIGINT) in entrypoint.sh
- **Graceful restart**: SIGTERM → 2s wait → SIGKILL if needed
- **PID tracking**: Store/read from `/var/lib/nebula/nebula.pid`
- **Process detection**: Fallback to `pgrep -f "nebula.*config.yml"`
- **Background processes**: Nebula runs detached, agent manages it

Example:
```python
import subprocess
import signal
import sys

nebula_process = None

def stop_nebula():
    global nebula_process
    if nebula_process:
        print("Stopping Nebula daemon...")
        nebula_process.terminate()
        nebula_process.wait(timeout=10)
        nebula_process = None

def start_nebula():
    global nebula_process
    stop_nebula()
    print("Starting Nebula daemon...")
    nebula_process = subprocess.Popen(
        ["nebula", "-config", "/etc/nebula/config.yml"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

def signal_handler(signum, frame):
    print(f"Received signal {signum}, shutting down...")
    stop_nebula()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

### Logging
- Log all important events (config fetch, cert update, Nebula restart)
- Include timestamps
- Log errors with stack traces
- Use structured logging if possible

### Common Pitfalls to Avoid
- ❌ Don't expose private keys in logs or environment
- ❌ Don't crash on network errors - retry gracefully
- ❌ Don't start Nebula if config is invalid
- ❌ Don't write files synchronously without error handling
- ❌ Don't ignore certificate expiry warnings
- ❌ Don't poll too frequently - respect server resources
- ❌ Don't forget to close file descriptors

## File Structure
```
client/
├── agent.py              # Main agent script
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container build instructions
├── entrypoint.sh        # Container startup script
└── README.md            # Client documentation
```

## Security Considerations

### Private Key Security
- Generate keypair locally (never send private key)
- Store with mode 600 (read/write owner only)
- Never log or transmit private key
- Rotate keypair if compromised

### Token Security
- Store token in environment variable (not in code)
- Never log token value
- Rotate token if compromised
- Validate token before each API call

### Network Security
- Use HTTPS for production (SERVER_URL)
- Validate TLS certificates
- Don't disable certificate verification
- Handle network errors gracefully

### Container Security
- Run as non-root user when possible
- Only grant necessary capabilities (NET_ADMIN)
- Mount only required devices (/dev/net/tun)
- Keep base image updated

## Docker Deployment

### Requirements
- **Capability**: `--cap-add=NET_ADMIN` (required for TUN device)
- **Device**: `--device /dev/net/tun` (virtual network interface)
- **Volumes** (optional): Mount `/var/lib/nebula` to persist keypair

### Example Docker Compose
```yaml
services:
  nebula-client:
    image: managed-nebula-client:latest
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    environment:
      CLIENT_TOKEN: "${CLIENT_TOKEN}"
      SERVER_URL: "${SERVER_URL}"
      POLL_INTERVAL_HOURS: "24"
      START_NEBULA: "true"
    restart: unless-stopped
    volumes:
      - ./nebula-data:/var/lib/nebula  # Optional: persist keypair
```

## Troubleshooting

### Common Issues

**Client can't connect to server**
- Check `SERVER_URL` is correct
- Verify network connectivity
- Check firewall rules
- Verify token is valid

**Nebula won't start**
- Check config syntax: `nebula -test -config /etc/nebula/config.yml`
- Verify TUN device exists: `ls -l /dev/net/tun`
- Check NET_ADMIN capability
- Review Nebula logs

**Certificate errors**
- Verify CA certificate is valid
- Check certificate expiry
- Ensure keypair matches certificate
- Verify public key was sent to server

**Config not updating**
- Check poll interval
- Verify server is reachable
- Check for error logs
- Manually trigger update

## Testing the Client

### Manual Testing
```bash
# Test config fetch
curl -X POST http://localhost:8080/api/v1/client/config \
  -H "Content-Type: application/json" \
  -d '{"token": "your-token", "public_key": "..."}'

# Test Nebula config
nebula -test -config /etc/nebula/config.yml

# Test connectivity
nebula-cert print -path /etc/nebula/host.crt
```

### Integration Testing
1. Start server with test database
2. Create client and generate token
3. Start client agent with token
4. Verify client receives config
5. Verify Nebula starts successfully
6. Test periodic polling

## Performance Considerations
- Default poll interval (24h) is sufficient for most deployments
- Reduce polling frequency for large deployments
- Consider using webhooks for immediate updates (future enhancement)
- Monitor network bandwidth usage
- Keep agent lightweight - minimal CPU/memory footprint
