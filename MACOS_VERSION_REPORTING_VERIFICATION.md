# macOS Client Version Reporting - Verification Guide

## Overview
This document describes how to verify that the macOS client correctly reports version information to the server.

## Implementation Summary

### Changes Made

1. **Configuration.swift** (Models)
   - Added optional `clientVersion: String?` field to `ClientConfigRequest`
   - Added optional `nebulaVersion: String?` field to `ClientConfigRequest`
   - Added corresponding `CodingKeys` for snake_case API mapping

2. **APIClient.swift** (Services)
   - Updated `fetchConfig()` signature to accept optional `clientVersion` and `nebulaVersion` parameters
   - Pass version parameters to request body when encoding

3. **PollingService.swift** (Services)
   - Added `getClientVersion()` helper method that:
     - Checks `CLIENT_VERSION_OVERRIDE` environment variable first
     - Falls back to reading `CFBundleShortVersionString` from app bundle
     - Returns "unknown" if neither is available
   - Updated `checkForUpdates()` to:
     - Call `getClientVersion()` to get client version
     - Call `nebulaManager.getNebulaVersion()` to get Nebula version (already existed)
     - Pass both versions to `apiClient.fetchConfig()`

4. **Documentation**
   - Updated `macos_client/README.md` with version field examples
   - Updated `macos_client/IMPLEMENTATION_SUMMARY.md` with version reporting details
   - Updated `VERSION_CHECKING_FEATURE.md` with macOS client section

## Server-Side Support

The server already supports version reporting (implemented in issue #93):

**Endpoint**: `POST /v1/client/config`

**Request Schema** (`server/app/models/schemas.py`):
```python
class ClientConfigRequest(BaseModel):
    token: str
    public_key: str
    client_version: Optional[str] = None  # ✅ Optional - supports older clients
    nebula_version: Optional[str] = None  # ✅ Optional - supports older clients
```

**Server Behavior** (`server/app/routers/api.py` lines 609-621):
```python
# Update last config download timestamp and version info
try:
    client.last_config_download_at = datetime.utcnow()
    if body.client_version:
        client.client_version = body.client_version
    if body.nebula_version:
        client.nebula_version = body.nebula_version
    if body.client_version or body.nebula_version:
        client.last_version_report_at = datetime.utcnow()
    await session.commit()
except Exception:
    # Timestamp update is non-critical; log and continue
    pass
```

The server:
- ✅ Accepts optional version fields in the request
- ✅ Updates client record with version information
- ✅ Updates `last_version_report_at` timestamp
- ✅ Continues working if version fields are missing (backward compatible)
- ✅ Handles update failures gracefully (non-critical operation)

## Testing Prerequisites

### Required Environment
- **macOS**: 12 (Monterey) or later
- **Xcode**: With Swift 5.9+ toolchain
- **Nebula Binary**: Installed at `/usr/local/bin/nebula`
- **Server**: Running Managed Nebula server (v1.0.0+)

### Test Setup
1. Build and install the macOS client
2. Configure server URL and client token
3. Ensure Nebula binary is installed
4. Have access to server web UI

## Verification Steps

### 1. Build the macOS Client

```bash
cd macos_client
make build
```

Expected output: Build succeeds without errors

### 2. Check Bundle Version

```bash
# If using app bundle
defaults read /Applications/ManagedNebula.app/Contents/Info.plist CFBundleShortVersionString

# Should output something like: 1.0.0
```

### 3. Check Nebula Version Detection

```bash
/usr/local/bin/nebula -version
```

Expected output:
```
Version: 1.9.7
Build: ...
```

### 4. Run the Client

Start the macOS client and connect to the server. Monitor the console logs:

```bash
# If running from terminal
./build/release/ManagedNebula

# Check logs
tail -f ~/Library/Logs/ManagedNebula/nebula.log
```

Expected log output in PollingService:
```
[PollingService] Configuration check completed successfully
```

### 5. Verify Version Reporting via API

Using the server API, check that the client's version information was updated:

```bash
# Login and get session cookie
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin"}' \
  -c cookies.txt

# Get client details
curl -X GET http://localhost:8080/api/v1/clients/{client_id} \
  -b cookies.txt
```

Expected response (relevant fields):
```json
{
  "id": 1,
  "name": "my-macos-client",
  "client_version": "1.0.0",
  "nebula_version": "1.9.7",
  "last_version_report_at": "2025-11-24T17:30:00Z",
  "version_status": {
    "client_version_status": "current",
    "nebula_version_status": "current"
  }
}
```

### 6. Verify Web UI Display

1. Open the Managed Nebula web interface
2. Navigate to **Clients** page
3. Find the macOS client in the list

**Expected UI Elements**:
- Version column shows "1.0.0 / 1.9.7" (or actual versions)
- Status icon shows:
  - 🟢 Green circle if versions are current
  - 🟡 Yellow circle if outdated
  - 🔴 Red circle if vulnerable
  - ⚪ Gray circle if unknown (should NOT appear if reporting works)

4. Click on the client to view details
5. Check the "Version Status" section

**Expected Details Section**:
```
Version Status
--------------
Client Version: 1.0.0 (✅ Current)
Nebula Version: 1.9.7 (✅ Current)
Last Reported: 2025-11-24 17:30:00 UTC
```

### 7. Test Environment Override

Test that the environment override works:

```bash
# Set override
export CLIENT_VERSION_OVERRIDE="test-version-1.2.3"

# Run client
./build/release/ManagedNebula --once

# Check via API
curl -X GET http://localhost:8080/api/v1/clients/{client_id} -b cookies.txt | jq '.client_version'
```

Expected: `"test-version-1.2.3"`

### 8. Test Missing Nebula Binary

Temporarily rename Nebula binary to test error handling:

```bash
# Rename binary
sudo mv /usr/local/bin/nebula /usr/local/bin/nebula.backup

# Run client (should still work, but nebula_version will be "Unknown")
./build/release/ManagedNebula --once

# Check version
curl -X GET http://localhost:8080/api/v1/clients/{client_id} -b cookies.txt | jq '.nebula_version'

# Restore binary
sudo mv /usr/local/bin/nebula.backup /usr/local/bin/nebula
```

Expected: `"Unknown"` (client still connects successfully)

## Validation Checklist

- [ ] macOS client builds without errors
- [ ] `getClientVersion()` returns correct bundle version
- [ ] `getNebulaVersion()` returns correct Nebula version
- [ ] Client successfully connects to server
- [ ] Server receives and stores `client_version`
- [ ] Server receives and stores `nebula_version`
- [ ] Server updates `last_version_report_at` timestamp
- [ ] Web UI displays version information correctly
- [ ] Version status indicators appear (green/yellow/red)
- [ ] Client detail page shows version status section
- [ ] `CLIENT_VERSION_OVERRIDE` environment variable works
- [ ] Client continues working if Nebula version detection fails

## Expected Behavior

### Normal Operation
1. macOS client detects versions on every config fetch
2. Versions are sent to server in POST request body
3. Server updates client record with version info
4. Web UI displays current version status
5. Administrators can see which clients need updates

### Error Handling
- If bundle version not found → uses "unknown"
- If Nebula version detection fails → uses "Unknown"
- If server doesn't support version fields → continues normally (backward compatible)
- Version detection failures don't prevent VPN connectivity

## Comparison with Python Client

| Feature | Python Client | macOS Client | Status |
|---------|--------------|--------------|--------|
| Client version detection | `__version__` constant | Bundle `CFBundleShortVersionString` | ✅ Equivalent |
| Nebula version detection | `nebula -version` subprocess | `nebula -version` subprocess | ✅ Same |
| Environment override | `CLIENT_VERSION_OVERRIDE` | `CLIENT_VERSION_OVERRIDE` | ✅ Same |
| Nebula override | `NEBULA_VERSION_OVERRIDE` | N/A (could be added) | ⚠️ Missing |
| API field names | `client_version`, `nebula_version` | `client_version`, `nebula_version` | ✅ Same |
| Optional fields | Yes | Yes | ✅ Same |

## Known Limitations

1. **macOS-only testing**: Cannot build or test on Linux/Windows
2. **Nebula override**: Python client supports `NEBULA_VERSION_OVERRIDE`, macOS client doesn't (not critical)
3. **Bundle requirement**: Client version detection requires proper app bundle with Info.plist

## Troubleshooting

### Version shows as "unknown" in UI

**Possible causes**:
1. App not properly bundled (missing Info.plist)
2. `CFBundleShortVersionString` not set in Info.plist
3. Client hasn't connected since update

**Solutions**:
1. Verify Info.plist exists and contains version
2. Rebuild app bundle with `create-app-bundle.sh`
3. Trigger manual config update from menu bar

### Nebula version shows as "Unknown"

**Possible causes**:
1. Nebula binary not in `/usr/local/bin/nebula`
2. Permission denied executing `nebula -version`
3. Nebula binary is corrupted

**Solutions**:
1. Install Nebula to correct location
2. Make binary executable: `chmod +x /usr/local/bin/nebula`
3. Reinstall Nebula binary

### Version not appearing in web UI

**Possible causes**:
1. Server version too old (pre-#93)
2. Client hasn't connected since upgrade
3. Database migration not applied

**Solutions**:
1. Upgrade server to latest version
2. Force config refresh from client menu bar
3. Run Alembic migrations: `alembic upgrade head`

## Files Modified

- `macos_client/ManagedNebula/Sources/Models/Configuration.swift`
- `macos_client/ManagedNebula/Sources/Services/APIClient.swift`
- `macos_client/ManagedNebula/Sources/Services/PollingService.swift`
- `macos_client/README.md`
- `macos_client/IMPLEMENTATION_SUMMARY.md`
- `VERSION_CHECKING_FEATURE.md`

## Related Issues

- #93 - Version Checking and Security Advisory System (server-side implementation)
- #94 - Docker compose template feature (current branch context)

## Conclusion

The macOS client now reports version information identically to the Python client, enabling:
- ✅ Version tracking in web UI
- ✅ Security advisory notifications
- ✅ Outdated client detection
- ✅ Better fleet management visibility

All changes are backward compatible and non-breaking.
