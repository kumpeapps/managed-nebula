#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Running Alembic migrations..."
# Run migrations (handles sqlite/mysql/postgres depending on DB_URL)
if alembic upgrade head; then
    echo "[entrypoint] Migrations completed successfully"
else
    echo "[entrypoint] WARNING: Migrations failed or had errors"
    echo "[entrypoint] Attempting to continue startup..."
fi

echo ""
echo "[entrypoint] ========================================"
echo "[entrypoint] Managed Nebula Server Starting"
echo "[entrypoint] ========================================"
echo "[entrypoint] "
echo "[entrypoint] Admin user creation:"
if [ -n "${ADMIN_EMAIL:-}" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
    echo "[entrypoint]   Auto-bootstrap enabled (ADMIN_EMAIL set)"
    echo "[entrypoint]   Will create admin if no users exist"
else
    echo "[entrypoint]   Auto-bootstrap disabled (ADMIN_EMAIL not set)"
    echo "[entrypoint]   Create admin manually:"
    echo "[entrypoint]     docker exec <container> python manage.py create-admin <email>"
fi
echo "[entrypoint] ========================================"
echo ""

echo "[entrypoint] Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
