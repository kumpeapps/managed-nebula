# Managed Nebula - Copilot Instructions

## Architecture Overview

This is a **Nebula mesh VPN management platform** with three main components:

- **Server** (`server/`): FastAPI REST API backend with SQLAlchemy ORM, Alembic migrations, and comprehensive JSON endpoints
- **Frontend** (`frontend/`): Angular 17 SPA for web-based management (connects to server REST API)
- **Client** (`client/`): Lightweight Python agent that polls the server for Nebula configs and manages the local Nebula daemon

The server is a pure JSON API backend that orchestrates CA/certificate lifecycle, IP allocation, firewall rules, and group membership. The Angular frontend provides the web UI, and client agents authenticate with tokens to download configs.

## Database & Migrations

- **Database-agnostic** via SQLAlchemy async: supports SQLite (default), PostgreSQL, MySQL
  - Configure via `DB_URL` env var (e.g., `sqlite+aiosqlite:///./app.db`, `postgresql+asyncpg://...`)
- **Alembic** for schema migrations in `server/alembic/versions/`
- **Runtime column additions** happen in `main.py::migrate_columns()` using SQLAlchemy introspection - idempotent DDL for adding columns without full migrations
- Run migrations: `docker exec -it nebula-server bash -lc "alembic upgrade head"` (inside container)

## Certificate Management (Critical Pattern)

Uses `nebula-cert` CLI via subprocess calls in `services/cert_manager.py`:

- **CA Rotation**: Configurable validity (default 18mo), rotation at 12mo, 3mo overlap window
  - Scheduler (`core/scheduler.py`) runs daily checks at 3am UTC for rotation
  - Previous CAs marked `is_previous=True, include_in_config=True` during overlap
- **Client Certificates**: 6-month validity, rotated 3 months before expiry
  - Certificate reuse: only reissue if IP/CIDR/groups changed (see `issue_or_rotate_client_cert()`)
  - Public key provided by client via `/api/v1/client/config` POST
- **Key Files**: Clients generate keypairs locally (`host.key`, `host.pub`) with `nebula-cert keygen`

## API Authentication Patterns

Two distinct auth mechanisms:

1. **Angular Frontend**: Session-based (SessionMiddleware), auth via `core/auth.py::get_current_user()`
   - Login via `POST /api/v1/auth/login` (JSON), logout via `POST /api/v1/auth/logout`
   - Current user via `GET /api/v1/auth/me`
   - Role-based: `require_admin()` dependency for privileged routes
   - Session stored in cookies, automatically sent by browser

2. **Client API**: Token-based at `/api/v1/client/config`
   - Validates `ClientToken` from request body (not headers)
   - Tokens created per-client in database, checked for `is_active=True`

## REST API Architecture (`server/app/routers/api.py`)

**All endpoints under `/api/v1` prefix, pure JSON responses:**

### Resources with Full CRUD:
- **Clients** (`/clients`): GET list, GET by ID, PUT update, DELETE
  - Returns `ClientResponse` with eager-loaded groups and tokens (admin only)
  - PUT updates `config_last_changed_at` when groups/firewall rules change
- **Groups** (`/groups`): GET list, GET by ID, POST create, PUT update, DELETE
  - Returns `GroupResponse` with `client_count`
  - Delete returns 409 if clients still use group
- **Firewall Rules** (`/firewall-rules`): GET list, GET by ID, POST create, PUT update, DELETE
  - Returns `FirewallRuleResponse` with `client_count`
  - YAML validation via `yaml.safe_load()` on create/update
  - Delete returns 409 if clients still reference rule
- **IP Pools** (`/ip-pools`): GET list, GET by ID, POST create, PUT update, DELETE
  - Returns `IPPoolResponse` with `allocated_count`
  - CIDR validation via `ipaddress.ip_network()`
  - Cannot change CIDR if IPs allocated, delete returns 409 if allocations exist
- **CA Management** (`/ca`): GET list, POST create, POST import, DELETE
  - Returns `CAResponse` with status: current/previous/expired/inactive
  - Create via `CertManager.create_new_ca()`, marks previous CAs as `is_previous=True`
  - Delete returns 409 if attempting to delete active CA
- **Users** (`/users`, admin-only): GET list, GET by ID, POST create, PUT update, DELETE
  - Returns `UserResponse` with role information
  - Password hashing via `auth.hash_password()` using bcrypt_sha256
  - Delete prevents self-deletion with 409

### Pydantic Schemas (`server/app/models/schemas.py`):
All request/response models organized by resource:
- `ClientResponse`, `ClientUpdate`, `GroupRef`
- `GroupCreate`, `GroupUpdate`, `GroupResponse`
- `FirewallRuleCreate`, `FirewallRuleUpdate`, `FirewallRuleResponse`
- `IPPoolCreate`, `IPPoolUpdate`, `IPPoolResponse`
- `CACreate`, `CAImport`, `CAResponse`
- `UserCreate`, `UserUpdate`, `UserResponse`, `RoleRef`
- `ClientConfigRequest` (for client agent)

### Key API Patterns:
- All endpoints return proper HTTP status codes (200, 400, 401, 403, 404, 409, 503)
- Conflict detection (409) for delete operations when resources are in use
- Validation errors (400) for invalid CIDR, YAML, etc.
- Admin-only endpoints use `Depends(require_admin)`
- Eager-loading with `selectinload()` to avoid async lazy-load issues

## Configuration Building (`services/config_builder.py`)

- Generates Nebula YAML configs dynamically per client
- **Inline PEM handling**: Uses custom `LiteralStr` class + YAML representer for block scalar (`|`) style
- Config references local paths: `/var/lib/nebula/host.key`, `/etc/nebula/host.crt`, `/etc/nebula/ca.crt`
- Static host map, lighthouse IPs, firewall rules all templated from database state
- Groups converted to Nebula groups in config

## IP Allocation (`services/ip_allocator.py`)

- IP pools (`IPPool`) define CIDR ranges
- `ensure_default_pool()` creates default pool if none exists
- `allocate_ip_from_pool()` finds next available IP, avoiding conflicts with `IPAssignment` table
- Clients require IP assignment before fetching config (409 if missing)

## Client Agent Workflow (`client/agent.py`)

1. Generate keypair if not exists (`nebula-cert keygen`)
2. POST `{token, public_key}` to `/api/v1/client/config`
3. Receive JSON with `config` (YAML string), `client_cert_pem`, `ca_chain_pems`
4. Write files to `/etc/nebula/config.yml`, `/etc/nebula/host.crt`, `/etc/nebula/ca.crt`
5. Run `nebula` daemon (via `entrypoint.sh`)
6. Poll server every `POLL_INTERVAL_HOURS` (default 24) for config updates

## Testing

- Tests in `server/tests/` use `TestClient` from FastAPI
- **Skip tests requiring `nebula-cert`** with `@pytest.mark.skipif(shutil.which("nebula-cert") is None)`
- Test pattern: create admin user → create CA → create pool → create client → fetch config
- No mocking of database - uses in-memory SQLite or test database

## Development Commands

```bash
# Build images
docker build -t managed-nebula-server ./server
docker build -t managed-nebula-client ./client

# Run server (standalone)
docker run --rm -it -p 8080:8080 \
  -e DB_URL=sqlite+aiosqlite:///./app.db \
  -e SECRET_KEY=change-me \
  --name nebula-server managed-nebula-server

# Run with docker-compose
docker-compose up -d server

# Run tests (inside container or with local Python)
pytest server/tests/

# Alembic migrations
alembic revision -m "description"
alembic upgrade head
```

## Key Conventions

- **Async everywhere**: All database access via `AsyncSession`, `async def` route handlers
- **Eager loading**: Use `selectinload()` for relationships to avoid lazy-load errors in async (e.g., `Client.groups`)
- **DateTime**: Always `datetime.utcnow()`, stored as UTC in database
- **Password hashing**: Uses `bcrypt_sha256` (not plain bcrypt) to avoid 72-byte truncation
- **Pydantic models**: All request/response schemas in `models/schemas.py`, not inline in routers
- **Firewall rules**: Stored as YAML/JSON strings in `FirewallRule.rule` column, parsed when building config
- **Many-to-many**: Association tables (`client_groups`, `client_firewall_rules`) use SQLAlchemy `Table` + `relationship(secondary=...)`

## Project-Specific Patterns

- **Lighthouse detection**: `Client.is_lighthouse` flag, `public_ip` required for lighthouses
- **Config change tracking**: `config_last_changed_at` timestamp updated when IP/groups/rules change
- **Blocked clients**: `is_blocked` flag prevents config generation (403 error in client config endpoint)
- **Ownership**: `owner_user_id` FK for multi-tenant future use (not enforced currently)
- **API-first design**: No HTML templates or server-side rendering - Angular handles all UI

## Common Pitfalls

- Don't use `session.query()` - use `session.execute(select(...))` for async compatibility
- Don't forget `await session.commit()` after writes
- Inline PEM certs must use `LiteralStr` wrapper for proper YAML formatting
- Client API returns 503 if no active CA exists
- Tests assume `nebula-cert` binary is in PATH (Docker images include it)
- Always use Pydantic schemas from `models/schemas.py` - don't define inline BaseModel classes in routers
- Frontend auth uses session cookies - ensure CORS/CSRF properly configured for production
