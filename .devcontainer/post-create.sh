#!/bin/bash
set -e

echo "=========================================="
echo "Setting up dev container..."
echo "=========================================="

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Install pre-commit and ggshield
echo "Installing pre-commit and ggshield..."
pip3 install pre-commit ggshield

# Install pre-commit hooks
echo "Installing pre-commit git hooks..."
pre-commit install

# Check if ggshield is authenticated
echo ""
echo "=========================================="
echo "Checking GitGuardian authentication..."
echo "=========================================="

if ! ggshield auth status &>/dev/null; then
    echo ""
    echo "⚠️  GitGuardian is not authenticated."
    echo "You need to authenticate to use pre-commit hooks with GitGuardian."
    echo ""
    echo "Please run the following command when ready:"
    echo "  ggshield auth login"
    echo ""
else
    echo "✓ GitGuardian is already authenticated"
fi

echo ""
echo "=========================================="
echo "Dev container setup complete!"
echo "=========================================="
echo "Ports forwarded: 8443 (Frontend HTTPS), 8080 (Server API), 4200 (Frontend Dev)"
echo ""
if ! ggshield auth status &>/dev/null; then
    echo "⚠️  Remember to run: ggshield auth login"
fi
