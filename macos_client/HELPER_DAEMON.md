# Nebula Helper Daemon Architecture

## Overview

The macOS client uses a privileged helper daemon to manage Nebula without requiring repeated authentication prompts. This provides a seamless user experience while maintaining security.

## Architecture

### Components

1. **ManagedNebula.app** (User application)
   - Runs in user space without elevated privileges
   - Provides UI for configuration and control
   - Communicates with helper daemon via file-based IPC

2. **nebula-helper.sh** (Helper daemon)
   - Runs as root via LaunchDaemon
   - Manages Nebula process lifecycle (start/stop/status)
   - Listens for commands on `/tmp/nebula-control`

3. **Nebula daemon**
   - Started/stopped by helper daemon with root privileges
   - Creates TUN interfaces (requires root on macOS)
   - Logs to `/var/log/nebula.log`

### Communication Flow

```
User App                Helper Daemon (root)         Nebula Process
    |                           |                           |
    |--[write "start"]--------->|                           |
    |   /tmp/nebula-control     |                           |
    |                           |--[fork/exec]------------->|
    |                           |                           |
    |                           |<-[PID]-------------------|
    |                           |  (stores in /var/run)     |
    |                           |                           |
    |--[write "stop"]---------->|                           |
    |                           |--[kill PID]-------------->|
    |                           |                           X
```

### IPC Protocol

The app and helper daemon communicate via simple file-based commands:

**Commands** (written to `/tmp/nebula-control`):
- `start` - Start Nebula daemon
- `stop` - Stop Nebula daemon  
- `restart` - Restart Nebula daemon
- `status` - Check if Nebula is running (writes result to `/tmp/nebula-control.status`)

**Status Response**:
- `running` - Nebula process is active
- `stopped` - Nebula process is not running

## Installation

The PKG installer handles all setup:

1. Copies `nebula-helper.sh` to `/usr/local/bin/`
2. Installs LaunchDaemon plist to `/Library/LaunchDaemons/com.managednebula.helper.plist`
3. Creates IPC control file `/tmp/nebula-control` with world-writable permissions
4. Loads helper daemon: `launchctl load /Library/LaunchDaemons/com.managednebula.helper.plist`

### Post-Installation

The helper daemon:
- Starts automatically on boot (`RunAtLoad: true`)
- Restarts if it crashes (`KeepAlive: true`)
- Runs as root (LaunchDaemon context)
- Logs to `/var/log/nebula-helper.log`

## Security Considerations

### File Permissions

- `/tmp/nebula-control` - World-writable (0666) for IPC
  - Any user can send commands, but only affects local system
  - Alternative: Use Unix socket with group permissions for multi-user systems

- `/Library/LaunchDaemons/com.managednebula.helper.plist` - Root-owned (0644)
  - Prevents tampering with daemon configuration

- `/usr/local/bin/nebula-helper.sh` - Root-owned, executable (0755)
  - Prevents unauthorized modification

### Process Isolation

- Helper daemon runs in separate process from user app
- Nebula runs as child of helper daemon with root privileges
- User app has no direct access to Nebula process

### Attack Surface

**Mitigated Risks:**
- ✅ No shell injection - commands are fixed strings, not arbitrary
- ✅ No privilege escalation - user app already has no privileges
- ✅ No config injection - helper reads config from fixed path `/etc/nebula/config.yml`

**Potential Concerns:**
- ⚠️ Local DoS - Any user can start/stop Nebula (intentional for single-user systems)
- ⚠️ Config tampering - User app writes config to `/etc/nebula/` (requires app to be malicious)

**Recommended for Multi-User Systems:**
- Use Unix socket with group-based access control
- Restrict config writes to admin group
- Add authentication token to IPC protocol

## Debugging

### Check Helper Daemon Status

```bash
# Is helper daemon running?
sudo launchctl list | grep managednebula

# View helper daemon logs
sudo tail -f /var/log/nebula-helper.log
sudo tail -f /var/log/nebula-helper.error.log

# View Nebula logs
sudo tail -f /var/log/nebula.log
```

### Manual Control

```bash
# Start Nebula
echo "start" > /tmp/nebula-control

# Stop Nebula
echo "stop" > /tmp/nebula-control

# Check status
echo "status" > /tmp/nebula-control
cat /tmp/nebula-control.status
```

### Reload Helper Daemon

```bash
# Unload daemon
sudo launchctl unload /Library/LaunchDaemons/com.managednebula.helper.plist

# Reload daemon
sudo launchctl load /Library/LaunchDaemons/com.managednebula.helper.plist
```

### Uninstall

```bash
# Stop and unload helper daemon
sudo launchctl unload /Library/LaunchDaemons/com.managednebula.helper.plist

# Remove files
sudo rm /Library/LaunchDaemons/com.managednebula.helper.plist
sudo rm /usr/local/bin/nebula-helper.sh
sudo rm /tmp/nebula-control
sudo rm /tmp/nebula-control.status
```

## Troubleshooting

### Nebula Won't Start

1. Check if helper daemon is running:
   ```bash
   sudo launchctl list | grep managednebula
   ```

2. Check helper daemon logs:
   ```bash
   sudo tail -50 /var/log/nebula-helper.log
   ```

3. Verify config file exists:
   ```bash
   ls -la /etc/nebula/config.yml
   ```

4. Test manual start:
   ```bash
   echo "start" > /tmp/nebula-control
   sleep 2
   pgrep -f "nebula -config"
   ```

### Helper Daemon Not Running

1. Check LaunchDaemon plist:
   ```bash
   sudo plutil -lint /Library/LaunchDaemons/com.managednebula.helper.plist
   ```

2. Load manually:
   ```bash
   sudo launchctl load -w /Library/LaunchDaemons/com.managednebula.helper.plist
   ```

3. Check system logs:
   ```bash
   log show --predicate 'process == "launchd"' --last 10m | grep managednebula
   ```

### Commands Not Working

1. Check IPC file permissions:
   ```bash
   ls -la /tmp/nebula-control
   # Should be: -rw-rw-rw- (666)
   ```

2. Fix permissions:
   ```bash
   sudo chmod 666 /tmp/nebula-control
   ```

3. Verify helper daemon is watching file:
   ```bash
   sudo tail -f /var/log/nebula-helper.log &
   echo "status" > /tmp/nebula-control
   ```

## Future Enhancements

### Planned Improvements

1. **XPC Service** - Replace file-based IPC with proper XPC for better security and reliability
2. **SMJobBless** - Use Apple's privileged helper tool API for proper privilege separation
3. **Authentication** - Add per-request authentication tokens to IPC protocol
4. **Audit Logging** - Log all commands with timestamps and user identifiers
5. **Config Validation** - Validate config changes before applying to prevent misconfigurations

### Known Limitations

- File-based IPC has race conditions (polling interval: 1 second)
- World-writable control file allows any local user to control Nebula
- No command queueing - concurrent commands may conflict
- Status checks require polling - no event notifications

## References

- [Apple LaunchDaemons Documentation](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)
- [Apple SMJobBless Documentation](https://developer.apple.com/documentation/servicemanagement/1431078-smjobbless)
- [Nebula GitHub Repository](https://github.com/slackhq/nebula)
