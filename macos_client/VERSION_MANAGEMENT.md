# macOS Client Version Management

## Overview

The macOS client version is managed through a `VERSION` resource file that is embedded in the binary during build time. This ensures that the version is always available, whether the app is run as a standalone executable or as an app bundle.

## Version Sources (Priority Order)

The client checks for version information in the following order:

1. **Environment Variable**: `CLIENT_VERSION_OVERRIDE` (for testing/debugging)
2. **App Bundle Info.plist**: `CFBundleShortVersionString` (when running as `.app`)
3. **Embedded Resource**: `Resources/VERSION` file (when running as executable)
4. **Fallback**: `"unknown"` (if none of the above are available)

## Setting the Version

### During Build

All build scripts accept a `VERSION` environment variable:

```bash
# Build with specific version
VERSION=1.2.3 make build

# Create app bundle with version
VERSION=1.2.3 ./create-app-bundle.sh

# Install with version
VERSION=1.2.3 ./install.sh

# Create installer with version
VERSION=1.2.3 ./create-installer.sh
```

### Default Version

If `VERSION` is not specified, the default is `1.0.0`.

### For Development

Debug builds automatically append `-dev` to the version:

```bash
make debug  # Creates version 1.0.0-dev
VERSION=2.0.0 make debug  # Creates version 2.0.0-dev
```

## How It Works

1. **Build Time**: The VERSION file is created after compilation
   - Location: `.build/release/VERSION` (or `.build/debug/VERSION`)
   - Content: Plain text version string (e.g., `1.0.0`)

2. **Installation**: The VERSION file is copied alongside the executable
   - Executable: `/usr/local/bin/ManagedNebula`
   - VERSION file: `/usr/local/bin/VERSION`
   - App bundle: `ManagedNebula.app/Contents/MacOS/VERSION`

3. **Runtime**: The app reads the version from multiple sources:
   - First checks environment variable `CLIENT_VERSION_OVERRIDE`
   - Then checks Info.plist `CFBundleShortVersionString` (app bundles)
   - Finally reads `VERSION` file next to the executable
   - Falls back to "unknown" if none found

## Version Reporting to Server

When the client polls the server for configuration updates:

1. It calls `getClientVersion()` to get the version
2. It passes the version in the API request: `POST /v1/client/config`
3. The server stores it in the `clients` table (`client_version` column)
4. The web UI displays version status and update availability

## Testing Version Override

For testing, you can override the version without rebuilding:

```bash
CLIENT_VERSION_OVERRIDE="test-1.2.3" /usr/local/bin/ManagedNebula
```

This is useful for:
- Testing version detection logic
- Simulating different client versions
- Debugging version-related issues

## Checking Current Version

### From Command Line

```bash
# If installed as app bundle
defaults read /Applications/ManagedNebula.app/Contents/Info.plist CFBundleShortVersionString

# If installed as executable, check the embedded resource
strings /usr/local/bin/ManagedNebula | grep -A1 "VERSION"
```

### From UI

Open the app and check:
- Menu bar → About ManagedNebula
- Preferences window → Version display at bottom

### From Server

Check the client's version in the web UI:
1. Navigate to Clients page
2. View the client details
3. Check "Version Status" section

## Updating Version for Release

1. **Update VERSION file** (if desired, though build scripts will overwrite it):
   ```bash
   echo "1.2.3" > ManagedNebula/Sources/Resources/VERSION
   ```

2. **Build with new version**:
   ```bash
   VERSION=1.2.3 make build
   ```

3. **Create installer**:
   ```bash
   VERSION=1.2.3 ./create-installer.sh
   ```

4. **Verify version**:
   ```bash
   /usr/local/bin/ManagedNebula &
   # Check logs for: [PollingService] Detected client version: 1.2.3
   ```

## Troubleshooting

### Version Shows as "unknown"

Possible causes:
1. VERSION file not embedded properly
   - Check: `swift package describe` includes Resources
   - Fix: Ensure `Package.swift` has `resources: [.copy("Resources/VERSION")]`

2. VERSION file is empty or malformed
   - Check: `cat ManagedNebula/Sources/Resources/VERSION`
   - Fix: Rebuild with `VERSION=x.y.z make build`

3. Build artifacts are stale
   - Fix: `make clean && VERSION=x.y.z make build`

### Version Not Reporting to Server

1. Check client logs:
   ```bash
   tail -f ~/Library/Logs/ManagedNebula/nebula.log
   ```
   Look for: `[PollingService] Detected client version: ...`

2. Check API request logs (added debug logging):
   ```
   [APIClient] Client version: x.y.z, Nebula version: ...
   [APIClient] Request body: {"token":"...","public_key":"...","client_version":"x.y.z",...}
   ```

3. Check server logs:
   ```bash
   docker logs nebula-server
   ```
   Look for: `[API] Updating client version to: x.y.z`

4. Verify database:
   ```sql
   SELECT name, client_version, nebula_version, last_version_report_at FROM clients;
   ```

## Implementation Details

### Swift Code

```swift
// In PollingService.swift
private func getClientVersion() -> String {
    // 1. Check override
    if let override = ProcessInfo.processInfo.environment["CLIENT_VERSION_OVERRIDE"] {
        return override
    }
    
    // 2. Check Info.plist (app bundle)
    if let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String {
        return version
    }
    
    // 3. Check VERSION file next to executable
    if let executablePath = Bundle.main.executablePath {
        let executableURL = URL(fileURLWithPath: executablePath)
        let versionURL = executableURL.deletingLastPathComponent().appendingPathComponent("VERSION")
        if let versionString = try? String(contentsOf: versionURL, encoding: .utf8) {
            return versionString.trimmingCharacters(in: .whitespacesAndNewlines)
        }
    }
    
    // 4. Fallback
    return "unknown"
}
```

## Related Files

- `.build/release/VERSION` (or `.build/debug/VERSION`) - Version file created during build
- `/usr/local/bin/VERSION` - Installed VERSION file (standalone executable)
- `ManagedNebula.app/Contents/MacOS/VERSION` - VERSION file in app bundle
- `ManagedNebula/Sources/Services/PollingService.swift` - Version detection logic
- `Package.swift` - Executable target definition
- `Makefile` - Build with VERSION creation
- `install.sh` - Install with VERSION file
- `create-app-bundle.sh` - App bundle creation with VERSION
- `create-installer.sh` - Installer creation with VERSION
