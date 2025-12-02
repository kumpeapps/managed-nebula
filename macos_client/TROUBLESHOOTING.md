# Troubleshooting Guide - ManagedNebula macOS Client

This guide helps you diagnose and fix common issues with the ManagedNebula macOS client.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Connection Issues](#connection-issues)
- [Network Issues](#network-issues)
- [Performance Issues](#performance-issues)
- [Security Issues](#security-issues)
- [Advanced Debugging](#advanced-debugging)

## Installation Issues

### Problem: Swift not found

**Error**: `swift: command not found`

**Solution**: Install Xcode Command Line Tools:
```bash
xcode-select --install
```

Or install full Xcode from the Mac App Store.

---

### Problem: Nebula binary not found

**Error**: `Nebula binary not found at /usr/local/bin/nebula`

**Solution**: Install Nebula binaries:
```bash
curl -LO https://github.com/slackhq/nebula/releases/latest/download/nebula-darwin.tar.gz
tar xzf nebula-darwin.tar.gz
sudo mv nebula nebula-cert /usr/local/bin/
sudo chmod +x /usr/local/bin/nebula /usr/local/bin/nebula-cert
```

Verify installation:
```bash
which nebula
nebula -version
```

---

### Problem: Build fails with linker errors

**Error**: Various Swift linker errors

**Solution**:
1. Clean build directory:
   ```bash
   make clean
   ```

2. Rebuild:
   ```bash
   make build
   ```

3. If still failing, check Swift version:
   ```bash
   swift --version
   ```
   Should be Swift 5.9 or later.

---

### Problem: Permission denied during installation

**Error**: `Permission denied` when running `make install`

**Solution**: Installation requires sudo:
```bash
sudo make install
```

## Connection Issues

### Problem: "Invalid client token"

**Symptoms**: Connection fails with authentication error

**Solution**:
1. **Verify token is correct**:
   - Open Preferences
   - Check token is complete (no spaces, line breaks)
   - Copy token again from server

2. **Check token is active on server**:
   - Log in to web interface
   - Navigate to Clients → Your Client
   - Verify token is listed and active

3. **Generate new token**:
   - In web interface, click "Generate Token"
   - Update token in macOS client Preferences

---

### Problem: "Client is blocked on server"

**Symptoms**: HTTP 403 error when connecting

**Solution**: Contact your Nebula administrator to unblock the client:
1. Log in to Managed Nebula server
2. Navigate to Clients
3. Find your client
4. Uncheck "Is Blocked"
5. Save changes

---

### Problem: "Server CA not configured"

**Symptoms**: HTTP 503 error when connecting

**Solution**: The server needs a Certificate Authority created:
1. Administrator must log in to web interface
2. Navigate to CA Management
3. Create a new CA
4. Try connecting again from macOS client

---

### Problem: "Client has no IP assignment"

**Symptoms**: HTTP 409 error when connecting

**Solution**:
1. **Check IP pool exists**:
   - Server admin: verify IP pool is created
   - Navigate to IP Pools in web interface

2. **Assign IP to client**:
   - Open client in web interface
   - Assign to an IP pool
   - Try connecting again

---

### Problem: Connection hangs at "Connecting..."

**Symptoms**: Status stuck at "Connecting..." for more than 30 seconds

**Solution**:
1. **Check network connectivity**:
   ```bash
   ping -c 3 your-server-hostname
   ```

2. **Verify server URL in Preferences**:
   - Should be: `https://your-server.com` (with https if using SSL)
   - Not: `https://your-server.com/` (no trailing slash)

3. **Check server is running**:
   ```bash
   curl https://your-server.com/api/v1/healthz
   ```

4. **Check firewall**:
   - macOS Firewall might be blocking connections
   - System Settings → Network → Firewall → Allow ManagedNebula

5. **View logs**:
   ```bash
   tail -f ~/Library/Logs/ManagedNebula/nebula.log
   ```

## Network Issues

### Problem: Can't ping other Nebula clients

**Symptoms**: VPN connected but can't reach other clients

**Solution**:
1. **Verify connection status**:
   - Menu bar icon should show "Connected"
   - Check logs for errors

2. **Check Nebula interface exists**:
   ```bash
   ifconfig | grep nebula1
   ```
   Should show an interface with your Nebula IP.

3. **Verify your Nebula IP**:
   ```bash
   ifconfig nebula1
   ```
   Note your IP address (e.g., 10.100.0.5).

4. **Check routing table**:
   ```bash
   netstat -rn | grep nebula1
   ```

5. **Test lighthouse connectivity** (if not a lighthouse yourself):
   - Find lighthouse IP in config:
     ```bash
     cat ~/Library/Application\ Support/ManagedNebula/config.yml | grep lighthouse
     ```
   - Ping lighthouse:
     ```bash
     ping -c 3 <lighthouse-ip>
     ```

6. **Check firewall rules on server**:
   - Verify your client has appropriate firewall rules
   - Check group memberships in web interface

7. **Verify peer is in same pool**:
   - Clients can only communicate within their IP pool
   - Check IP pool assignment in web interface

---

### Problem: TUN interface creation fails

**Symptoms**: Error creating `/dev/net/tun` or permission denied

**Solution**:
1. **Check TUN/TAP kernel extension**:
   ```bash
   kextstat | grep tun
   ```

2. **macOS 11+ requires explicit approval**:
   - System Settings → Security & Privacy
   - Look for message about network extension
   - Click "Allow"

3. **Try running with elevated privileges** (not recommended for normal use):
   ```bash
   sudo ManagedNebula
   ```

4. **Check System Extension Policy**:
   ```bash
   systemextensionsctl list
   ```

---

### Problem: TUN interface not connecting on macOS Tahoe (macOS 26) or Sequoia

**Symptoms**: Nebula starts but the TUN interface (utun) is neither created nor connected

**Solution**:
1. **Ensure you're using the latest macOS client version**: The server now includes `use_system_route_table: true` in the TUN configuration for macOS clients, which is required for macOS 14+ (Sonoma, Sequoia, Tahoe).

2. **Verify the configuration includes the correct setting**:
   ```bash
   cat ~/Library/Application\ Support/ManagedNebula/config.yml | grep use_system_route_table
   ```
   Should show: `use_system_route_table: true`

3. **Manually trigger a config refresh**:
   - Click the menu bar icon
   - Select "Check for Updates"

4. **Restart Nebula**:
   - Click the menu bar icon
   - Select "Disconnect"
   - Wait a few seconds
   - Select "Connect"

5. **Check system logs for errors**:
   ```bash
   log show --predicate 'subsystem == "com.apple.networkextension"' --last 5m
   ```

---

### Problem: DNS not working through VPN

**Symptoms**: Can ping IPs but can't resolve hostnames

**Solution**:
1. **Check DNS configuration in Nebula config**:
   ```bash
   cat ~/Library/Application\ Support/ManagedNebula/config.yml | grep -A 5 dns
   ```

2. **Verify DNS servers are reachable**:
   ```bash
   ping <dns-server-ip>
   ```

3. **Check system DNS settings**:
   ```bash
   scutil --dns
   ```

## Performance Issues

### Problem: High CPU usage

**Symptoms**: Activity Monitor shows high CPU usage by Nebula or ManagedNebula

**Solution**:
1. **Check poll interval**:
   - Open Preferences
   - Increase poll interval (e.g., 24 hours instead of 1 hour)

2. **Check for connection issues**:
   - Frequent reconnection attempts use CPU
   - View logs for errors

3. **Reduce logging verbosity**:
   - Edit config: `~/Library/Application Support/ManagedNebula/config.yml`
   - Set logging level to `info` or `warning` instead of `debug`

---

### Problem: High memory usage

**Symptoms**: Activity Monitor shows high memory usage

**Solution**:
1. **Restart the application**:
   - Quit from menu bar
   - Relaunch

2. **Check log file size**:
   ```bash
   ls -lh ~/Library/Logs/ManagedNebula/nebula.log
   ```
   
3. **Rotate logs**:
   ```bash
   mv ~/Library/Logs/ManagedNebula/nebula.log ~/Library/Logs/ManagedNebula/nebula.log.old
   ```

---

### Problem: Slow connection speeds

**Symptoms**: Poor throughput through VPN

**Solution**:
1. **Check lighthouse configuration**:
   - Ensure lighthouses have good network connectivity
   - Verify lighthouse public IPs are correct

2. **Test direct connectivity**:
   ```bash
   nebula-cert print -path ~/Library/Application\ Support/ManagedNebula/host.crt
   ```

3. **Check MTU settings**:
   - Edit config and adjust `tun.mtu` if needed

4. **Verify no packet loss**:
   ```bash
   ping -c 100 <peer-ip>
   ```

## Security Issues

### Problem: Keychain access denied

**Symptoms**: Can't save or load token from Keychain

**Solution**:
1. **Grant Keychain access**:
   - Open Keychain Access app
   - Look for "managednebula" entries
   - Double-click → Access Control
   - Add ManagedNebula to allowed applications

2. **Reset Keychain item**:
   - Delete existing "managednebula" entry
   - Restart app and re-enter token

---

### Problem: Private key permissions incorrect

**Symptoms**: Nebula won't start, permission errors in logs

**Solution**:
```bash
chmod 600 ~/Library/Application\ Support/ManagedNebula/host.key
```

---

### Problem: Certificate expired

**Symptoms**: Can connect initially but fails after some time

**Solution**:
1. **Check certificate validity**:
   ```bash
   nebula-cert print -path ~/Library/Application\ Support/ManagedNebula/host.crt
   ```

2. **Trigger manual update**:
   - Click menu bar icon → Check for Updates

3. **Verify poll interval isn't too long**:
   - Check Preferences → Poll Interval
   - Should be less than certificate validity period

## Advanced Debugging

### Enable Debug Logging

1. Edit config file:
   ```bash
   nano ~/Library/Application\ Support/ManagedNebula/config.yml
   ```

2. Find logging section and change level:
   ```yaml
   logging:
     level: debug
   ```

3. Restart Nebula from menu bar

### View Live Logs

```bash
tail -f ~/Library/Logs/ManagedNebula/nebula.log
```

### Test Configuration

```bash
nebula -test -config ~/Library/Application\ Support/ManagedNebula/config.yml
```

### Check File Permissions

```bash
ls -la ~/Library/Application\ Support/ManagedNebula/
```

Should show:
- `host.key`: `-rw-------` (0600)
- `host.crt`, `ca.crt`, `config.yml`: `-rw-r--r--` (0644)

### Network Diagnostics

```bash
# Check Nebula interface
ifconfig nebula1

# Check routes
netstat -rn | grep nebula1

# Check Nebula process
ps aux | grep nebula

# Test lighthouse connectivity
ping <lighthouse-nebula-ip>

# Trace route
traceroute <peer-nebula-ip>
```

### API Testing

Test server connectivity manually:
```bash
curl -X POST https://your-server.com/v1/client/config \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your-token-here",
    "public_key": "-----BEGIN NEBULA ED25519 PUBLIC KEY-----\n...\n-----END NEBULA ED25519 PUBLIC KEY-----\n"
  }'
```

### Reset Application

If all else fails, reset the application:

```bash
# Stop application
# Then remove all data:
rm -rf ~/Library/Application\ Support/ManagedNebula
rm -rf ~/Library/Logs/ManagedNebula

# Remove Keychain entry:
# Open Keychain Access → search "managednebula" → delete

# Restart application
```

## Getting Help

If you can't resolve your issue:

1. **Collect diagnostic information**:
   ```bash
   # System info
   sw_vers
   
   # Nebula version
   nebula -version
   
   # Recent logs
   tail -n 100 ~/Library/Logs/ManagedNebula/nebula.log > nebula-debug.log
   
   # Configuration (remove sensitive data first!)
   cat ~/Library/Application\ Support/ManagedNebula/config.yml > config-debug.yml
   ```

2. **Open GitHub issue** with:
   - Description of problem
   - Steps to reproduce
   - macOS version
   - Relevant logs (sanitized)
   - What you've tried

3. **Check existing issues**:
   - Search GitHub issues
   - Check closed issues too

## Uninstallation

If you need to completely remove the application:

```bash
# Stop application first

# Remove binary
sudo rm /usr/local/bin/ManagedNebula

# Remove configuration
rm -rf ~/Library/Application\ Support/ManagedNebula

# Remove logs
rm -rf ~/Library/Logs/ManagedNebula

# Remove Keychain entry
# Open Keychain Access → search "managednebula" → delete items

# Optional: Remove Nebula binaries
sudo rm /usr/local/bin/nebula /usr/local/bin/nebula-cert
```

Then reinstall following the [QUICKSTART.md](QUICKSTART.md) guide.
