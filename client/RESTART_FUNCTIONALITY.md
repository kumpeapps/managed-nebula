# Nebula Client Agent - Restart Functionality

The Nebula client agent now includes automatic restart functionality to ensure the Nebula daemon is reloaded when configuration changes are detected.

## How It Works

### Config Change Detection
- **Hash-based detection**: The agent calculates SHA256 hashes of all config files (config.yml, ca.crt, host.crt)
- **Efficient polling**: Only restarts Nebula when actual content changes, not on every poll
- **Comprehensive coverage**: Monitors config file AND certificate changes

### Restart Process
1. **Graceful shutdown**: Sends SIGTERM to current Nebula process
2. **Fallback kill**: Uses SIGKILL if process doesn't stop within 2 seconds
3. **PID tracking**: Maintains `/var/lib/nebula/nebula.pid` for reliable process management
4. **Clean restart**: Starts new Nebula process with updated config

### Process Management
- **PID file**: Stores Nebula process ID in `/var/lib/nebula/nebula.pid`
- **Process detection**: Falls back to `pgrep` if PID file is missing or stale
- **Signal handling**: Proper cleanup on container shutdown

## Usage Modes

### Automatic Mode (Default)
```bash
# In container - automatic restart on config changes every 24 hours
python3 agent.py --loop
```

### Manual Mode
```bash
# One-time config update without restart
python3 agent.py --once

# One-time config update WITH restart if changed
python3 agent.py --once --restart
```

### Environment Variables
- `POLL_INTERVAL_HOURS`: Polling interval (default: 24)
- `START_NEBULA`: Whether to start Nebula daemon (default: true)
- `CLIENT_TOKEN`: Authentication token
- `SERVER_URL`: Management server URL

## Container Integration

The Docker entrypoint (`entrypoint.sh`) now properly manages both the agent poller and Nebula daemon:

1. **Startup**: Downloads initial config, starts Nebula daemon
2. **Background polling**: Runs agent in loop mode for periodic updates
3. **Signal handling**: Gracefully shuts down both processes on SIGTERM/SIGINT
4. **PID tracking**: Maintains PID files for reliable process management

## Testing

### Integration Test
```bash
cd client/
./test_integration.sh
```

### Unit Tests
```bash
cd client/
python3 test_restart.py
```

## Behavior Changes

### Before
- Config files updated every 24 hours
- Nebula daemon continued running with old config
- Manual restart required to pick up changes

### After
- Config files still updated every 24 hours
- **Nebula daemon automatically restarted when config changes**
- Hash comparison prevents unnecessary restarts
- Graceful process management with proper cleanup

## Debugging

### Check if restart is working
```bash
# Look for restart messages in logs
docker logs nebula-client | grep "Restarting Nebula daemon"

# Check PID file
cat /var/lib/nebula/nebula.pid

# Verify Nebula process
ps aux | grep nebula
```

### Force config refresh with restart
```bash
# From inside container
python3 /app/agent.py --once --restart
```

## Compatibility

- **Backward compatible**: No breaking changes to existing functionality
- **Optional restart**: Works in config-only mode (`START_NEBULA=false`)
- **Robust fallbacks**: Multiple methods for process detection and management