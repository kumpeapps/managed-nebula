#!/bin/bash
# Installation script for ManagedNebula macOS Client

set -e

NEBULA_VERSION="v1.8.2"
NEBULA_URL="https://github.com/slackhq/nebula/releases/download/${NEBULA_VERSION}/nebula-darwin.zip"
INSTALL_DIR="/usr/local/bin"

echo "=== ManagedNebula macOS Client Installer ==="
echo ""

# Check for macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: This installer is for macOS only"
    exit 1
fi

# Check for Homebrew (optional but recommended)
if command -v brew &> /dev/null; then
    echo "✓ Homebrew detected"
else
    echo "⚠ Homebrew not found (optional but recommended)"
fi

# Check for Swift
if command -v swift &> /dev/null; then
    SWIFT_VERSION=$(swift --version | head -n 1)
    echo "✓ Swift installed: $SWIFT_VERSION"
else
    echo "✗ Swift not found. Please install Xcode or Swift toolchain"
    exit 1
fi

echo ""
echo "Step 1: Installing Nebula binaries..."
echo ""

# Check if nebula is already installed
if command -v nebula &> /dev/null && command -v nebula-cert &> /dev/null; then
    CURRENT_VERSION=$(nebula -version 2>&1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
    echo "Nebula is already installed (version: $CURRENT_VERSION)"
    read -p "Do you want to reinstall/update? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping Nebula installation"
    else
        echo "Downloading Nebula ${NEBULA_VERSION}..."
        curl -L -o /tmp/nebula-darwin.zip "$NEBULA_URL"
        
        echo "Extracting..."
        cd /tmp
        unzip -q nebula-darwin.zip
        
        echo "Installing to ${INSTALL_DIR} (requires sudo)..."
        sudo mv nebula nebula-cert "${INSTALL_DIR}/"
        sudo chmod +x "${INSTALL_DIR}/nebula" "${INSTALL_DIR}/nebula-cert"
        
        echo "✓ Nebula installed successfully"
        rm -f /tmp/nebula-darwin.zip
    fi
else
    echo "Downloading Nebula ${NEBULA_VERSION}..."
    curl -L -o /tmp/nebula-darwin.zip "$NEBULA_URL"
    
    echo "Extracting..."
    cd /tmp
    unzip -q nebula-darwin.zip
    
    echo "Installing to ${INSTALL_DIR} (requires sudo)..."
    sudo mv nebula nebula-cert "${INSTALL_DIR}/"
    sudo chmod +x "${INSTALL_DIR}/nebula" "${INSTALL_DIR}/nebula-cert"
    
    echo "✓ Nebula installed successfully"
    rm -f /tmp/nebula-darwin.zip
fi

# Verify installation
if ! command -v nebula &> /dev/null; then
    echo "✗ Nebula installation failed"
    exit 1
fi

if ! command -v nebula-cert &> /dev/null; then
    echo "✗ nebula-cert installation failed"
    exit 1
fi

echo ""
echo "Step 2: Building ManagedNebula client..."
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Building release binary..."
swift build -c release

if [ ! -f ".build/release/ManagedNebula" ]; then
    echo "✗ Build failed"
    exit 1
fi

echo "✓ Build successful"

echo ""
echo "Step 3: Installing ManagedNebula..."
echo ""

read -p "Install to ${INSTALL_DIR}? (Y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "Skipping installation. Binary is at: .build/release/ManagedNebula"
    echo "You can run it manually: ./.build/release/ManagedNebula"
else
    sudo cp .build/release/ManagedNebula "${INSTALL_DIR}/"
    sudo chmod +x "${INSTALL_DIR}/ManagedNebula"
    echo "✓ Installed to ${INSTALL_DIR}/ManagedNebula"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Launch ManagedNebula: ${INSTALL_DIR}/ManagedNebula"
echo "   (or run: ./.build/release/ManagedNebula if not installed)"
echo "2. Click the menu bar icon and select 'Preferences'"
echo "3. Enter your server URL and client token"
echo "4. Click 'Connect' to start the VPN"
echo ""
echo "For more information, see README.md"
