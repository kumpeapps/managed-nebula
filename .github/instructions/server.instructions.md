---
applies_to:
  - server/**/*
  - "**/test_*.py"
  - "**/conftest.py"
---

# Server (FastAPI Backend) Instructions

## Overview
The server is a FastAPI REST API backend that manages Nebula VPN mesh networks. It handles certificate lifecycle, IP allocation, firewall rules, and group-based access control.

## Tech Stack
- **Framework**: FastAPI with async/await patterns
- **ORM**: SQLAlchemy (async) with proper session management
- **Migrations**: Alembic for database schema versioning
- **Testing**: pytest with TestClient
- **Authentication**: Session-based (frontend) and token-based (client agents)

## Development Commands

### Running the Server Locally
```bash
cd server
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Database Migrations
```bash
# Apply migrations
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "description"

# Check current version
alembic current
```

### Running Tests
```bash
cd server
pytest tests/ -v

# Skip tests requiring nebula-cert binary
pytest tests/ -m "not nebula_cert"

# Run specific test file
pytest tests/test_health.py -v
```

### Linting and Formatting
```bash
# Format code (if black is installed)
black app/ tests/

# Check imports (if isort is installed)
isort app/ tests/
```

## Key Patterns and Conventions

### Database Access
- **Always use async**: All database operations must use `AsyncSession` and `await`
- **Never use session.query()**: Use `session.execute(select(...))` for async compatibility
- **Eager loading**: Use `selectinload()` for relationships to avoid lazy-load errors
- **Always commit**: Don't forget `await session.commit()` after write operations

Example:
```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Correct async pattern
async def get_client_with_groups(db: AsyncSession, client_id: int):
    result = await db.execute(
        select(Client)
        .options(selectinload(Client.groups))
        .where(Client.id == client_id)
    )
    return result.scalar_one_or_none()
```

### API Endpoints
- **All endpoints under `/api/v1`**: Never create endpoints outside this prefix
- **Use Pydantic schemas**: All request/response models in `models/schemas.py`, never inline
- **Return proper status codes**: 200 (OK), 400 (validation), 401 (auth), 403 (forbidden), 404 (not found), 409 (conflict), 503 (service unavailable)
- **Dependency injection**: Use FastAPI dependencies for auth, database sessions
- **Admin checks**: Use `Depends(require_admin)` for privileged routes

Example:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.auth import get_current_user, require_admin
from app.models.schemas import ClientResponse, ClientUpdate

router = APIRouter(prefix="/api/v1")

@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Implementation
    pass
```

### Certificate Management
- Uses `nebula-cert` CLI via subprocess calls
- **CA Rotation**: Configurable validity (default 18mo), rotation at 12mo, 3mo overlap
- **Client Certificates**: 6-month validity, rotated 3 months before expiry
- **Certificate Reuse**: Only reissue if IP/CIDR/groups changed
- Key files managed in `services/cert_manager.py`

### Password Security
- **Always use bcrypt_sha256**: Not plain bcrypt (avoids 72-byte truncation)
- Import from `app.core.auth` module: `hash_password()`, `verify_password()`

### Testing Patterns
- Tests use `TestClient` from FastAPI
- Skip nebula-cert tests: `@pytest.mark.skipif(shutil.which("nebula-cert") is None)`
- Test pattern: create admin → create CA → create pool → create client → test
- No database mocking - use in-memory SQLite or test database

### Common Pitfalls to Avoid
- ❌ Don't use `session.query()` - incompatible with async
- ❌ Don't forget `await session.commit()` - changes won't persist
- ❌ Don't lazy-load relationships in async context - use `selectinload()`
- ❌ Don't define Pydantic models inline in routers - use `models/schemas.py`
- ❌ Don't use plain bcrypt - use `bcrypt_sha256` from `auth.py`
- ❌ Don't create endpoints outside `/api/v1` prefix
- ❌ Don't return HTML - this is a pure JSON API

### File Structure
```
server/
├── app/
│   ├── main.py              # FastAPI app initialization
│   ├── db.py                # Database session management
│   ├── models/              # SQLAlchemy models
│   │   ├── models.py        # Database models
│   │   └── schemas.py       # Pydantic request/response schemas
│   ├── routers/             # API endpoints
│   │   └── api.py           # Main API router
│   ├── services/            # Business logic
│   │   ├── cert_manager.py  # Certificate operations
│   │   ├── config_builder.py # Config generation
│   │   └── ip_allocator.py  # IP allocation
│   └── core/                # Core functionality
│       ├── auth.py          # Authentication
│       └── scheduler.py     # Background jobs
├── alembic/                 # Database migrations
├── tests/                   # Test suite
└── requirements.txt         # Python dependencies
```

## Adding New Features

### Adding a New API Endpoint
1. Add Pydantic schemas in `app/models/schemas.py`
2. Add route handler in `app/routers/api.py` under `/api/v1` prefix
3. Use proper status codes and error handling
4. Add authentication dependency if needed
5. Write tests in `tests/`

### Adding a New Database Model
1. Create model in `app/models/models.py` with proper SQLAlchemy async support
2. Create Alembic migration: `alembic revision --autogenerate -m "add model"`
3. Apply migration: `alembic upgrade head`
4. Add corresponding Pydantic schemas in `app/models/schemas.py`
5. Update API endpoints as needed

### Adding Background Tasks
1. Add task function in appropriate service module
2. Register with scheduler in `app/core/scheduler.py`
3. Ensure proper error handling and logging

## Database Support
The system supports multiple database backends:
- **SQLite** (default): Good for development and small deployments
- **PostgreSQL** (recommended for production): Use `postgresql+asyncpg://...`
- **MySQL**: Use `mysql+aiomysql://...`

Configure via `DB_URL` environment variable.
