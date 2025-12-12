# Root Privilege Solution - No More Auth Prompts! ✅

## Problem Solved

Previously, the macOS client prompted for admin credentials **every time** you started or stopped Nebula. This was because Nebula requires root privileges to create TUN network interfaces on macOS.

## New Solution

The PKG installer now includes a **privileged helper daemon** that:
- ✅ Runs as root in the background (via LaunchDaemon)
- ✅ Starts automatically on boot
- ✅ Handles all Nebula start/stop operations
- ✅ **No auth prompts after installation!**

## How It Works

```
┌─────────────────┐
│ ManagedNebula   │ (Your app - runs as regular user)
│      .app       │
└────────┬────────┘
         │ writes commands
         ↓
┌─────────────────┐
│ /tmp/nebula-    │ (IPC file - communication channel)
│    control      │
└────────┬────────┘
         │ reads commands
         ↓
┌─────────────────┐
│ nebula-helper   │ (Helper daemon - runs as root)
│      .sh        │
└────────┬────────┘
         │ starts/stops
         ↓
┌─────────────────┐
│ Nebula daemon   │ (VPN process - runs as root)
└─────────────────┘
```

## Installation

1. **Install PKG** (requires ONE admin prompt):
   ```bash
   sudo installer -pkg ManagedNebula-1.0.0.pkg -target /
   ```

2. **That's it!** The helper daemon is now running as root.

3. **Use the app** without any more prompts:
   - Open ManagedNebula.app
   - Click Connect - no prompt!
   - Click Disconnect - no prompt!

## What Gets Installed

### Files Installed

| File | Location | Permissions | Purpose |
|------|----------|-------------|---------|
| ManagedNebula.app | /Applications/ | User | UI application |
| nebula | /usr/local/bin/ | 0755 (root) | Nebula binary |
| nebula-cert | /usr/local/bin/ | 0755 (root) | Certificate tool |
| nebula-helper.sh | /usr/local/bin/ | 0755 (root) | Helper daemon |
| com.managednebula.helper.plist | /Library/LaunchDaemons/ | 0644 (root) | Daemon config |

### Directories Created

| Directory | Permissions | Purpose |
|-----------|-------------|---------|
| /etc/nebula/ | 0755 | Nebula configuration |
| /var/lib/nebula/ | 0700 | Private keys |
| /var/log/nebula/ | 0755 | Log files |
| /tmp/ | Default | IPC control file |

## Security

### During Installation
- **One admin prompt** when running the PKG installer
- Installs LaunchDaemon as root (standard macOS practice)
- Creates helper daemon that runs with root privileges

### During Normal Use
- **Zero admin prompts** for connect/disconnect
- App runs as regular user
- Helper daemon validates all commands
- No arbitrary code execution - only fixed commands (start/stop/status)

### IPC Security
- Commands: `start`, `stop`, `restart`, `status` (fixed strings only)
- No user input passed to shell
- No command injection possible
- File-based IPC with world-writable control file (local access only)

## Verification

### Check Helper Daemon Status
```bash
# Should show: com.managednebula.helper
sudo launchctl list | grep managednebula
```

### Test Commands Without Prompts
```bash
# Start Nebula (no prompt!)
echo "start" > /tmp/nebula-control
sleep 2

# Check if running (no prompt!)
pgrep -f "nebula -config"

# Stop Nebula (no prompt!)
echo "stop" > /tmp/nebula-control
```

### View Logs
```bash
# Helper daemon logs
sudo tail -f /var/log/nebula/nebula-helper.log

# Nebula logs  
sudo tail -f /var/log/nebula/nebula.log
```

## Comparison: Before vs After

| Scenario | Before | After |
|----------|--------|-------|
| **Installation** | Manual setup | One PKG install with admin prompt |
| **First connect** | Admin prompt | No prompt ✅ |
| **Disconnect** | Admin prompt | No prompt ✅ |
| **Reconnect** | Admin prompt | No prompt ✅ |
| **After restart** | Admin prompt | No prompt ✅ |
| **Daily use** | Admin prompt every time 😤 | Zero prompts! 🎉 |

## Troubleshooting

### Helper Daemon Not Running

```bash
# Reload daemon
sudo launchctl unload /Library/LaunchDaemons/com.managednebula.helper.plist
sudo launchctl load /Library/LaunchDaemons/com.managednebula.helper.plist

# Check status
sudo launchctl list | grep managednebula
```

### Still Getting Prompts?

This should **not** happen with the new system. If you see prompts:

1. Verify PKG was installed (not just DMG):
   ```bash
   ls -la /usr/local/bin/nebula-helper.sh
   # Should exist and be executable
   ```

2. Check helper daemon is running:
   ```bash
   sudo launchctl list | grep managednebula
   # Should show PID and status
   ```

3. Check IPC file exists:
   ```bash
   ls -la /tmp/nebula-control
   # Should be -rw-rw-rw- (666)
   ```

### Commands Not Working

```bash
# Manually test IPC
echo "status" > /tmp/nebula-control
sleep 2
cat /tmp/nebula-control.status
# Should show: running or stopped
```

## Uninstallation

```bash
# Stop helper daemon
sudo launchctl unload /Library/LaunchDaemons/com.managednebula.helper.plist

# Remove files
sudo rm /Library/LaunchDaemons/com.managednebula.helper.plist
sudo rm /usr/local/bin/nebula-helper.sh
sudo rm /usr/local/bin/nebula
sudo rm /usr/local/bin/nebula-cert
sudo rm -rf /Applications/ManagedNebula.app
sudo rm -rf /etc/nebula
sudo rm /tmp/nebula-control
```

## Technical Details

For developers interested in the implementation details, see [HELPER_DAEMON.md](HELPER_DAEMON.md).

## Summary

🎉 **No more authentication prompts during normal use!**

- ✅ Install once with PKG (requires admin)
- ✅ Helper daemon runs as root automatically
- ✅ App controls Nebula without prompts
- ✅ Works across reboots
- ✅ Standard macOS LaunchDaemon approach
- ✅ Secure file-based IPC

The user experience is now smooth and professional! 🚀
