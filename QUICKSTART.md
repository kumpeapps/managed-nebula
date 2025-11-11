# Managed Nebula - Quick Start Guide

## First Time Setup

If you see "No admin user exists" errors, create one manually:

```bash
# From host machine
docker exec -it managed-nebula-server python manage.py create-admin admin@example.com

# You'll be prompted for a password
```

## Useful Management Commands

### User Management
```bash
# Create admin user
docker exec -it managed-nebula-server python manage.py create-admin user@example.com

# List all users
docker exec managed-nebula-server python manage.py list-users

# Reset password
docker exec -it managed-nebula-server python manage.py reset-password user@example.com

# Make existing user an admin
docker exec managed-nebula-server python manage.py make-admin user@example.com
```

### Check Container Status
```bash
# View logs
docker logs managed-nebula-server

# Check if server is running
docker ps | grep managed-nebula

# Access container shell
docker exec -it managed-nebula-server bash
```

### Database Operations
```bash
# Check migration status
docker exec managed-nebula-server alembic current

# View migration history
docker exec managed-nebula-server alembic history

# Run migrations
docker exec managed-nebula-server alembic upgrade head
```

## Web Interface

- **Frontend**: http://localhost:4200
- **API Docs**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **Health Check**: http://localhost:8080/api/v1/healthz

## Environment Variables

Key variables to set in production:
- `DB_URL` - Database connection (default: SQLite)
- `SECRET_KEY` - Session encryption key (CHANGE THIS!)
- `ADMIN_EMAIL` - Auto-create admin on first start (optional)
- `ADMIN_PASSWORD` - Admin password (optional)

## Troubleshooting

### "No admin user exists"
Run: `docker exec -it managed-nebula-server python manage.py create-admin admin@example.com`

### "Connection refused"
Check if container is running: `docker ps`
Check logs: `docker logs managed-nebula-server`

### "Migration failed"
Reset database (WARNING: loses all data):
```bash
docker-compose down -v
docker-compose up -d
```

### "Can't connect to MySQL/PostgreSQL"
- Verify DB_URL is correct
- Ensure database server is accessible
- Check network connectivity: `docker exec managed-nebula-server ping database-host`
