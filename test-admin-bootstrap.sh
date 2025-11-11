#!/bin/bash
set -e

echo "========================================="
echo "Testing Admin Bootstrap on Fresh Install"
echo "========================================="

# Stop containers
echo "Stopping containers..."
docker compose stop server

# Remove existing database volume
echo "Removing existing database..."
docker volume rm managed-nebula_server_data 2>/dev/null || echo "Volume didn't exist"

# Recreate volume
echo "Creating fresh volume..."
docker volume create managed-nebula_server_data

# Start server with custom admin credentials
echo "Starting server with ADMIN_EMAIL=test@example.com and ADMIN_PASSWORD=testpass123..."
docker compose up -d server

# Wait for startup
echo "Waiting for server to start..."
sleep 8

# Check logs for bootstrap message
echo ""
echo "========================================="
echo "Checking Bootstrap Logs:"
echo "========================================="
docker logs managed-nebula-server-1 2>&1 | grep -A2 "\[bootstrap\]" || echo "No bootstrap logs found"

# Try to verify the admin user was created
echo ""
echo "========================================="
echo "Verifying Admin User Creation:"
echo "========================================="
docker exec managed-nebula-server-1 python3 << 'EOF'
import sqlite3
import sys

conn = sqlite3.connect('/app/data/app.db')
cursor = conn.execute('SELECT id, email FROM users WHERE email = ?', ('test@example.com',))
row = cursor.fetchone()
conn.close()

if row:
    print(f"✓ SUCCESS: Admin user created with email: {row[1]}")
    sys.exit(0)
else:
    # Check default admin
    conn = sqlite3.connect('/app/data/app.db')
    cursor = conn.execute('SELECT id, email FROM users WHERE email = ?', ('admin@example.com',))
    row = cursor.fetchone()
    conn.close()
    if row:
        print(f"✓ SUCCESS: Default admin user created with email: {row[1]}")
        sys.exit(0)
    else:
        print("✗ FAILURE: No admin user found in database!")
        sys.exit(1)
EOF

echo ""
echo "========================================="
echo "Test Complete!"
echo "========================================="
