# Test Plan - ManagedNebula macOS Client

This document outlines the testing strategy for the ManagedNebula macOS client.

## Prerequisites

- macOS 12 (Monterey) or later
- Intel or Apple Silicon Mac
- Managed Nebula server running and accessible
- Admin credentials for the server
- Nebula binaries installed (`/usr/local/bin/nebula`, `/usr/local/bin/nebula-cert`)

## Test Environment Setup

### 1. Server Setup
```bash
# Start Managed Nebula server
cd server
docker-compose up -d

# Create admin user
docker exec managed-nebula-server python manage.py create-admin admin@test.com TestPassword123

# Access web interface
open http://localhost:8080
```

### 2. Configure Server
1. Log in to web interface
2. Create Certificate Authority
3. Create IP pool (e.g., `10.100.0.0/16`)
4. Create a test client
5. Generate client token

### 3. Build macOS Client
```bash
cd macos_client
make build
```

## Test Cases

### Installation Tests

#### TC-001: Build from Source
**Objective**: Verify project builds successfully

**Steps**:
1. Run `make clean`
2. Run `make build`
3. Check `.build/release/ManagedNebula` exists

**Expected Result**: Build completes without errors, binary created

**Status**: [ ] Pass [ ] Fail

---

#### TC-002: Install Script
**Objective**: Verify install.sh works correctly

**Steps**:
1. Run `./install.sh`
2. Follow prompts
3. Verify `/usr/local/bin/ManagedNebula` exists

**Expected Result**: Installation completes, binary accessible in PATH

**Status**: [ ] Pass [ ] Fail

---

### Application Launch Tests

#### TC-003: First Launch
**Objective**: Verify app launches on first run

**Steps**:
1. Launch `ManagedNebula`
2. Check menu bar for network icon

**Expected Result**: 
- Application launches without crash
- Menu bar icon appears
- Status shows "Disconnected"

**Status**: [ ] Pass [ ] Fail

---

#### TC-004: Menu Bar Icon
**Objective**: Verify menu bar icon and menu

**Steps**:
1. Launch application
2. Click menu bar icon
3. Check menu items present

**Expected Result**: Menu shows:
- Status
- Connect/Disconnect
- Check for Updates
- View Logs
- Preferences
- Quit

**Status**: [ ] Pass [ ] Fail

---

### Configuration Tests

#### TC-005: Preferences Window
**Objective**: Verify preferences window opens and displays correctly

**Steps**:
1. Click menu bar icon → Preferences
2. Check all fields present

**Expected Result**: Window displays with fields:
- Server URL
- Client Token (secure field)
- Poll Interval
- Auto-start Nebula (checkbox)
- Launch at login (checkbox)
- Save and Cancel buttons

**Status**: [ ] Pass [ ] Fail

---

#### TC-006: Save Configuration
**Objective**: Verify configuration saves correctly

**Steps**:
1. Open Preferences
2. Enter:
   - Server URL: `http://localhost:8080`
   - Token: `<test-token>`
   - Poll Interval: `24`
3. Check Auto-start Nebula
4. Click Save
5. Reopen Preferences

**Expected Result**: All values persisted correctly

**Status**: [ ] Pass [ ] Fail

---

#### TC-007: Configuration Validation
**Objective**: Verify input validation works

**Steps**:
1. Open Preferences
2. Leave Server URL empty
3. Click Save
4. Check error message

**Expected Result**: Error alert shown: "Server URL is required"

**Status**: [ ] Pass [ ] Fail

---

### Keychain Tests

#### TC-008: Token Storage
**Objective**: Verify token saved to Keychain

**Steps**:
1. Open Preferences
2. Enter token
3. Click Save
4. Open Keychain Access app
5. Search for "managednebula"

**Expected Result**: Keychain entry exists with token

**Status**: [ ] Pass [ ] Fail

---

#### TC-009: Token Retrieval
**Objective**: Verify token can be loaded from Keychain

**Steps**:
1. Save token in Preferences
2. Quit application
3. Relaunch application
4. Try to connect

**Expected Result**: Connection works without re-entering token

**Status**: [ ] Pass [ ] Fail

---

### Keypair Generation Tests

#### TC-010: First-Time Keypair Generation
**Objective**: Verify keypair generated on first connect

**Steps**:
1. Delete `~/Library/Application Support/ManagedNebula/host.*` if exists
2. Click Connect
3. Check files created

**Expected Result**: Files created:
- `host.key` (permissions: 0600)
- `host.pub`

**Status**: [ ] Pass [ ] Fail

---

#### TC-011: Keypair Reuse
**Objective**: Verify existing keypair is reused

**Steps**:
1. Generate keypair (connect once)
2. Note creation date of `host.key`
3. Connect again
4. Check creation date unchanged

**Expected Result**: Existing keypair reused, not regenerated

**Status**: [ ] Pass [ ] Fail

---

### API Communication Tests

#### TC-012: Successful Config Fetch
**Objective**: Verify configuration fetched from server

**Steps**:
1. Configure valid server URL and token
2. Click Connect
3. Check logs

**Expected Result**: 
- Configuration fetched successfully
- Files created in `~/Library/Application Support/ManagedNebula/`:
  - `config.yml`
  - `host.crt`
  - `ca.crt`

**Status**: [ ] Pass [ ] Fail

---

#### TC-013: Invalid Token Handling
**Objective**: Verify proper error handling for invalid token

**Steps**:
1. Enter invalid token in Preferences
2. Click Connect

**Expected Result**: Error message: "Invalid client token"

**Status**: [ ] Pass [ ] Fail

---

#### TC-014: Blocked Client Handling
**Objective**: Verify proper error handling for blocked client

**Steps**:
1. Block client on server
2. Try to connect from macOS client

**Expected Result**: Error message: "Client is blocked on server"

**Status**: [ ] Pass [ ] Fail

---

#### TC-015: Server Unreachable
**Objective**: Verify proper error handling when server is down

**Steps**:
1. Stop server: `docker-compose down`
2. Try to connect from macOS client

**Expected Result**: Connection timeout with appropriate error message

**Status**: [ ] Pass [ ] Fail

---

### Nebula Daemon Tests

#### TC-016: Nebula Startup
**Objective**: Verify Nebula daemon starts correctly

**Steps**:
1. Click Connect
2. Wait for connection
3. Check process: `ps aux | grep nebula`

**Expected Result**: Nebula process running

**Status**: [ ] Pass [ ] Fail

---

#### TC-017: TUN Interface Creation
**Objective**: Verify TUN interface created

**Steps**:
1. Connect to VPN
2. Run: `ifconfig | grep nebula1`

**Expected Result**: Interface `nebula1` exists with Nebula IP

**Status**: [ ] Pass [ ] Fail

---

#### TC-018: Nebula Shutdown
**Objective**: Verify Nebula stops cleanly

**Steps**:
1. Connect to VPN
2. Click Disconnect
3. Check process: `ps aux | grep nebula`

**Expected Result**: Nebula process terminated, no zombie processes

**Status**: [ ] Pass [ ] Fail

---

### Connection Tests

#### TC-019: Full Connection Flow
**Objective**: Verify complete connection flow

**Steps**:
1. Start with clean state
2. Configure application
3. Click Connect
4. Wait for "Connected" status

**Expected Result**: 
- Status changes: Disconnected → Connecting → Connected
- Nebula IP assigned and visible
- Can ping other Nebula clients

**Status**: [ ] Pass [ ] Fail

---

#### TC-020: Ping Other Clients
**Objective**: Verify network connectivity through VPN

**Steps**:
1. Connect to VPN
2. Get peer IP from server UI
3. Ping peer: `ping -c 5 <peer-ip>`

**Expected Result**: Successful ping responses

**Status**: [ ] Pass [ ] Fail

---

#### TC-021: Reconnection After Network Change
**Objective**: Verify VPN reconnects after network changes

**Steps**:
1. Connect to VPN
2. Turn off Wi-Fi
3. Turn on Wi-Fi
4. Check connection status

**Expected Result**: Application reconnects automatically

**Status**: [ ] Pass [ ] Fail

---

### Configuration Update Tests

#### TC-022: Automatic Polling
**Objective**: Verify automatic config polling works

**Steps**:
1. Connect with poll interval of 1 hour
2. Wait 1 hour (or modify poll interval in code for testing)
3. Check logs

**Expected Result**: Log entry showing config check performed

**Status**: [ ] Pass [ ] Fail

---

#### TC-023: Manual Update Check
**Objective**: Verify manual update check works

**Steps**:
1. Connect to VPN
2. Make change on server (e.g., add group)
3. Click "Check for Updates"

**Expected Result**: Configuration updated, Nebula restarted

**Status**: [ ] Pass [ ] Fail

---

#### TC-024: Config Change Detection
**Objective**: Verify hash-based change detection works

**Steps**:
1. Connect to VPN
2. Click "Check for Updates" without server changes
3. Check logs

**Expected Result**: Log shows "Configuration unchanged, no restart needed"

**Status**: [ ] Pass [ ] Fail

---

### File Management Tests

#### TC-025: File Permissions
**Objective**: Verify correct file permissions set

**Steps**:
1. Connect to VPN
2. Run: `ls -la ~/Library/Application\ Support/ManagedNebula/`

**Expected Result**: 
- `host.key`: `-rw-------` (0600)
- `host.crt`: `-rw-r--r--` (0644)
- `ca.crt`: `-rw-r--r--` (0644)
- `config.yml`: `-rw-r--r--` (0644)

**Status**: [ ] Pass [ ] Fail

---

#### TC-026: Log File Creation
**Objective**: Verify log file created and accessible

**Steps**:
1. Connect to VPN
2. Click "View Logs"

**Expected Result**: Finder opens showing `nebula.log`

**Status**: [ ] Pass [ ] Fail

---

### Error Handling Tests

#### TC-027: Nebula Binary Not Found
**Objective**: Verify error handling when Nebula binary missing

**Steps**:
1. Rename `/usr/local/bin/nebula` temporarily
2. Try to connect

**Expected Result**: Error message: "Nebula binary not found"

**Status**: [ ] Pass [ ] Fail

---

#### TC-028: Config File Corruption
**Objective**: Verify handling of corrupted config file

**Steps**:
1. Connect successfully
2. Edit `config.yml` to be invalid YAML
3. Restart Nebula

**Expected Result**: Error logged, graceful failure

**Status**: [ ] Pass [ ] Fail

---

### UI Tests

#### TC-029: Status Updates
**Objective**: Verify status messages update correctly

**Steps**:
1. Watch menu bar during connection
2. Note status changes

**Expected Result**: Status shows:
- "Disconnected" (initial)
- "Connecting..." (during connection)
- "Connected" (when successful)

**Status**: [ ] Pass [ ] Fail

---

#### TC-030: Menu Item State
**Objective**: Verify menu items enable/disable correctly

**Steps**:
1. Open menu when disconnected
2. Connect
3. Open menu when connected

**Expected Result**: 
- Disconnected: "Connect" enabled
- Connected: "Disconnect" enabled

**Status**: [ ] Pass [ ] Fail

---

### Cleanup Tests

#### TC-031: Application Quit
**Objective**: Verify application quits cleanly

**Steps**:
1. Connect to VPN
2. Click menu bar icon → Quit
3. Check for zombie processes

**Expected Result**: 
- Application quits
- Nebula daemon stops
- No processes left running

**Status**: [ ] Pass [ ] Fail

---

#### TC-032: Launch at Login
**Objective**: Verify launch at login works (manual test)

**Steps**:
1. Enable "Launch at login" in Preferences
2. Log out and log back in
3. Check if application launches

**Expected Result**: Application auto-launches on login

**Status**: [ ] Pass [ ] Fail [ ] Not Implemented

---

## Performance Tests

### PT-001: CPU Usage
**Objective**: Verify reasonable CPU usage

**Steps**:
1. Connect to VPN
2. Let run for 10 minutes
3. Monitor Activity Monitor

**Expected Result**: CPU usage < 5% when idle

**Status**: [ ] Pass [ ] Fail

---

### PT-002: Memory Usage
**Objective**: Verify reasonable memory usage

**Steps**:
1. Connect to VPN
2. Let run for 10 minutes
3. Monitor Activity Monitor

**Expected Result**: Memory usage < 50 MB

**Status**: [ ] Pass [ ] Fail

---

### PT-003: Network Throughput
**Objective**: Verify acceptable network performance

**Steps**:
1. Connect to VPN
2. Transfer large file to peer
3. Measure throughput

**Expected Result**: Throughput comparable to Docker client

**Status**: [ ] Pass [ ] Fail

---

## Security Tests

### ST-001: Token Security
**Objective**: Verify token not logged or exposed

**Steps**:
1. Configure with token
2. Search all logs for token string

**Expected Result**: Token not found in any logs

**Status**: [ ] Pass [ ] Fail

---

### ST-002: Private Key Protection
**Objective**: Verify private key protected

**Steps**:
1. Connect to VPN
2. Check `host.key` permissions

**Expected Result**: File has 0600 permissions (owner-only access)

**Status**: [ ] Pass [ ] Fail

---

### ST-003: Keychain Security
**Objective**: Verify Keychain integration secure

**Steps**:
1. Open Keychain Access
2. Find managednebula entry
3. Check access control

**Expected Result**: Entry protected, requires authentication to view

**Status**: [ ] Pass [ ] Fail

---

## Compatibility Tests

### CT-001: macOS 12 (Monterey)
**Objective**: Verify works on macOS 12

**Platform**: macOS 12.x

**Status**: [ ] Pass [ ] Fail [ ] Not Tested

---

### CT-002: macOS 13 (Ventura)
**Objective**: Verify works on macOS 13

**Platform**: macOS 13.x

**Status**: [ ] Pass [ ] Fail [ ] Not Tested

---

### CT-003: macOS 14 (Sonoma)
**Objective**: Verify works on macOS 14

**Platform**: macOS 14.x

**Status**: [ ] Pass [ ] Fail [ ] Not Tested

---

### CT-004: Intel Mac
**Objective**: Verify works on Intel processors

**Platform**: Intel Mac

**Status**: [ ] Pass [ ] Fail [ ] Not Tested

---

### CT-005: Apple Silicon Mac
**Objective**: Verify works on Apple Silicon

**Platform**: Apple Silicon (M1/M2/M3)

**Status**: [ ] Pass [ ] Fail [ ] Not Tested

---

## Test Summary

**Total Test Cases**: 37 functional + 5 compatibility

**Passed**: ___ / 42
**Failed**: ___ / 42
**Not Tested**: ___ / 42

## Known Issues

Document any issues found during testing:

1. Issue #1: Description
   - Severity: High/Medium/Low
   - Workaround: If any
   - Status: Open/Fixed

## Test Environment

- **macOS Version**: 
- **Hardware**: Intel / Apple Silicon
- **Swift Version**: 
- **Nebula Version**: 
- **Server Version**: 
- **Test Date**: 

## Notes

Add any additional notes or observations:

---

**Tester Name**: _______________
**Date Completed**: _______________
**Signature**: _______________
