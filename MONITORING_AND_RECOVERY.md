# Nebula Process Monitoring & Resilient Recovery

## Overview

The Managed Nebula client agents now include comprehensive process monitoring and resilient recovery capabilities to ensure continuous VPN connectivity with minimal manual intervention. This document describes the monitoring features, configuration options, and troubleshooting procedures.

## Features

### 1. Process Monitoring & Crash Detection

The client continuously monitors the Nebula daemon and detects crashes or unexpected terminations:

- **Detection interval**: Configurable (default: 10 seconds)
- **Crash detection**: Identifies when Nebula process terminates unexpectedly
- **Automatic recovery**: Attempts to restart Nebula automatically
- **Structured logging**: All crash events logged with timestamps

### 2. Automatic Restart with Exponential Backoff

When a crash is detected, the client automatically attempts to restart Nebula:

- **Retry attempts**: Up to 5 consecutive attempts (configurable)
- **Exponential backoff**: 1s → 2s → 4s, maximum 30s between attempts
- **Initialization timeout**: Waits up to 30s for Nebula to fully initialize
- **Idempotent restarts**: Skips restart if Nebula restarts during detection window
- **Administrator alert**: Stops automatic restarts after max failures and alerts admin

### 3. Health Checking

Periodic health checks verify Nebula connectivity:

- **Check interval**: Configurable (default: 60 seconds)
- **Basic check**: Verifies process is running
- **Future enhancements**: Lighthouse connectivity, neighbor handshakes

### 4. Config Fetch with Timeout & Retry

Configuration fetching includes robust error handling:

- **Timeout**: Configurable (default: 30 seconds)
- **Retry logic**: Up to 5 retries with exponential backoff (1s → 2s → 4s → 8s, max 60s)
- **Config caching**: Falls back to cached config when the server is unavailable
- **Failure tracking**: Logs all fetch failures

### 5. Coordinated Recovery

When restarting Nebula, the client follows a coordinated recovery sequence:

- **Wait period**: 10s delay after restart before fetching fresh config
- **Fresh config fetch**: Retrieves latest configuration after restart
- **Config validation**: Validates syntax before restarting to avoid boot loops
- **Full logging**: Timestamps for entire recovery sequence

### 6. Metrics Tracking

The client tracks comprehensive metrics for monitoring and troubleshooting:

- `crash_count`: Total number of Nebula crashes detected
- `disconnect_count`: Number of disconnect events detected
- `restart_count`: Total successful restarts
- `config_fetch_failures`: Number of failed config fetch attempts
- `consecutive_failures`: Current streak of consecutive failures
- `last_crash_time`: Timestamp of most recent crash
- `last_successful_restart`: Timestamp of most recent successful restart

Metrics are persisted to disk and survive agent restarts.

## Configuration

### Environment Variables

All timeouts and retry parameters are configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PROCESS_CHECK_INTERVAL` | `10` | Seconds between process checks |
| `HEALTH_CHECK_INTERVAL` | `60` | Seconds between health checks |
| `CONFIG_FETCH_TIMEOUT` | `30` | Timeout for config fetch requests (seconds) |
| `MAX_RESTART_ATTEMPTS` | `5` | Maximum consecutive restart attempts |
| `MAX_FETCH_RETRIES` | `5` | Maximum config fetch retry attempts |
| `POST_RESTART_WAIT` | `10` | Seconds to wait after restart before fetching fresh config |
| `RESTART_INIT_TIMEOUT` | `30` | Seconds to wait for Nebula to initialize after restart |
| `ENABLE_MONITORING` | `true` | Enable enhanced monitoring mode (Docker/Linux) |

### Example Configuration

#### Docker Compose

```yaml
version: '3.8'

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
      
      # Monitoring configuration
      ENABLE_MONITORING: "true"
      PROCESS_CHECK_INTERVAL: "10"
      HEALTH_CHECK_INTERVAL: "60"
      CONFIG_FETCH_TIMEOUT: "30"
      MAX_RESTART_ATTEMPTS: "5"
      MAX_FETCH_RETRIES: "5"
      POST_RESTART_WAIT: "10"
      RESTART_INIT_TIMEOUT: "30"
    restart: unless-stopped
```

#### Windows Service

Environment variables can be set in the Windows service configuration or via the GUI.

#### Linux Systemd Service

```ini
[Service]
Environment="PROCESS_CHECK_INTERVAL=10"
Environment="HEALTH_CHECK_INTERVAL=60"
Environment="CONFIG_FETCH_TIMEOUT=30"
Environment="MAX_RESTART_ATTEMPTS=5"
```

## Usage

### Docker/Linux Client

#### Enhanced Monitoring Mode (Recommended)

```bash
# Start with monitoring (automatically enabled by default)
python3 agent.py --monitor

# Or explicitly enable via environment
ENABLE_MONITORING=true python3 agent.py --loop
```

#### Legacy Mode (Without Monitoring)

```bash
# Disable monitoring
ENABLE_MONITORING=false python3 agent.py --loop
```

### Windows Client

#### Enhanced Monitoring Mode

```powershell
# Start with monitoring
python agent.py --monitor

# Or use the GUI to enable monitoring
```

#### Legacy Mode

```powershell
# Standard polling loop
python agent.py --loop
```

### Command Line Options

All clients support the following options:

- `--once`: Run once and exit
- `--loop`: Run in continuous polling loop
- `--monitor`: Run in enhanced monitoring mode (recommended)
- `--restart`: Restart Nebula if config changes (only with --once)
- `--status`: Show current status and metrics
- `--version`: Show version information

## Monitoring and Alerts

### Log Messages

The client produces structured log messages for all recovery events:

#### Crash Detection

```
[2024-01-15T10:30:45] CRASH DETECTED: Nebula process not running
[2024-01-15T10:30:45] Attempting automatic recovery...
[2024-01-15T10:30:45] Restart attempt 1/5
```

#### Successful Recovery

```
[2024-01-15T10:30:50] Nebula restarted successfully (PID: 12345)
[2024-01-15T10:30:50] Recovery successful
```

#### Failed Recovery

```
[2024-01-15T10:31:15] ERROR: Failed to restart Nebula after 5 attempts
[2024-01-15T10:31:15] Consecutive failures: 5
[2024-01-15T10:31:15] ALERT: Administrator intervention required!
```

#### Config Fetch Issues

```
[2024-01-15T10:35:00] Config fetch timeout (attempt 1/5)
[2024-01-15T10:35:01] Retrying in 1 seconds...
[2024-01-15T10:35:10] All config fetch attempts failed, trying cached config...
[2024-01-15T10:35:10] Using cached config as fallback
```

### Metrics Files

Metrics are stored in JSON format:

- **Docker/Linux**: `/var/lib/nebula/metrics.json`
- **Windows**: `C:\ProgramData\Nebula\metrics.json`

Example metrics file:

```json
{
  "crash_count": 3,
  "disconnect_count": 1,
  "restart_count": 3,
  "config_fetch_failures": 5,
  "last_crash_time": "2024-01-15T10:30:45",
  "last_successful_restart": "2024-01-15T10:30:50",
  "consecutive_failures": 0
}
```

### Alert Thresholds

The client automatically stops restart attempts and alerts when:

- **Consecutive failures**: Reaches `MAX_RESTART_ATTEMPTS` (default: 5)
- **Recovery failure**: All restart attempts fail
- **Config unavailable**: All fetch retries fail and no cache available

## Troubleshooting

### High Crash Rate

If `crash_count` is increasing rapidly:

1. Check Nebula logs for errors:
   - Docker/Linux: Check docker logs or `/var/log/nebula/`
   - Windows: `C:\ProgramData\Nebula\logs\nebula.log`

2. Verify config validity:
   ```bash
   nebula -test -config /etc/nebula/config.yml
   ```

3. Check system resources (memory, CPU)

4. Review firewall rules and network connectivity

### Config Fetch Failures

If `config_fetch_failures` is high:

1. Verify server connectivity:
   ```bash
   curl -k ${SERVER_URL}/v1/healthz
   ```

2. Check CLIENT_TOKEN is valid

3. Review server logs for authentication issues

4. Verify network/firewall rules allow outbound HTTPS

### Restart Loops

If Nebula restarts repeatedly:

1. Review metrics to identify pattern:
   ```bash
   cat /var/lib/nebula/metrics.json
   ```

2. Check for config validation errors in logs

3. Verify TUN device availability:
   ```bash
   ls -l /dev/net/tun
   ```

4. Check process capabilities (NET_ADMIN for Docker)

### Manual Recovery

If automatic recovery fails:

1. Check metrics and logs to diagnose issue

2. Manually restart the client:
   ```bash
   # Docker
   docker restart nebula-client
   
   # Windows
   net stop NebulaAgent
   net start NebulaAgent
   ```

3. Reset metrics if needed:
   ```bash
   rm /var/lib/nebula/metrics.json
   ```

4. Test config manually:
   ```bash
   nebula -config /etc/nebula/config.yml
   ```

## Implementation Status

### ✅ Docker/Linux Client (Python)

- **Complete**: All monitoring and recovery features implemented
- **Status**: Production ready
- **Testing**: Unit and integration tests available

### ✅ Windows Client (Python)

- **Complete**: All monitoring and recovery features implemented
- **Status**: Production ready
- **Testing**: Unit tests available

### 🚧 macOS Client (Swift)

- **Status**: Partial implementation
- **Implemented**: Basic monitoring via PollingService
- **Pending**: 
  - Enhanced crash detection with exponential backoff
  - Config caching and retry logic
  - Metrics tracking
  - Background monitoring thread
- **Note**: Due to the helper daemon architecture, full implementation requires more extensive changes

## Future Enhancements

### Advanced Health Checks

- Lighthouse connectivity verification
- Neighbor handshake status monitoring
- Network reachability tests
- Latency and packet loss monitoring

### Enhanced Metrics

- Performance metrics (latency, throughput)
- Config change history
- Downtime tracking
- Trend analysis

### Integration

- Prometheus metrics export
- Webhook notifications for alerts
- Syslog integration
- Status API endpoint

## Related Documentation

- [Client README](client/README.md)
- [Windows Client README](windows_client/README.md)
- [macOS Client README](macos_client/README.md)
- [Docker Compose Examples](docker-compose.yml)

## Support

For issues or questions:

1. Check logs for error messages
2. Review metrics file for patterns
3. Consult troubleshooting section above
4. Open GitHub issue with logs and metrics
