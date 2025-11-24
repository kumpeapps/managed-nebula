# macOS Version Reporting Fix

## Problem

The macOS client was not reporting its version to the server. The version always appeared as "unknown" in the server database and web UI.

## Root Cause

The macOS client was using `Bundle.main.infoDictionary?["CFBundleShortVersionString"]` to retrieve the version, which only works when the app is running as an app bundle (`.app`). However:

1. The `install.sh` script copies the raw executable to `/usr/local/bin/ManagedNebula`
2. When running as a standalone executable (not in an app bundle), `Bundle.main` doesn't have access to Info.plist
3. This caused `getClientVersion()` to always return `"unknown"`

## Solution

Implemented a multi-layered version detection system using a VERSION file alongside the executable:

1. **Created VERSION File System**: The VERSION file is created next to the executable after build
   - Location: `.build/release/VERSION` or `.build/debug/VERSION`
   - Installed to: `/usr/local/bin/VERSION` or `ManagedNebula.app/Contents/MacOS/VERSION`

2. **Updated getClientVersion()**: Modified to check three sources in priority order:
   - Environment variable `CLIENT_VERSION_OVERRIDE` (for testing)
   - App bundle Info.plist `CFBundleShortVersionString` (for .app bundles)
   - VERSION file next to the executable (for standalone executables)
   - Fallback to `"unknown"`

3. **Updated Build Scripts**: Modified all build scripts to create VERSION file after building:
   - `Makefile` (make build/debug)
   - `install.sh` (copies VERSION file alongside executable)
   - `create-app-bundle.sh` (copies VERSION into app bundle)

5. **Added Debug Logging**: Added logging to help diagnose version reporting issues:
   - Client logs version detection
   - Client logs API request body
   - Server logs version updates

## Files Changed

### macOS Client
- `ManagedNebula/Sources/Services/PollingService.swift` - Updated version detection logic with logging
- `ManagedNebula/Sources/Services/APIClient.swift` - Added debug logging for request
- `Makefile` - Updated to create VERSION file after build
- `install.sh` - Updated to copy VERSION file alongside executable
- `create-app-bundle.sh` - Updated to copy VERSION file into app bundle
- `VERSION_MANAGEMENT.md` - New documentation for version management

### Server
- `server/app/routers/api.py` - Added debug logging for version updates

## How It Works

### Build Time
```bash
VERSION=1.2.3 make build
# 1. swift build -c release (compiles the binary)
# 2. Creates .build/release/VERSION with "1.2.3"
```

### Installation
```bash
sudo cp .build/release/ManagedNebula /usr/local/bin/
sudo cp .build/release/VERSION /usr/local/bin/
# Now VERSION file is at /usr/local/bin/VERSION
```

### Runtime
```swift
// 1. Check env override
if let override = ProcessInfo.processInfo.environment["CLIENT_VERSION_OVERRIDE"] {
    return override
}

// 2. Check app bundle (for .app)
if let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String {
    return version
}

// 3. Check VERSION file next to executable ✅ NEW
if let executablePath = Bundle.main.executablePath {
    let versionURL = URL(fileURLWithPath: executablePath)
        .deletingLastPathComponent()
        .appendingPathComponent("VERSION")
    if let versionString = try? String(contentsOf: versionURL, encoding: .utf8) {
        return versionString.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

// 4. Fallback
return "unknown"
```

### Server Side
```python
# Server receives version in request
if body.client_version:
    print(f"[API] Updating client version to: {body.client_version}")
    client.client_version = body.client_version
    client.last_version_report_at = datetime.utcnow()
await session.commit()
```

## Testing

### Verify Version in Binary
```bash
# Check embedded resource
strings /usr/local/bin/ManagedNebula | grep -A1 "VERSION"
```

### Check Logs
```bash
# Client logs
tail -f ~/Library/Logs/ManagedNebula/nebula.log
# Look for: [PollingService] Detected client version: 1.0.0
# Look for: [APIClient] Client version: 1.0.0, Nebula version: ...
```

### Check Server
```bash
# Server logs
docker logs nebula-server
# Look for: [API] Updating client version to: 1.0.0
```

### Verify Database
```sql
SELECT name, client_version, nebula_version, last_version_report_at FROM clients;
```

### Check Web UI
1. Navigate to Clients page
2. Check version column
3. View client details for version status

## Build Instructions

### For Development
```bash
cd macos_client
make clean
VERSION=1.0.0 make build
```

### For Distribution (App Bundle)
```bash
cd macos_client
VERSION=1.2.3 ./create-app-bundle.sh
# Creates ManagedNebula.app with version in both:
# - Info.plist (CFBundleShortVersionString)
# - Embedded resource (Resources/VERSION)
```

### For Installer
```bash
cd macos_client
VERSION=1.2.3 ./create-installer.sh
# Creates .pkg and .dmg with version 1.2.3
```

## Benefits

1. **Works for All Execution Modes**: Version reporting now works whether running as:
   - App bundle (`.app`)
   - Standalone executable (`/usr/local/bin/ManagedNebula`)
   - Development build (`.build/release/ManagedNebula`)

2. **Single Source of Truth**: The VERSION file is the authoritative source, updated at build time

3. **Build-Time Configuration**: Version is set via `VERSION` environment variable during build

4. **Debug Support**: Environment override allows testing without rebuilding

5. **Backward Compatible**: Still reads from Info.plist when running as app bundle

## Related Issues

- Issue #107: Add version reporting to macOS client
- Issue #93: Server-side version tracking (already implemented)

## Documentation

See `macos_client/VERSION_MANAGEMENT.md` for comprehensive documentation on:
- Version management workflow
- Build commands
- Testing procedures
- Troubleshooting guide
