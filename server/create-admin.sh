#!/bin/bash
# Quick script to create admin user - can be run inside container
# Usage: ./create-admin.sh email@example.com password

set -e

EMAIL="${1}"
PASSWORD="${2}"

if [ -z "$EMAIL" ]; then
    echo "Usage: $0 <email> [password]"
    echo ""
    echo "If password is not provided, you will be prompted."
    exit 1
fi

cd "$(dirname "$0")"

if [ -z "$PASSWORD" ]; then
    python3 manage.py create-admin "$EMAIL"
else
    python3 manage.py create-admin "$EMAIL" "$PASSWORD"
fi
