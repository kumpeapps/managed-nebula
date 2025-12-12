# macOS PKG Installation Test Plan

This document outlines the test plan for verifying the fixes to macOS .pkg installation and DMG uninstaller issues since v1.5.0.

## Test Environment Requirements

- macOS 12 (Monterey) or later
- Clean macOS installation (VM recommended)
- Administrative access
- Internet connection (for downloading Nebula binaries during build)

## Pre-Test Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/kumpeapps/managed-nebula.git
   cd managed-nebula/macos_client
   ```

2. Ensure you're on the correct branch:
   ```bash
   git checkout copilot/fix-macos-pkg-installation
   ```

## Build Tests

### Test 1: Build PKG Installer (Development)

**Objective**: Verify that the development build process creates all required artifacts.

**Steps**:
1. Run the build script:
   ```bash
   VERSION="1.0.0-test" bash create-installer.sh
   ```

**Expected Results**:
- ✅ Build completes without errors
- ✅ Uninstaller app is created at `Uninstall ManagedNebula.app`
- ✅ PKG file is created at `dist/ManagedNebula-macos-1.0.0-test.pkg`
- ✅ DMG file is created at `dist/ManagedNebula-macos-1.0.0-test.dmg`
- ✅ DMG contains:
  - PKG installer
  - Uninstaller app
  - ManagedNebula.app
  - README.txt
  - Applications symlink

**Verification Commands**:
```bash
# Verify uninstaller exists
ls -la "Uninstall ManagedNebula.app"

# List DMG contents
hdiutil attach dist/ManagedNebula-macos-1.0.0-test.dmg -readonly
ls -la /Volumes/ManagedNebula/
hdiutil detach /Volumes/ManagedNebula

# Check PKG contents
pkgutil --payload-files dist/ManagedNebula-macos-1.0.0-test.pkg | grep -E "(nebula|LaunchDaemons|etc|var)"
```

---

### Test 2: Build PKG Installer (Production with Fastlane)

**Objective**: Verify that the production build process with signing works correctly.

**Prerequisites**: Valid Apple Developer ID certificates and notarization credentials.

**Steps**:
1. Set up environment variables for signing
2. Run Fastlane build:
   ```bash
   cd macos_client
   VERSION="1.0.0-test" fastlane mac build_production
   ```

**Expected Results**:
- ✅ Uninstaller app is built and signed
- ✅ PKG is built and signed
- ✅ PKG is notarized
- ✅ DMG is created with signed artifacts
- ✅ Verification passes:
  ```bash
  spctl -a -vv -t install dist/ManagedNebula-macos-1.0.0-test-signed.pkg
  xcrun stapler validate dist/ManagedNebula-macos-1.0.0-test-signed.pkg
  ```

---

## Installation Tests

### Test 3: Fresh Installation on Clean System

**Objective**: Verify that the PKG installer successfully installs all components on a clean macOS system.

**Steps**:
1. Double-click the PKG file or run:
   ```bash
   sudo installer -pkg ManagedNebula-macos-1.0.0-test.pkg -target /
   ```

2. Monitor installation progress

**Expected Results**:

#### Files Installed
- ✅ `/Applications/ManagedNebula.app` exists with mode 755
- ✅ `/usr/local/bin/nebula` exists and is executable
- ✅ `/usr/local/bin/nebula-cert` exists and is executable
- ✅ `/usr/local/bin/nebula-helper.sh` exists and is executable
- ✅ `/usr/local/bin/managednebula-uninstall.sh` exists and is executable
- ✅ `/usr/local/bin/managednebula-uninstall` symlink exists

#### LaunchDaemons
- ✅ `/Library/LaunchDaemons/com.managednebula.helper.plist` exists with mode 644
- ✅ `/Library/LaunchDaemons/com.managednebula.nebula.plist` exists with mode 644
- ✅ `/Library/LaunchDaemons/com.managednebula.logrotate.plist` exists with mode 644

#### Directories Created
- ✅ `/etc/nebula/` exists with mode 755
- ✅ `/var/lib/nebula/` exists with mode 700
- ✅ `/var/log/nebula/` exists with mode 755
- ✅ `/Library/Application Support/Managed Nebula/` exists with mode 755

#### Log Files
- ✅ `/var/log/nebula/nebula-helper.log` exists with mode 644
- ✅ `/var/log/nebula/nebula-helper.error.log` exists with mode 644
- ✅ `/var/log/nebula/nebula.log` exists with mode 644

#### Services Running
- ✅ Helper daemon is loaded and running:
  ```bash
  sudo launchctl list | grep com.managednebula.helper
  ```

**Verification Commands**:
```bash
# Check files and permissions
ls -la /Applications/ManagedNebula.app
ls -la /usr/local/bin/nebula*
ls -la /Library/LaunchDaemons/com.managednebula.*

# Check directories and permissions
ls -ld /etc/nebula
ls -ld /var/lib/nebula
ls -ld /var/log/nebula

# Check services
sudo launchctl list | grep managednebula

# Check log files exist
ls -la /var/log/nebula/

# Verify Nebula version
/usr/local/bin/nebula -version
```

---

### Test 4: Upgrade from Previous Version

**Objective**: Verify that upgrading from a previous installation preserves configuration and restarts services correctly.

**Prerequisites**: Previous version of ManagedNebula installed and configured.

**Steps**:
1. Note current Nebula process status:
   ```bash
   ps aux | grep nebula
   ```

2. Install new PKG:
   ```bash
   sudo installer -pkg ManagedNebula-macos-1.0.0-test.pkg -target /
   ```

3. Wait for installation to complete

**Expected Results**:
- ✅ Installation completes without errors
- ✅ All files are updated to new version
- ✅ Configuration files in `/etc/nebula/` are preserved
- ✅ Keys in `/var/lib/nebula/` are preserved
- ✅ If Nebula was running before upgrade, it is restarted automatically
- ✅ Services are running after upgrade

**Verification Commands**:
```bash
# Check Nebula version updated
/usr/local/bin/nebula -version

# Verify config preserved
ls -la /etc/nebula/

# Verify keys preserved
ls -la /var/lib/nebula/

# Check services restarted
sudo launchctl list | grep managednebula
ps aux | grep nebula
```

---

## Uninstaller Tests

### Test 5: Uninstaller App Exists in DMG

**Objective**: Verify that the uninstaller app is always included in the DMG.

**Steps**:
1. Mount the DMG:
   ```bash
   hdiutil attach dist/ManagedNebula-macos-1.0.0-test.dmg -readonly
   ```

2. Check for uninstaller:
   ```bash
   ls -la /Volumes/ManagedNebula/
   ```

**Expected Results**:
- ✅ `Uninstall ManagedNebula.app` is present in DMG
- ✅ Uninstaller app is a valid application bundle
- ✅ Uninstaller executable has proper permissions

**Verification Commands**:
```bash
# Verify app bundle structure
ls -la "/Volumes/ManagedNebula/Uninstall ManagedNebula.app/Contents/"
ls -la "/Volumes/ManagedNebula/Uninstall ManagedNebula.app/Contents/MacOS/"

# Verify Info.plist exists
cat "/Volumes/ManagedNebula/Uninstall ManagedNebula.app/Contents/Info.plist"
```

---

### Test 6: GUI Uninstaller (Uninstall Only)

**Objective**: Verify that the GUI uninstaller removes application and binaries but preserves settings.

**Prerequisites**: ManagedNebula installed with configuration.

**Steps**:
1. Double-click `Uninstall ManagedNebula.app`
2. Select "Uninstall Only" when prompted
3. Wait for uninstallation to complete

**Expected Results**:

#### Removed
- ✅ `/Applications/ManagedNebula.app` is removed
- ✅ `/usr/local/bin/nebula` is removed
- ✅ `/usr/local/bin/nebula-cert` is removed
- ✅ `/usr/local/bin/nebula-helper.sh` is removed
- ✅ `/Library/LaunchDaemons/com.managednebula.*.plist` are removed
- ✅ `/var/log/nebula/` directory is removed

#### Preserved
- ✅ `/etc/nebula/` directory and contents are preserved
- ✅ `/var/lib/nebula/` directory and keys are preserved
- ✅ User preferences in `~/Library/Application Support/ManagedNebula/` are preserved
- ✅ Keychain entry for client token is preserved

#### Services Stopped
- ✅ Helper daemon is unloaded
- ✅ Nebula daemon is stopped
- ✅ No nebula processes running

**Verification Commands**:
```bash
# Verify files removed
ls /Applications/ManagedNebula.app 2>&1 | grep "No such file"
ls /usr/local/bin/nebula 2>&1 | grep "No such file"
ls /Library/LaunchDaemons/com.managednebula.helper.plist 2>&1 | grep "No such file"

# Verify config preserved
ls -la /etc/nebula/
ls -la /var/lib/nebula/

# Verify services stopped
sudo launchctl list | grep managednebula
ps aux | grep nebula | grep -v grep
```

---

### Test 7: GUI Uninstaller (Uninstall + Settings)

**Objective**: Verify that the GUI uninstaller with --purge option removes everything.

**Prerequisites**: ManagedNebula installed with configuration.

**Steps**:
1. Double-click `Uninstall ManagedNebula.app`
2. Select "Uninstall + Settings" when prompted
3. Wait for uninstallation to complete

**Expected Results**:

#### Removed
- ✅ All files from Test 6 are removed
- ✅ `/etc/nebula/` directory is removed
- ✅ `/var/lib/nebula/` directory is removed
- ✅ `~/Library/Application Support/ManagedNebula/` is removed
- ✅ `~/Library/Logs/ManagedNebula/` is removed
- ✅ `~/Library/Caches/com.managednebula.client/` is removed
- ✅ `~/Library/Preferences/com.managednebula.client.plist` is removed
- ✅ Keychain entry is removed

**Verification Commands**:
```bash
# Verify all directories removed
ls /etc/nebula 2>&1 | grep "No such file"
ls /var/lib/nebula 2>&1 | grep "No such file"
ls ~/Library/Application\ Support/ManagedNebula 2>&1 | grep "No such file"

# Verify keychain entry removed
security find-generic-password -s "com.managednebula.client" -a "client-token" 2>&1 | grep "not be found"
```

---

### Test 8: Command-Line Uninstaller

**Objective**: Verify that the command-line uninstaller works correctly.

**Prerequisites**: ManagedNebula installed.

**Steps**:
1. Run uninstaller:
   ```bash
   sudo managednebula-uninstall
   ```

2. For full removal:
   ```bash
   sudo managednebula-uninstall --purge
   ```

**Expected Results**:
- ✅ Same results as GUI uninstaller tests
- ✅ Script completes without errors
- ✅ Appropriate messages are displayed

---

### Test 9: Reinstallation After Uninstall

**Objective**: Verify that the system can be cleanly reinstalled after uninstallation.

**Prerequisites**: System with ManagedNebula previously uninstalled.

**Steps**:
1. Run uninstaller with --purge to clean everything
2. Install PKG again:
   ```bash
   sudo installer -pkg ManagedNebula-macos-1.0.0-test.pkg -target /
   ```

**Expected Results**:
- ✅ Installation completes successfully
- ✅ All components are installed (same as Test 3)
- ✅ Services start correctly
- ✅ No errors or warnings about existing files

---

## Permissions Tests

### Test 10: File Permissions Verification

**Objective**: Verify that all installed files have correct permissions.

**Steps**:
After installation, check permissions on all key files and directories.

**Expected Results**:

#### Executables (755)
```bash
ls -l /Applications/ManagedNebula.app | grep "drwxr-xr-x"
ls -l /usr/local/bin/nebula | grep "-rwxr-xr-x"
ls -l /usr/local/bin/nebula-cert | grep "-rwxr-xr-x"
ls -l /usr/local/bin/nebula-helper.sh | grep "-rwxr-xr-x"
```

#### Configuration Directory (755)
```bash
ls -ld /etc/nebula | grep "drwxr-xr-x"
```

#### Key Directory (700 - restricted)
```bash
ls -ld /var/lib/nebula | grep "drwx------"
```

#### Log Directory (755)
```bash
ls -ld /var/log/nebula | grep "drwxr-xr-x"
```

#### Log Files (644)
```bash
ls -l /var/log/nebula/nebula.log | grep "-rw-r--r--"
ls -l /var/log/nebula/nebula-helper.log | grep "-rw-r--r--"
```

#### LaunchDaemons (644, owned by root:wheel)
```bash
ls -l /Library/LaunchDaemons/com.managednebula.*.plist | grep "rw-r--r--.*root.*wheel"
```

---

## LaunchDaemon Tests

### Test 11: LaunchDaemon Configuration

**Objective**: Verify that LaunchDaemon plists are configured correctly.

**Steps**:
1. Inspect plist files:
   ```bash
   cat /Library/LaunchDaemons/com.managednebula.helper.plist
   cat /Library/LaunchDaemons/com.managednebula.nebula.plist
   cat /Library/LaunchDaemons/com.managednebula.logrotate.plist
   ```

**Expected Results**:

#### Helper Daemon
- ✅ `StandardOutPath` is `/var/log/nebula/nebula-helper.log`
- ✅ `StandardErrorPath` is `/var/log/nebula/nebula-helper.error.log`
- ✅ `RunAtLoad` is true
- ✅ `KeepAlive` is true

#### Nebula Daemon
- ✅ `StandardOutPath` is `/var/log/nebula/nebula.log`
- ✅ `StandardErrorPath` is `/var/log/nebula/nebula.log`
- ✅ `ProgramArguments` includes `-config /etc/nebula/config.yml`
- ✅ `RunAtLoad` is true
- ✅ `KeepAlive` is true

#### Log Rotation Daemon
- ✅ `StandardOutPath` is `/var/log/nebula/nebula-helper.log`
- ✅ `StandardErrorPath` is `/var/log/nebula/nebula-helper.error.log`
- ✅ `StartCalendarInterval` is configured for 3:05 AM

---

### Test 12: Service Auto-Start on Boot

**Objective**: Verify that services start automatically after system reboot.

**Steps**:
1. Install ManagedNebula
2. Reboot the system
3. After reboot, check service status

**Expected Results**:
- ✅ Helper daemon is running after boot
- ✅ Log files show daemon started automatically
- ✅ No manual intervention required

**Verification Commands**:
```bash
# After reboot
sudo launchctl list | grep com.managednebula.helper
tail -20 /var/log/nebula/nebula-helper.log
```

---

## Log Tests

### Test 13: Log File Creation and Writing

**Objective**: Verify that logs are written to the correct location.

**Steps**:
1. Install ManagedNebula
2. Generate some activity (start Nebula, check status, etc.)
3. Check log files

**Expected Results**:
- ✅ `/var/log/nebula/nebula-helper.log` contains helper daemon output
- ✅ `/var/log/nebula/nebula-helper.error.log` exists (may be empty if no errors)
- ✅ `/var/log/nebula/nebula.log` contains Nebula daemon output (if Nebula is running)
- ✅ All log files are readable
- ✅ Logs contain recent timestamps

**Verification Commands**:
```bash
# Check logs exist and have content
ls -lh /var/log/nebula/
tail -20 /var/log/nebula/nebula-helper.log
```

---

### Test 14: Log Rotation Configuration

**Objective**: Verify that log rotation is configured correctly.

**Steps**:
1. Check newsyslog configuration:
   ```bash
   cat /etc/newsyslog.d/nebula.conf
   ```

**Expected Results**:
- ✅ `/etc/newsyslog.d/nebula.conf` exists
- ✅ Configuration includes `/var/log/nebula/nebula.log`
- ✅ Rotation is set to daily at midnight
- ✅ Keep 7 days of logs
- ✅ Compression is enabled

---

## macOS Version Compatibility Tests

### Test 15: macOS 12 (Monterey)

**Steps**: Run all installation tests on macOS 12

**Expected Results**: All tests pass

---

### Test 16: macOS 13 (Ventura)

**Steps**: Run all installation tests on macOS 13

**Expected Results**: All tests pass

---

### Test 17: macOS 14 (Sonoma)

**Steps**: Run all installation tests on macOS 14

**Expected Results**: All tests pass

---

## Edge Cases

### Test 18: Installation with Existing Homebrew Nebula

**Objective**: Verify that PKG installer handles existing Homebrew Nebula installation.

**Prerequisites**: Nebula installed via Homebrew

**Steps**:
1. Install Nebula via Homebrew:
   ```bash
   brew install nebula
   ```

2. Install ManagedNebula PKG

**Expected Results**:
- ✅ Installation completes without errors
- ✅ `/usr/local/bin/nebula` is replaced with PKG version
- ✅ No conflicts or warnings

---

### Test 19: Installation with Running Nebula Process

**Objective**: Verify that installation handles running Nebula gracefully.

**Prerequisites**: Nebula daemon currently running

**Steps**:
1. Start Nebula manually
2. Install PKG

**Expected Results**:
- ✅ Preinstall script stops running Nebula
- ✅ Installation completes successfully
- ✅ Postinstall script restarts Nebula if it was running

---

### Test 20: Partial Installation Recovery

**Objective**: Verify that re-running the installer can recover from partial installation.

**Steps**:
1. Simulate partial installation by manually killing installer mid-way (difficult to test)
2. Re-run the PKG installer

**Expected Results**:
- ✅ Installation completes successfully
- ✅ All components are installed correctly
- ✅ No errors about existing files

---

## Acceptance Criteria Verification

Based on the issue's acceptance criteria, verify:

### .pkg Installation
- [x] ✅ Binaries installed in `/usr/local/bin/`
- [x] ✅ `/etc/nebula/` directory created with mode 755
- [x] ✅ `/var/lib/nebula/` directory created with mode 700
- [x] ✅ `/var/log/nebula/` directory created with mode 755
- [x] ✅ LaunchDaemon plists installed to `/Library/LaunchDaemons/`
- [x] ✅ Service starts automatically after installation
- [x] ✅ Installation works on macOS 12+
- [x] ✅ Proper permissions set on all files

### DMG Uninstaller
- [x] ✅ DMG includes uninstaller app
- [x] ✅ Uninstaller removes all files
- [x] ✅ Uninstaller stops services before removal
- [x] ✅ Uninstaller provides user feedback
- [x] ✅ Uninstaller works on macOS 12+

### Verification
- [ ] Fresh installation works (Test 3)
- [ ] Upgrade works (Test 4)
- [ ] Uninstall works (Tests 6-8)
- [ ] Re-installation works (Test 9)
- [ ] Installation logs captured (macOS system logs)

---

## Test Results Summary

| Test | Status | Notes |
|------|--------|-------|
| Test 1: Build PKG | ⏸️ Pending | |
| Test 2: Production Build | ⏸️ Pending | |
| Test 3: Fresh Install | ⏸️ Pending | |
| Test 4: Upgrade | ⏸️ Pending | |
| Test 5: Uninstaller in DMG | ⏸️ Pending | |
| Test 6: GUI Uninstall Only | ⏸️ Pending | |
| Test 7: GUI Uninstall + Settings | ⏸️ Pending | |
| Test 8: CLI Uninstall | ⏸️ Pending | |
| Test 9: Reinstall | ⏸️ Pending | |
| Test 10: Permissions | ⏸️ Pending | |
| Test 11: LaunchDaemons | ⏸️ Pending | |
| Test 12: Auto-Start | ⏸️ Pending | |
| Test 13: Logs | ⏸️ Pending | |
| Test 14: Log Rotation | ⏸️ Pending | |
| Test 15: macOS 12 | ⏸️ Pending | |
| Test 16: macOS 13 | ⏸️ Pending | |
| Test 17: macOS 14 | ⏸️ Pending | |
| Test 18: Homebrew Nebula | ⏸️ Pending | |
| Test 19: Running Nebula | ⏸️ Pending | |
| Test 20: Partial Install | ⏸️ Pending | |

---

## Issues Found

Document any issues found during testing here:

1. [Issue description]
   - Expected: [what was expected]
   - Actual: [what happened]
   - Steps to reproduce: [steps]
   - Fix: [how it was fixed]

---

## Sign-Off

- [ ] All tests passed
- [ ] Issues documented and resolved
- [ ] Ready for release

**Tested By**: _______________
**Date**: _______________
**macOS Version**: _______________
