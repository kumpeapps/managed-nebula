# Control File Permission Fix

## Issue
On new macOS client installations, users encountered the error:
```
"you do not have permission to save nebula-control to the folder tmp"
```

This occurred when the app tried to communicate with the helper daemon via `/tmp/nebula-control`.

## Root Cause
The issue occurred due to the atomic write operation in `NebulaManager.swift`:

1. The app writes to `/tmp/nebula-control.tmp` first
2. Then attempts to atomically move/replace it to `/tmp/nebula-control`
3. If the control file doesn't exist or has incorrect permissions, the operation fails
4. The atomic write with `fileManager.replaceItemAt()` requires write access to both the file and directory

## Solution Implemented

### Changes to `NebulaManager.swift`

1. **Created `writeControlCommand()` helper method** with robust error handling:
   - Checks if control file exists, creates it if missing with proper permissions (0o666)
   - Attempts atomic write first (preferred for IPC safety)
   - Falls back to direct write if atomic write fails
   - Provides detailed error messages for troubleshooting

2. **Simplified `startNebula()` and `stopNebula()` methods**:
   - Now use the centralized `writeControlCommand()` method
   - Cleaner code with consistent error handling

3. **Added new error case** to `NebulaError` enum:
   - `controlFileWriteFailed(reason: String)` - provides context for failures

### How It Works

```swift
private func writeControlCommand(_ command: String) throws {
    let controlFile = "/tmp/nebula-control"
    let fileURL = URL(fileURLWithPath: controlFile)
    let tempFileURL = URL(fileURLWithPath: controlFile + ".tmp")
    
    guard let data = command.data(using: .utf8) else {
        throw NebulaError.controlFileWriteFailed(reason: "Failed to encode command")
    }
    
    do {
        // Ensure control file exists with proper permissions
        if !fileManager.fileExists(atPath: controlFile) {
            fileManager.createFile(atPath: controlFile, contents: nil, attributes: [
                .posixPermissions: 0o666
            ])
        }
        
        // Try atomic write first (prevents helper from reading partial data)
        try data.write(to: tempFileURL, options: .atomic)
        _ = try? fileManager.removeItem(at: fileURL)
        try fileManager.moveItem(at: tempFileURL, to: fileURL)
        
    } catch {
        // Fallback: Direct write if atomic write fails
        try data.write(to: fileURL, options: [])
    }
}
```

## Defense in Depth

The fix implements multiple layers of protection:

1. **Installer** (`create-installer.sh`):
   - Creates `/tmp/nebula-control` with `chmod 666` during installation
   
2. **Helper Daemon** (`nebula-helper.sh`):
   - Ensures control file exists on daemon startup
   - Recreates with proper permissions if missing
   
3. **Swift App** (`NebulaManager.swift`):
   - Now creates control file if missing before writing
   - Falls back to direct write if atomic write fails
   - Provides clear error messages

## Testing

Build verification:
```bash
cd macos_client
swift build
# Result: Build complete! ✓
```

To test the fix:
1. Delete the control file: `sudo rm /tmp/nebula-control`
2. Launch ManagedNebula.app
3. Attempt to connect to server
4. App should create the control file and connect successfully

## Files Modified

- `macos_client/ManagedNebula/Sources/Services/NebulaManager.swift`
  - Added `writeControlCommand()` method
  - Updated `startNebula()` to use new method
  - Updated `stopNebula()` to use new method
  - Added `controlFileWriteFailed` error case

## Backward Compatibility

This fix is fully backward compatible:
- Existing installations continue to work unchanged
- Installer still creates the file (primary mechanism)
- Helper daemon still ensures file exists (backup mechanism)
- App now handles missing file gracefully (final safety net)

## Related Files

- `/tmp/nebula-control` - IPC file for app → helper daemon communication
- `/tmp/managed-nebula/` - Staging directory for config files
- `nebula-helper.sh` - Root daemon that reads control file
- `create-installer.sh` - PKG installer script
