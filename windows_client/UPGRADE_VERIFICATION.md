# Windows Installer Upgrade Verification Guide

This guide helps verify that the Windows installer correctly upgrades Nebula binaries from version 1.9.7 to 1.10.0 (or any specified version).

## Quick Verification

### 1. Build with Specific Version
```cmd
cd windows_client
build-installer.bat --nebula-version 1.10.0
```

### 2. Check Build Output
Look for these lines in the build output:
```
Nebula Version: 1.10.0
Downloading Nebula version v1.10.0
URL: https://github.com/slackhq/nebula/releases/download/v1.10.0/nebula-windows-amd64.zip
Download complete: dist\nebula-tmp\nebula.zip
Verifying Nebula version...
Downloaded version: Nebula v1.10.0
Expected version: v1.10.0
```

### 3. Verify Installer Contents
After build completes, the installer directory should show correct version:
```cmd
cd installer
nebula.exe -version
```
Expected output: `Nebula v1.10.0`

### 4. Install and Verify
Run the installer and after installation:
```cmd
"C:\Program Files\ManagedNebula\nebula.exe" -version
```
Expected output: `Nebula v1.10.0`

## Detailed Verification Steps

### Pre-Installation Check (Upgrade Scenario)

If testing an upgrade from 1.9.7 to 1.10.0:

1. **Verify current version:**
   ```cmd
   "C:\Program Files\ManagedNebula\nebula.exe" -version
   ```
   Should show: `Nebula v1.9.7`

2. **Note file timestamp:**
   ```cmd
   dir "C:\Program Files\ManagedNebula\nebula.exe"
   ```

### Build Verification

1. **Clean build environment:**
   ```cmd
   rmdir /s /q dist
   rmdir /s /q build
   del /q nebula-*.zip
   ```

2. **Run build with version flag:**
   ```cmd
   build-installer.bat --version 1.0.1 --nebula-version 1.10.0
   ```

3. **Check for success indicators:**
   - Build completes without errors
   - Output shows: "Nebula binaries ready"
   - Output shows: "Verifying Nebula version..."
   - Output shows: "Downloaded version: Nebula v1.10.0"

4. **Verify build output:**
   ```cmd
   dir dist\ManagedNebula-*-Setup.exe
   ```
   Should show a file like: `ManagedNebula-1.0.1-Setup.exe`

### Installation Verification

1. **Run installer:**
   - Double-click `ManagedNebula-1.0.1-Setup.exe`
   - Watch installation details window for:
     - "Installing Managed Nebula 1.0.1"
     - "Nebula Version: 1.10.0"
     - "Verifying Nebula version..."
     - "Nebula binary verified successfully"

2. **Post-installation check:**
   ```cmd
   "C:\Program Files\ManagedNebula\nebula.exe" -version
   ```
   Should show: `Nebula v1.10.0`

3. **Verify file was updated (upgrade scenario):**
   ```cmd
   dir "C:\Program Files\ManagedNebula\nebula.exe"
   ```
   Timestamp should be newer than pre-upgrade

4. **Check other binaries:**
   ```cmd
   "C:\Program Files\ManagedNebula\nebula-cert.exe" -version
   ```
   Should also show: `Nebula v1.10.0`

### Functional Testing

1. **Test Nebula configuration:**
   ```cmd
   cd "C:\Program Files\ManagedNebula"
   nebula.exe -version
   nebula-cert.exe -version
   ```

2. **Check service status:**
   ```powershell
   Get-Service NebulaAgent
   ```

3. **Test agent functionality:**
   ```cmd
   NebulaAgent.exe --version
   NebulaAgent.exe --status
   ```

## Common Issues and Solutions

### Issue: Version shows 1.9.7 after upgrade

**Cause:** Old binaries not properly overwritten

**Solution:**
1. Uninstall Managed Nebula
2. Delete `C:\Program Files\ManagedNebula`
3. Rebuild installer with clean cache:
   ```cmd
   del /q nebula-*.zip
   rmdir /s /q dist
   build-installer.bat --nebula-version 1.10.0
   ```
4. Reinstall

### Issue: Build fails with "Failed to download Nebula binaries"

**Possible Causes:**
- Network connectivity issue
- Invalid version number
- GitHub releases unavailable

**Solution:**
1. Verify version exists at: https://github.com/slackhq/nebula/releases
2. Check internet connection
3. Try with a known-good version:
   ```cmd
   build-installer.bat --nebula-version 1.9.7
   ```

### Issue: Download completes but version is wrong

**Cause:** Cached zip file from previous build

**Solution:**
The build script now automatically cleans cached files, but you can manually clean:
```cmd
del /q nebula-*.zip
del /q nebula.exe
del /q nebula-cert.exe
```

### Issue: Installer builds but version verification fails

**Cause:** Corrupted download or incompatible binary

**Solution:**
1. Delete the dist directory:
   ```cmd
   rmdir /s /q dist
   ```
2. Rebuild from scratch
3. If problem persists, try downloading manually:
   ```cmd
   curl -L -o nebula.zip https://github.com/slackhq/nebula/releases/download/v1.10.0/nebula-windows-amd64.zip
   ```

## Testing Checklist

Use this checklist when testing the upgrade fix:

- [ ] **Build Test**
  - [ ] Clean environment (no cached files)
  - [ ] Build with `--nebula-version 1.10.0` succeeds
  - [ ] Build output shows correct version being downloaded
  - [ ] Build output shows version verification passed
  - [ ] Installer file created in `dist/` directory

- [ ] **Fresh Installation Test**
  - [ ] Install on clean Windows 10/11 VM
  - [ ] Installation completes without errors
  - [ ] `nebula.exe -version` shows v1.10.0
  - [ ] Service installs and starts correctly
  - [ ] Agent connects to server

- [ ] **Upgrade Test**
  - [ ] Install version with Nebula 1.9.7 first
  - [ ] Verify `nebula.exe -version` shows v1.9.7
  - [ ] Run new installer with 1.10.0
  - [ ] Verify `nebula.exe -version` shows v1.10.0
  - [ ] Service continues running after upgrade
  - [ ] Configuration preserved

- [ ] **Documentation Test**
  - [ ] README.md updated with verification steps
  - [ ] Build output matches documentation
  - [ ] Troubleshooting steps are accurate

## Automated Testing Script

For CI/CD or automated testing, use this PowerShell script:

```powershell
# test-nebula-version.ps1
param(
    [string]$ExpectedVersion = "1.10.0"
)

$ErrorActionPreference = "Stop"

Write-Host "Testing Nebula version upgrade..." -ForegroundColor Cyan

# Check if nebula.exe exists
$nebulaPath = "C:\Program Files\ManagedNebula\nebula.exe"
if (-not (Test-Path $nebulaPath)) {
    Write-Error "Nebula.exe not found at: $nebulaPath"
    exit 1
}

# Get version
$versionOutput = & $nebulaPath -version 2>&1
Write-Host "Installed version: $versionOutput" -ForegroundColor Yellow

# Check if version matches
if ($versionOutput -match "v?$ExpectedVersion") {
    Write-Host "✓ Version matches expected: v$ExpectedVersion" -ForegroundColor Green
    exit 0
} else {
    Write-Error "✗ Version mismatch! Expected: v$ExpectedVersion, Got: $versionOutput"
    exit 1
}
```

Usage:
```cmd
powershell -ExecutionPolicy Bypass -File test-nebula-version.ps1 -ExpectedVersion 1.10.0
```

## Version Matrix

Tested configurations:

| Installer Version | Nebula Version | Status | Notes |
|-------------------|----------------|--------|-------|
| 1.0.0 | 1.9.7 | ✓ | Baseline |
| 1.0.0 | 1.10.0 | ✓ | Target version |
| 1.0.1 | 1.10.0 | ✓ | Upgrade scenario |

## References

- [Nebula Releases](https://github.com/slackhq/nebula/releases)
- [Windows Client README](README.md)
- [Issue: Windows installer not upgrading Nebula binary](https://github.com/kumpeapps/managed-nebula/issues/XXX)
