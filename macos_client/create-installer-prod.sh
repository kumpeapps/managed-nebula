#!/bin/bash
# Script to create a production-signed installer using Fastlane
# This is now a simple wrapper around Fastlane's build_production lane

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=== ManagedNebula Production Installer Creator ==="
echo ""
echo "Using Fastlane for certificate management, signing, and notarization..."
echo ""

# Prompt for MATCH_PASSWORD if not set
if [ -z "$MATCH_PASSWORD" ]; then
    read -sp "Enter Fastlane Match password (encryption key): " MATCH_PASSWORD
    echo ""
    export MATCH_PASSWORD
fi

# Prompt for notarization credentials if not set via Appfile
if [ -z "$FASTLANE_APPLE_ID" ]; then
    read -p "Enter Apple ID email: " FASTLANE_APPLE_ID
    export FASTLANE_APPLE_ID
fi

if [ -z "$FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD" ]; then
    read -sp "Enter App-Specific Password: " FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD
    echo ""
    export FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD
fi

cd "${SCRIPT_DIR}"
/usr/local/bin/fastlane mac build_production

echo ""
echo "=== Production Build Complete ==="
echo ""
echo "Signed installer packages created in: ${SCRIPT_DIR}/dist/"
echo ""
echo "Files:"
echo "  - ManagedNebula-1.0.0-signed.pkg (Signed & Notarized PKG)"
echo "  - ManagedNebula-1.0.0-signed.dmg (Signed DMG with app bundle)"
echo ""
echo "Verification commands:"
echo "  pkgutil --check-signature dist/ManagedNebula-1.0.0-signed.pkg"
echo "  spctl -a -vv -t install dist/ManagedNebula-1.0.0-signed.pkg"
echo "  codesign -dvv ManagedNebula.app"
echo ""
