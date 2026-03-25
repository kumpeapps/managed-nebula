# Managed Nebula - Copilot Instructions

## Critical Rules

**NEVER CREATE .MD FILES TO DOCUMENT FIXES OR UPDATES**
- Do NOT create implementation summaries, fix summaries, or progress documentation files
- Do NOT create temporary .md files like `IMPLEMENTATION_SUMMARY.md`, `FIX_SUMMARY.md`, etc.
- If documentation is needed, update the appropriate existing README.md only
- Focus on code changes, not documentation artifacts

## Architecture Overview

This is a **Nebula mesh VPN management platform** with three main components:

- **Server** (`server/`): FastAPI REST API backend with SQLAlchemy ORM, Alembic migrations, and comprehensive JSON endpoints
- **Frontend** (`frontend/`): Angular 17 SPA for web-based management (connects to server REST API)
- **Client** (`client/`): Lightweight Python agent that polls the server for Nebula configs and manages the local Nebula daemon

The server is a pure JSON API backend that orchestrates CA/certificate lifecycle, IP allocation, firewall rules, and group membership. The Angular frontend provides the web UI, and client agents authenticate with tokens to download configs.

## Git Workflow and Branching Strategy

**CRITICAL: Always follow this branching strategy when working on issues:**

### Branch Creation
1. **Always create feature branches from `dev` branch** (not `main`)
2. If `dev` branch doesn't exist:
   - First create `dev` branch from `main`: `git checkout -b dev main`
   - Then create your feature branch from `dev`: `git checkout -b feature/your-branch dev`
3. Feature branch naming conventions:
   - **Format**: `<type>/<service>-<issue-number>` where:
     - `<type>`: `feature`, `bugfix`, `hotfix`, `docs`, `refactor`, etc.
     - `<service>`: `server`, `frontend`, `client`, or `all` (for changes affecting multiple services)
     - `<issue-number>`: GitHub issue number
   - **Examples**:
     - `feature/server-5` - Feature for server (issue #5)
     - `bugfix/frontend-12` - Bug fix for frontend (issue #12)
     - `feature/client-8` - Feature for client agent (issue #8)
     - `hotfix/all-23` - Hotfix affecting all services (issue #23)
   - Branch names created by Copilot should follow this convention

### Pull Request Target
- **All pull requests should target the `dev` branch** (not `main`)
- **PR title format**: `[<branch-name>] Description`
  - Example: `[feature/server-5] Add user authentication endpoint`
  - Example: `[bugfix/frontend-12] Fix login form validation`
- Only merge from `dev` to `main` for releases
- Use pull request templates from `.github/PULL_REQUEST_TEMPLATE/`

### Workflow Summary
```
main (production)
  ↑
  └── dev (development/integration)
        ↑
        ├── feature/server-5
        ├── bugfix/frontend-12
        └── feature/client-8
```

### Commit Message Format
**CRITICAL: All commits must follow this format:**

```
[<branch-name>] <Short description>

Resolves #<issue-number>

<Detailed description of changes>
- Bullet point 1
- Bullet point 2
...
```

**Examples:**
```
[feature/server-5] Add user authentication endpoint

Resolves #5

- Implement JWT token-based authentication
- Add login/logout endpoints
- Create auth middleware for protected routes
```

```
[bugfix/frontend-12] Fix login form validation

Resolves #12

- Add email format validation
- Fix password minimum length check
- Update error messages for clarity
```

**Key rules:**
- Start with `[<branch-name>]` prefix
- Include `Resolves #<issue-number>` in commit body
- Use present tense ("Add" not "Added")
- Be descriptive but concise

### When Assigned an Issue
1. Check if `dev` branch exists: `git branch -r | grep origin/dev`
2. If `dev` doesn't exist: `git checkout -b dev origin/main && git push -u origin dev`
3. **Determine the primary service affected** by analyzing the issue:
   - Changes primarily in `server/` → use `server`
   - Changes primarily in `frontend/` → use `frontend`
   - Changes primarily in `client/` → use `client`
   - Changes across multiple services → use `all`
4. Create feature branch using format `<type>/<service>-<issue-number>`:
   - Example: `git checkout -b feature/server-5 origin/dev` (for issue #5 affecting server)
5. Make changes and commit with proper format (see Commit Message Format above)
6. **Rebase branch against `dev` before requesting review**: `git fetch origin dev && git rebase origin/dev`
7. Create PR with title format `[<branch-name>] Description` targeting `dev` branch

## Database & Migrations

- **Database-agnostic** via SQLAlchemy async: supports SQLite (default), PostgreSQL, MySQL
  - Configure via `DB_URL` env var (e.g., `sqlite+aiosqlite:///./app.db`, `postgresql+asyncpg://...`)
- **Alembic** for schema migrations in `server/alembic/versions/`
- **CRITICAL: All migrations MUST be idempotent**
  - Always check if columns/tables/indexes exist before adding them
  - Always check if columns/tables/indexes exist before dropping them
  - Use SQLAlchemy inspector to check schema state
  - Example pattern:
    ```python
    def upgrade() -> None:
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        
        # Check if column exists before adding
        columns = {col['name'] for col in inspector.get_columns('table_name')}
        if 'new_column' not in columns:
            op.add_column('table_name', sa.Column('new_column', sa.String(50)))
    
    def downgrade() -> None:
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        
        # Check if column exists before dropping
        columns = {col['name'] for col in inspector.get_columns('table_name')}
        if 'new_column' in columns:
            op.drop_column('table_name', 'new_column')
    ```
  - This ensures migrations can be run multiple times safely without errors
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

Three distinct auth mechanisms:

1. **Angular Frontend**: Session-based (SessionMiddleware), auth via `core/auth.py::get_current_user()`
   - Login via `POST /api/v1/auth/login` (JSON), logout via `POST /api/v1/auth/logout`
   - Current user via `GET /api/v1/auth/me`
   - Role-based: `require_admin()` dependency for privileged routes
   - Session stored in cookies, automatically sent by browser

2. **API Keys** (Programmatic Access): Token-based via Bearer authentication
   - Authenticate via `Authorization: Bearer mnapi_<64-hex-chars>` header
   - Created/managed via `/api/v1/api-keys` endpoints
   - Supports fine-grained scope restrictions:
     - `allowed_group_ids`: Limit to specific groups
     - `allowed_ip_pool_ids`: Limit to specific IP pools
     - `restrict_to_created_clients`: Only access clients created by this key
   - Regeneration maintains permissions: `POST /api/v1/api-keys/{id}/regenerate`
   - Authorization tracked in `request.state.api_key_id` and `request.state.api_key`
   - Clients track creating key via `created_by_api_key_id` column

3. **Client API**: Token-based at `/api/v1/client/config`
   - Validates `ClientToken` from request body (not headers)
   - Tokens created per-client in database, checked for `is_active=True`

## Frontend UI (`frontend/src/app/components/`)

**Angular 17 SPA with key management interfaces:**

- **Profile Component** (`profile.component.ts`): User profile and API key management
  - **Profile Settings Tab**: Email/password updates
  - **API Keys Tab**: Complete API key lifecycle management
    - Create keys with name, expiration, and scope restrictions (groups, IP pools, client restriction)
    - Edit existing key permissions (name, groups, IP pools, restrictions)
    - Regenerate keys (creates new key with same permissions, revokes old)
    - Revoke keys (immediate deactivation)
    - View key details: preview, status, creation date, expiration, last used, usage count
    - Scope display: Shows group/IP pool restrictions and "created clients only" flag
  - Route: `/profile`

- **Settings Component** (`settings.component.ts`): Admin-only system settings
  - Version information (frontend, server, Nebula)
  - Nebula configuration (punchy, lighthouse settings)
  - Version cache management
  - GitHub webhook secret configuration
  - Route: `/settings` (admin only)

- **Navbar Component** (`navbar.component.ts`): Main navigation
  - Conditional visibility based on authentication and role
  - Profile link available to all authenticated users
  - Settings link visible to admins only

## GitHub Secret Scanning Integration

**Automatic token revocation for leaked secrets via GitHub Secret Scanning Partner Program:**

- **Metadata Endpoint** (`GET /.well-known/secret-scanning.json`): Public endpoint that returns regex patterns
  - Client tokens: `<prefix>[a-z0-9]{32}` (prefix configurable, default `mnebula_`)
  - API keys: `mnapi_[a-f0-9]{64}` (fixed format, 70 chars total)
  
- **Verify Endpoint** (`POST /api/v1/github/secret-scanning/verify`): Checks if tokens are valid
  - Requires GitHub webhook signature verification (HMAC SHA-256)
  - Accepts both client tokens and API keys (determined by `mnapi_` prefix)
  - Client tokens: Direct database lookup by token value
  - API keys: Iterates through active keys, verifies against hash using `passlib`
  - Returns token details: label, URL, is_active status
  - Logs all verification attempts to `GitHubSecretScanningLog`
  
- **Revoke Endpoint** (`POST /api/v1/github/secret-scanning/revoke`): Auto-deactivates leaked tokens
  - Requires GitHub webhook signature verification
  - Client tokens: Sets `is_active=False` in `ClientToken` table
  - API keys: Sets `is_active=False` in `UserAPIKey` table
  - Logs revocations with warning level (includes client_id or key_id)
  - Returns count of successfully revoked tokens
  
- **Implementation Notes**:
  - Both endpoints use `get_token_preview()` for safe logging (first 12 chars)
  - API key verification requires iterating all active keys (they're bcrypt hashed)
  - Signature verification uses constant-time comparison (`hmac.compare_digest`)
  - Webhook secret configurable via `/api/v1/settings/github-webhook-secret`

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

## API Key Authorization Service (`services/api_key_auth.py`)

When API keys have scope restrictions, use the authorization service to enforce permissions:

**Key Functions:**
- `check_client_access(session, api_key, client, operation)` - Returns bool for client access
- `check_group_access(api_key, group)` - Returns bool for group access
- `check_ip_pool_access(api_key, ip_pool)` - Returns bool for IP pool access
- `require_client_access()` - Raises HTTPException(403) if access denied
- `filter_clients_by_scope()` - Filters client list based on key permissions

**When to Use:**
- In API endpoints that list/access clients when authenticated via API key
- Before modifying resources that have scope restrictions
- Use `request.state.api_key` to get the authenticated API key object

**Example Pattern:**
```python
@router.get("/clients")
async def list_clients(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    # Get all clients user can access
    result = await session.execute(select(Client))
    clients = result.scalars().all()
    
    # If authenticated via API key, filter by scope
    if hasattr(request.state, "api_key") and request.state.api_key:
        from ..services.api_key_auth import filter_clients_by_scope
        clients = await filter_clients_by_scope(session, request.state.api_key, clients)
    
    return clients
```

**Authorization Checks:**
- Group restrictions: Client must be in at least one allowed group
- IP pool restrictions: Client must have IP in at least one allowed pool
- Created clients only: Client's `created_by_api_key_id` must match key ID
- Empty restrictions = no limitations (full user access)

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
- When API keys are used for authentication, check `request.state.api_key` for scope restrictions
- Always use `filter_clients_by_scope()` when listing clients with API key auth to enforce restrictions
- Client creation should store `created_by_api_key_id` when authenticated via API key for proper scope tracking
- API key regeneration (`POST /api-keys/{id}/regenerate`) maintains scope restrictions and parent_key_id for client access tracking
- Frontend API key forms handle scope restrictions via multi-select dropdowns for groups/IP pools
- GitHub secret scanning works for both client tokens and API keys - ensure webhook secret is configured
