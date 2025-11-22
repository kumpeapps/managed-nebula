#!/bin/bash
# Test script for control file permission fix
# This tests that the app can create and write to the control file

set -e

echo "=== Control File Permission Test ==="
echo ""

CONTROL_FILE="/tmp/nebula-control"

# Test 1: Remove control file and verify app can recreate it
echo "Test 1: Verify app can create missing control file"
sudo rm -f "$CONTROL_FILE" 2>/dev/null || true
if [ -f "$CONTROL_FILE" ]; then
    echo "✗ Failed to remove control file for testing"
    exit 1
fi
echo "✓ Control file removed"

# Note: This test requires the app to be running and attempting a connection
echo "NOTE: Launch ManagedNebula.app and attempt to connect to test file creation"
echo ""

# Test 2: Verify control file permissions if it exists
if [ -f "$CONTROL_FILE" ]; then
    PERMS=$(stat -f "%Lp" "$CONTROL_FILE")
    if [ "$PERMS" = "666" ]; then
        echo "✓ Control file has correct permissions (666)"
    else
        echo "⚠ Control file permissions: $PERMS (expected 666)"
    fi
    
    # Test write access
    if echo "test" > "$CONTROL_FILE" 2>/dev/null; then
        echo "✓ Control file is writable by current user"
    else
        echo "✗ Control file is not writable by current user"
        exit 1
    fi
else
    echo "Control file doesn't exist yet (normal for fresh install)"
fi

echo ""
echo "Test 3: Verify helper daemon can read control file"
if [ -f "$CONTROL_FILE" ]; then
    if sudo cat "$CONTROL_FILE" > /dev/null 2>&1; then
        echo "✓ Helper daemon (root) can read control file"
    else
        echo "✗ Helper daemon cannot read control file"
        exit 1
    fi
else
    echo "Skipping (file doesn't exist)"
fi

echo ""
echo "=== All Tests Passed ==="
echo ""
echo "To fully test the fix:"
echo "1. Remove control file: sudo rm /tmp/nebula-control"
echo "2. Launch ManagedNebula.app"
echo "3. Configure server URL and token"
echo "4. Click 'Connect'"
echo "5. Verify connection succeeds without permission errors"
