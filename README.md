<div align="center">

<img src="logo/social-preview.png" alt="Managed Nebula Logo" width="200" height="200">

# Managed Nebula

### Enterprise-Grade Mesh VPN Management Platform

*Simplify your Nebula mesh VPN deployment with centralized certificate management, automatic rotation, and an intuitive web interface.*

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](docker-compose.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Configuration](#-configuration) • [API Documentation](#-api-documentation)

</div>

---

## 📋 Overview

**Managed Nebula** is a comprehensive management platform for [Nebula](https://github.com/slackhq/nebula) mesh VPN networks. It provides centralized control over certificate authorities, client configurations, IP allocation, firewall rules, and group-based access control through both a web GUI and REST API.

### What is Nebula?

Nebula is a scalable overlay networking tool focusing on performance, simplicity, and security. Managed Nebula takes the complexity out of operating a Nebula network at scale.

## ✨ Features

### 🔐 **Certificate Authority Management**
- Automated CA creation and rotation (18-month validity, 12-month rotation, 3-month overlap)
- Multiple CA support with seamless transitions
- CA import for existing Nebula deployments
- Certificate lifecycle tracking and expiry monitoring
- Automatic client certificate renewal (6-month validity, 3-month renewal window)
- Certificate reuse optimization (only reissue when IP/groups change)
- Background scheduler for automated rotation checks

### 🖥️ **Web Management Interface (Angular)**
- Modern Angular 17 single-page application
- Intuitive dashboard for network overview
- Client management with real-time status
- Hierarchical group management with permissions
- Structured firewall rulesets (not just YAML strings)
- IP pool and IP group management
- User and user group administration
- Global settings configuration
- Role-based access control (admin/standard users)

### 🤖 **Automated Client Provisioning**
- Self-service token-based authentication
- **Standardized token format** with configurable prefix for GitHub Secret Scanning
- **Token re-issuance** for rotation and security incidents
- Automatic keypair generation on client side
- Dynamic configuration delivery via REST API
- Periodic polling for certificate rotation and config updates
- **Process monitoring & resilient recovery** (NEW!)
  - Automatic crash detection and restart with exponential backoff
  - Config fetch timeout and retry with caching fallback
  - Metrics tracking (crash/restart/failure counts)
  - Coordinated recovery after restarts
- Docker Compose file generation for easy deployment
- Client blocking/unblocking support
- Granular per-client user permissions

### 🌐 **Flexible IP Management**
- Multiple IP pool support (CIDR-based)
- IP groups within pools for logical segmentation
- Automatic IP allocation from pools
- Manual IP assignment override via UI
- **Change client IP address, pool, or group** directly from client detail page
- Pool-aware assignment tracking
- **Pool-specific lighthouses** - Clients only connect to lighthouses in their IP pool
- Lighthouse configuration with static hosts

### 🔥 **Advanced Firewall Management**
- **Structured firewall rules** with dedicated fields (direction, port, proto, host, CIDR, groups)
- **Firewall rulesets** - named collections of rules for easy reuse
- Group-based access control within rules
- Per-client ruleset assignment
- Inbound/outbound traffic control
- Support for local CIDR, CA name/SHA filtering

### 💾 **Database Flexibility**
- **SQLite** (default) - Perfect for small deployments, no external DB needed
- **PostgreSQL** - Recommended for production with asyncpg driver
- **MySQL** - Alternative production option with aiomysql driver
- Database-agnostic design via SQLAlchemy async engine
- Alembic migrations for schema versioning
- Auto-sync mode for development (optional column additions)

### 👥 **Advanced User & Permission Management**
- **Comprehensive RBAC** - Granular, resource/action permissions (e.g. `clients:read`, `ip_pools:update`)
- **User Groups** - Users inherit all permissions from their groups
- **Admin Groups** - Any group with `is_admin` automatically has all permissions
- **System Seed** - Initial migration seeds default permissions & two groups (Administrators, Users)
- **Permission Management UI** - Assign/revoke group permissions in a dedicated page
- **Client-Level Grants** - Fine-grained per-client overrides for visibility & config download
- **Admin Lockout Protection** - Admin role + admin group bypass ensures continuous access

## 🆕 Recent Updates

### 🔄 Process Monitoring & Resilient Recovery (NEW!)
- 🛡️ **Automatic Crash Detection** - Monitors Nebula process with configurable intervals (default: 10s)
- 🔄 **Intelligent Restart Logic** - Exponential backoff (1s → 2s → 4s, max 30s) with max 5 attempts
- 📊 **Comprehensive Metrics** - Tracks crashes, restarts, disconnects, and config fetch failures
- ⏱️ **Timeout & Retry** - Config fetches timeout after 30s with exponential backoff retry (up to 5 attempts)
- 💾 **Config Caching** - Falls back to cached config when server unavailable
- 🔍 **Health Checks** - Periodic connectivity verification (default: 60s intervals)
- 🔧 **Config Validation** - Validates syntax before restart to prevent boot loops
- 🚨 **Administrator Alerts** - Stops auto-restart after max failures and alerts for intervention
- 📚 **Documentation**: See [MONITORING_AND_RECOVERY.md](MONITORING_AND_RECOVERY.md) for full details

**Supported Clients:**
- ✅ **Docker/Linux Client** - Full implementation with `--monitor` mode
- ✅ **Windows Client** - Full implementation with `--monitor` mode  
- 🚧 **macOS Client** - Basic monitoring via PollingService (enhanced features pending)

### 🔒 Security & Token Management (NEW!)
- 🔐 **Standardized Token Format** - Configurable prefix (default: `mnebula_`) + 32 secure random characters
- 🔐 **Token Re-issuance** - Admins can rotate client tokens with a single API call
- 🔐 **GitHub Secret Scanning Integration** - Automatic detection of leaked tokens in public repositories
- 🔐 **Audit Trail** - All token operations and GitHub scanning events logged
- 🔐 **Backward Compatibility** - Legacy tokens without prefix continue to work
- 📚 **Documentation**: See [GITHUB_SECRET_SCANNING.md](GITHUB_SECRET_SCANNING.md) for setup guide

### IP Management Enhancements
- ✨ **Change client IP configuration** directly from the UI
- ✨ **Reassign clients** to different IP pools or IP groups
- ✨ **Pool-specific lighthouses** - Clients only see lighthouses in their own pool for better network segmentation

### Database & Reliability
- 🔧 **Fixed foreign key CASCADE behaviors** across all models for proper MySQL/PostgreSQL support
- 🔧 **Improved client deletion** with proper cascade handling for tokens, certificates, and IP assignments
- 🔧 **Enhanced error handling** in certificate management and client creation

### Container Distribution
- 📦 **Pre-built images available** at `ghcr.io/kumpeapps/managed-nebula/{server,frontend,client}:latest`
- 📦 **Automatic START_NEBULA=true** in generated docker-compose files

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) PostgreSQL or MySQL for production deployments
- 10 minutes of your time ☕

### 1️⃣ Clone and Start

```bash
# Clone the repository
git clone https://github.com/kumpeapps/managed-nebula.git
cd managed-nebula

# Start all services (server + frontend) using pre-built images
docker-compose up -d

# Or start just the server (API only)
docker-compose up -d server
```

### Alternative Compose Examples

Additional deployment examples are provided:

```bash
# Production-like: Frontend terminates TLS and proxies /api to server
DOMAIN=nebula.example.com \
  docker compose -f docker-compose-server.yml up -d

# Standalone client example (requires CLIENT_TOKEN and SERVER_URL)
CLIENT_TOKEN=your-token SERVER_URL=https://your-domain \
  docker compose -f docker-compose-client.yml up -d
```

About `docker-compose-server.yml`:
- The Angular frontend container serves the SPA and terminates HTTPS on port 443
- It proxies all `/api/*` requests to the FastAPI server service on the internal network
- If you mount real certs at `./certs` on the host, set their names via `SSL_CERT_NAME` and `SSL_KEY_NAME`
- If no certs are mounted, the container will generate a self-signed certificate for `DOMAIN` (default: `localhost`)

Environment variables for TLS:
- `DOMAIN` (default `localhost`) – Common Name used for self-signed fallback and redirects
- `SSL_CERT_NAME` (default `tls.crt`) – Filename of the certificate inside `/etc/nginx/certs`
- `SSL_KEY_NAME` (default `tls.key`) – Filename of the private key inside `/etc/nginx/certs`

Optional host certificate mount:
```yaml
services:
  frontend:
    volumes:
      - ./certs:/etc/nginx/certs:ro
```

The `docker-compose-client.yml` file demonstrates a single Nebula client container using host networking and required TUN capabilities.

**Note:** By default, `docker-compose.yml` builds images locally. To use pre-built images from GitHub Container Registry, update the `image:` lines in `docker-compose.yml`:
```yaml
services:
  server:
    image: ghcr.io/kumpeapps/managed-nebula/server:latest
  frontend:
    image: ghcr.io/kumpeapps/managed-nebula/frontend:latest
```

When using `docker-compose-server.yml`, the frontend is served at `https://<DOMAIN>` and the API is available under `https://<DOMAIN>/api/`.

### 2️⃣ Initial Setup

The server will automatically bootstrap an admin account on first startup if you provide environment variables:

```bash
docker-compose up -d server
# Admin credentials from docker-compose.yml: admin@example.com / admin
```

Or set custom credentials:
```bash
docker run -d \
  -e ADMIN_EMAIL=you@example.com \
  -e ADMIN_PASSWORD=your-secure-password \
  -p 8080:8080 \
  managed-nebula-server
```

**Alternative: Create Admin Manually**

If automatic bootstrap doesn't work (e.g., with MySQL), create an admin user manually:
```bash
# Easy way - using helper script
./scripts/create-admin.sh admin@example.com

# Using docker-compose
docker compose exec server python manage.py create-admin admin@example.com

# Using docker directly
docker exec -it managed-nebula-server python manage.py create-admin admin@example.com

# Non-interactive (useful for scripts)
docker exec managed-nebula-server python manage.py create-admin admin@example.com MySecurePassword1234

```

Open your browser to **http://localhost** (frontend) or **https://localhost/api/docs** (API docs) and log in with your admin credentials, then:

1. Generate your first Certificate Authority (CA) in the CA management page
2. Create an IP pool (e.g., `10.100.0.0/16`) in IP Pools
3. (Optional) Create firewall rulesets for common policies
4. Add your first client and generate a token

### 3️⃣ Deploy a Client

```bash
# Pull the latest client image from GitHub Container Registry
docker pull ghcr.io/kumpeapps/managed-nebula/client:latest

# Run with your client token
docker run -d \
  --name nebula-client-001 \
  --cap-add=NET_ADMIN \
  --device /dev/net/tun \
  -e CLIENT_TOKEN=<your-token-here> \
  -e SERVER_URL=http://your-server:8080 \
  ghcr.io/kumpeapps/managed-nebula/client:latest
```

**Alternative: Download docker-compose.yml from the UI**

The web interface provides a "Download Docker Compose" button on each client's detail page, which generates a pre-configured `docker-compose.yml` with the client token already embedded.

🎉 **That's it!** Your client will automatically:
- Generate a keypair
- Fetch its configuration and certificates
- Join the Nebula mesh network
- Poll for updates every 24 hours

### 🍎 macOS Native Client

For macOS users who need native TUN interface support (Docker networking limitations on macOS), a native menu bar application is available.

**📥 Installation (Recommended)**

Download the latest pre-built installer from the [Releases page](https://github.com/kumpeapps/managed-nebula/releases):

1. Download `ManagedNebula-Installer.pkg` from the latest release
2. Double-click to run the installer
3. Launch `ManagedNebula` from Applications or Spotlight
4. Enter your server URL and client token in Preferences

**🔨 Building from Source (Advanced)**

If you prefer to build manually:

```bash
# Clone and install
cd macos_client
./install.sh

# Or build manually
make build
sudo make install
```

**Features:**
- **Native Nebula integration** - Direct TUN interface on macOS
- **Menu bar application** - System tray icon with connection status
- **Secure storage** - Client token stored in macOS Keychain
- **Auto-updates** - Automatic configuration polling
- **Easy setup** - Simple preferences UI

See [`macos_client/README.md`](macos_client/README.md) and [`macos_client/QUICKSTART.md`](macos_client/QUICKSTART.md) for detailed documentation.

## 🏗️ Architecture

```
              ┌─────────────────────────────────┐
              │    Angular 17 Frontend (SPA)    │
              │  • Dashboard  • Clients         │
              │  • Groups     • Firewall Rules  │
              │  • IP Pools   • Users & CA      │
              └────────────┬────────────────────┘
                           │ HTTP/JSON API
                           │ (Session Auth)
              ┌────────────▼────────────────────┐
              │   Managed Nebula Server (API)   │
              │  ┌───────────────────────────┐  │
              │  │   FastAPI REST Endpoints  │  │
              │  │   • /api/v1/clients       │  │
              │  │   • /api/v1/groups        │  │
              │  │   • /api/v1/firewall-*    │  │
              │  │   • /api/v1/client/config │  │
              │  └───────────┬───────────────┘  │
              │              │                   │
              │  ┌───────────▼───────────────┐  │
              │  │  Background Scheduler     │  │
              │  │  • CA Rotation (Daily)    │  │
              │  │  • Cert Renewal Check     │  │
              │  └───────────────────────────┘  │
              │              │                   │
              │  ┌───────────▼───────────────┐  │
              │  │   SQLAlchemy ORM (Async)  │  │
              │  └───────────┬───────────────┘  │
              │              │                   │
              │  ┌───────────▼───────────────┐  │
              │  │  Database (Multi-engine)  │  │
              │  │  SQLite/PostgreSQL/MySQL  │  │
              │  └───────────────────────────┘  │
              └────────────┬────────────────────┘
                           │ Token Auth
         ┌─────────────────┴─────────────────┐
         │                                    │
    ┌────▼──────┐                      ┌─────▼──────┐
    │  Client 1 │                      │  Client 2  │
    │ • Polls   │  ◄────Mesh VPN────►  │  • Polls   │
    │ • Rotates │    (Nebula UDP)      │  • Rotates │
    └───────────┘                      └────────────┘
```

### Component Breakdown

#### 🖥️ **Server** (`server/`)
- **Framework**: FastAPI with async/await
- **ORM**: SQLAlchemy (async) with Alembic migrations
- **Authentication**: Session-based (web UI) + Token-based (client API)
- **API**: Pure JSON REST API - no server-side rendering
- **Scheduler**: APScheduler for background tasks (CA rotation, cert renewal)
- **Certificate Management**: `nebula-cert` CLI integration
- **Password Hashing**: bcrypt_sha256 (avoids 72-byte truncation)
- **RBAC Enforcement**: `require_permission(resource, action)` dependency replaces legacy admin checks
- **Default Permissions**: 40+ seeded covering clients, groups, firewall_rules, ip_pools, ip_groups, ca, users, user_groups, settings, lighthouse, dashboard

### 🔐 RBAC Permission System

Managed Nebula uses a resource/action permission matrix instead of simple roles.

| Resource | Common Actions | Notes |
|----------|----------------|-------|
| clients | read, create, update, delete, download | Download returns YAML config & certs |
| groups | read, create, update, delete | Nebula logical grouping |
| firewall_rules / firewall_rulesets | read, create, update, delete | Structured rule objects, not raw YAML |
| ip_pools | read, create, update, delete | CIDR-based allocation domains |
| ip_groups | read, create, update, delete | Sub-segmentation within pools |
| ca | read, create, delete, download | CA rotation & chain retrieval |
| users | read, create, update, delete | User admin endpoints |
| user_groups | read, create, update, delete, manage_members, manage_permissions | Group lifecycle & permission binding |
| settings | read, update, docker_compose | Global settings + compose template feature |
| lighthouse | read, update | Lighthouse public IP/port control |
| dashboard | read | Summary metrics & status |

Permission naming convention: `<resource>:<action>` (e.g. `firewall_rules:create`). Extended actions use underscores (`manage_permissions`).

Enforcement pattern:
```python
@router.get("/clients", dependencies=[Depends(require_permission("clients", "read"))])
async def list_clients(...):
  ...
```

Admin access paths:
- Belonging to a group with `is_admin=True` grants all permissions
- Admin role fallback in `User.has_permission()` prevents accidental lockout

Permission management endpoints:
- `GET /api/v1/permissions` – Enumerate all permissions
- `GET /api/v1/user-groups/{id}/permissions` – List a group's permissions
- `POST /api/v1/user-groups/{id}/permissions` – Grant permission (requires `user_groups:manage_permissions`)
- `DELETE /api/v1/user-groups/{id}/permissions/{perm_id}` – Revoke permission (requires `user_groups:manage_permissions`)

UI workflow:
1. Create a user group
2. Grant permissions via Permissions page
3. Add users to the group for inheritance
4. Optionally grant client-specific permissions for narrower access

Admin recommendations:
- Keep at least one non-deletable admin group (default: Administrators)
- Periodically audit group memberships and granted permissions
- Use client-level grants sparingly—prefer group-based policies

#### 🎨 **Frontend** (`frontend/`)
- **Framework**: Angular 17 SPA
- **UI Library**: Angular Material
- **State Management**: RxJS + Services
- **Build Tool**: Angular CLI
- **Deployment**: Nginx static hosting in Docker

#### 📱 **Client** (`client/`)
- **Runtime**: Lightweight Python agent (Docker-based)
- **Dependencies**: `httpx` for API calls, `nebula-cert` for keypair generation
- **Lifecycle**: Poll server → Fetch config → Update certificates → Restart if needed
- **Configuration**: Environment variables

#### 🍎 **macOS Client** (`macos_client/`)
- **Runtime**: Native Swift menu bar application
- **Platform**: macOS 12+ (Intel & Apple Silicon)
- **UI**: System tray icon with preferences window
- **Security**: Keychain integration for token storage
- **Features**: Native TUN interface, automatic config updates, launch at login

## ⚙️ Configuration

### Server Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_URL` | `sqlite+aiosqlite:///./app.db` | Database connection string (SQLite/PostgreSQL/MySQL) |
| `SECRET_KEY` | `change-me` | Session encryption key (⚠️ **must change in production!**) |
| `ADMIN_EMAIL` | None | Initial admin email (⚠️ **only used on first startup if no users exist**) |
| `ADMIN_PASSWORD` | None | Initial admin password (⚠️ **only used on first startup if no users exist**) |
| `CA_DEFAULT_VALIDITY_DAYS` | `540` (18 months) | CA certificate validity period |
| `CA_ROTATE_AT_DAYS` | `365` (12 months) | When to rotate CA |
| `CA_OVERLAP_DAYS` | `90` (3 months) | CA overlap window during rotation |
| `CLIENT_CERT_VALIDITY_DAYS` | `180` (6 months) | Client certificate validity |
| `CLIENT_ROTATE_BEFORE_DAYS` | `90` (3 months) | When to rotate client certs |
| `LIGHTHOUSE_DEFAULT_PORT` | `4242` | Default Nebula lighthouse port |
| `SERVER_PUBLIC_URL` | `http://localhost:8080` | Public URL for server (used in client configs) |
| `ENABLE_SCHEMA_AUTOSYNC` | `false` | Auto-add missing columns on startup (dev only, use Alembic in prod) |
| `APP_ENV` | `development` | Application environment (development/production) |

**Note**: Global settings like Punchy mode, default Docker image, and server URL are configured through the web UI Settings page after initial setup.

> **Note**: `ADMIN_EMAIL` and `ADMIN_PASSWORD` are only used during initial deployment when no admin user exists in the database. If you need to reset the admin password, you must do so through the web UI or by manually modifying the database.

### Client Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLIENT_TOKEN` | ✅ Yes | - | Authentication token from server |
| `SERVER_URL` | ✅ Yes | - | Server API endpoint |
| `POLL_INTERVAL_HOURS` | No | `24` | How often to check for updates |
| `START_NEBULA` | No | `true` | Whether to start Nebula daemon |

### Database Options

#### SQLite (Development/Small Deployments)
```bash
DB_URL=sqlite+aiosqlite:///./data/app.db
```

#### PostgreSQL (Production Recommended)
```bash
DB_URL=postgresql+asyncpg://username:password@hostname:5432/database
```

#### MySQL
```bash
DB_URL=mysql+aiomysql://username:password@hostname:3306/database
```

## 📚 API Documentation

### Key API Endpoints

#### Authentication
- `POST /api/v1/auth/login` - Login (returns session cookie)
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/me` - Get current user info

#### Client Configuration (for agents)
- `POST /api/v1/client/config` - Fetch Nebula config and certificates (token-based auth)

#### Clients Management
- `GET /api/v1/clients` - List all clients (filtered by permissions)
- `POST /api/v1/clients` - Create new client
- `GET /api/v1/clients/{id}` - Get client details
- `PUT /api/v1/clients/{id}` - Update client
- `DELETE /api/v1/clients/{id}` - Delete client
- `GET /api/v1/clients/{id}/config` - Download Nebula config YAML
- `GET /api/v1/clients/{id}/docker-compose` - Generate Docker Compose file
- `POST /api/v1/clients/{id}/certificates/reissue` - Force certificate reissue

#### Groups & Permissions
- `GET /api/v1/groups` - List groups
- `POST /api/v1/groups` - Create group
- `PUT /api/v1/groups/{id}` - Update group
- `DELETE /api/v1/groups/{id}` - Delete group
- `GET /api/v1/user-groups` - List user groups
- `POST /api/v1/clients/{id}/permissions` - Grant user access to client

#### Firewall Rules
- `GET /api/v1/firewall-rulesets` - List firewall rulesets
- `POST /api/v1/firewall-rulesets` - Create ruleset
- `GET /api/v1/firewall-rules` - List individual firewall rules
- `POST /api/v1/firewall-rules` - Create firewall rule

#### IP Management
- `GET /api/v1/ip-pools` - List IP pools
 
## 🧩 Systemd Services (Optional)

You can install systemd units on the host that automatically start/stop your Docker Compose services on boot. The templates and installer script are embedded in the container images.

### Quick Setup

**Step 1**: Copy the installer script from a running container to your host:

```bash
# Copy from server container
docker cp managed-nebula-server-1:/opt/managed-nebula/install-systemd-service.sh .

# Or from client container  
docker cp managed-nebula-client-1:/opt/managed-nebula/install-systemd-service.sh .
```

**Step 2**: Run the installer on your host (requires `docker` CLI and `sudo`):

```bash
# Install and activate server service
bash install-systemd-service.sh server --activate

# Install and activate client service
bash install-systemd-service.sh client --activate
```

**Step 3**: Verify the services:

```bash
sudo systemctl status managed-nebula-server.service
sudo systemctl restart managed-nebula-server.service
```

### Preview Before Installing

Render the unit file to review it first:

```bash
bash install-systemd-service.sh server --render managed-nebula-server.service
cat managed-nebula-server.service

# Then install manually
sudo install -m 0644 managed-nebula-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now managed-nebula-server.service
```

### How It Works

The installer script:
1. Uses `docker inspect` to detect your running container
2. Reads Docker Compose metadata (working dir, compose files, project name)
3. Renders a systemd unit that runs: `docker compose -f <files> -p <project> up -d <service>`
4. Installs to `/etc/systemd/system/managed-nebula-<service>.service`

**Note**: The script must run on the host (not inside the container) since it needs access to the `docker` CLI to inspect container metadata.

- `POST /api/v1/ip-pools` - Create IP pool
- `GET /api/v1/ip-groups` - List IP groups within pools

#### CA Management
- `GET /api/v1/ca` - List CA certificates
- `POST /api/v1/ca` - Create new CA
- `POST /api/v1/ca/import` - Import existing CA
- `DELETE /api/v1/ca/{id}` - Delete CA

#### Users & Settings
- `GET /api/v1/users` - List users (admin only)
- `POST /api/v1/users` - Create user (admin only)
- `GET /api/v1/settings` - Get global settings
- `PUT /api/v1/settings` - Update global settings

**Interactive API documentation:**

**Production deployment** (`docker-compose-server.yml`):
- Swagger UI: `https://localhost/api/docs`
- ReDoc: `https://localhost/api/redoc`
- OpenAPI spec: `https://localhost/api/openapi.json`

**Development mode** (`development-docker-compose-server.yml`):
- Swagger UI: `https://localhost/api/docs`
- ReDoc: `https://localhost/api/redoc`
- OpenAPI spec: `https://localhost/api/openapi.json`
- Direct server access: `http://localhost:8080/docs` and `http://localhost:8080/redoc`

All API documentation is accessible through the frontend proxy with proper SSL termination and includes comprehensive endpoint documentation, request/response schemas, and interactive testing capabilities.

See [DOCS_ACCESS.md](DOCS_ACCESS.md) for detailed documentation access guide.

## �️ Management Commands

The server includes a `manage.py` CLI tool for administrative tasks:

### Create Admin User
```bash
# Interactive (prompts for password)
docker exec -it <container> python manage.py create-admin admin@example.com

# Non-interactive
docker exec <container> python manage.py create-admin admin@example.com MyPassword123

# Using the helper script
docker exec <container> bash create-admin.sh admin@example.com
```

### Reset User Password
```bash
# Interactive
docker exec -it <container> python manage.py reset-password user@example.com

# Non-interactive
docker exec <container> python manage.py reset-password user@example.com NewPassword123
```

### List All Users
```bash
docker exec <container> python manage.py list-users
```

### Make User an Admin
```bash
docker exec <container> python manage.py make-admin user@example.com
```

### Full Management CLI Usage
```bash
docker exec <container> python manage.py --help
```

## �🔧 Development

### Branch Workflow Agent (Required)

This repo includes a small helper that enforces our Copilot branch policy and naming scheme.

Enable local git hooks once per clone:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/branch-agent.sh
```

Common commands:

```bash
# Ensure dev branch exists remotely (created from main if missing)
./scripts/branch-agent.sh ensure-dev

# Create a properly named feature branch from dev
./scripts/branch-agent.sh create-branch feature server 5 "Add user auth endpoint"

# Validate current branch conforms to policy
./scripts/branch-agent.sh check

# Print the required PR title format for this branch
./scripts/branch-agent.sh pr-title "Add user auth endpoint"

# Rebase your branch on the latest dev
./scripts/branch-agent.sh rebase-dev
```

Notes:
- Direct pushes to `main` are blocked by the pre-push hook.
- All PRs must target `dev`. A GitHub Action validates base branch, branch name, and PR title.
- **Copilot-generated branches** (starting with `copilot/`) are also allowed alongside the manual naming scheme.

### Local Development Setup

```bash
# Install server dependencies
cd server
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Database Migrations

The project uses Alembic for database schema management. The initial migration includes all tables.

```bash
# Apply migrations (done automatically by entrypoint.sh)
cd server
alembic upgrade head

# Create a new migration (after model changes)
alembic revision --autogenerate -m "description of changes"

# Check current migration version
alembic current
```

On container startup:
1. Alembic migrations run first (`alembic upgrade head`)
2. SQLAlchemy creates any missing tables from models (`Base.metadata.create_all`)
3. Schema sync adds any missing columns (if `ENABLE_SCHEMA_AUTOSYNC=true`)

### Running Tests

```bash
cd server
pytest tests/
```

Tests require `nebula-cert` binary in PATH. Skip certificate tests with:
```bash
pytest tests/ -m "not nebula_cert"
```

### Using Pre-built Images

Pre-built images are available from GitHub Container Registry:

```bash
# Pull images
docker pull ghcr.io/kumpeapps/managed-nebula/server:latest
docker pull ghcr.io/kumpeapps/managed-nebula/frontend:latest
docker pull ghcr.io/kumpeapps/managed-nebula/client:latest
```

Update your `docker-compose.yml` to use these images:
```yaml
services:
  server:
    image: ghcr.io/kumpeapps/managed-nebula/server:latest
    # ... rest of config
  
  frontend:
    image: ghcr.io/kumpeapps/managed-nebula/frontend:latest
    # ... rest of config
```

### Building Docker Images Locally

If you prefer to build images yourself:

```bash
# Server (FastAPI backend)
docker build -t managed-nebula-server:latest -f server/Dockerfile server/

# Frontend (Angular SPA)
docker build -t managed-nebula-frontend:latest -f frontend/Dockerfile frontend/

# Client (Agent)
docker build -t managed-nebula-client:latest -f client/Dockerfile client/
```

### Frontend Development

```bash
cd frontend
npm install
npm start  # Starts dev server on http://localhost

# Build for production
npm run build:prod  # Output in dist/
```

## 🛡️ Security Considerations

### Production Deployment Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Use PostgreSQL or MySQL instead of SQLite
- [ ] Enable HTTPS/TLS on the server
- [ ] Implement network firewall rules
- [ ] Regularly backup the database
- [ ] Monitor certificate expiry dates
- [ ] Rotate client tokens periodically
- [ ] Review and audit user access logs
- [ ] Keep Docker images updated

### Password Security

The system uses `bcrypt_sha256` for password hashing to avoid bcrypt's 72-byte password truncation limitation.

## 📖 Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Common commands and troubleshooting
- **[API Docs Access Guide](DOCS_ACCESS.md)** - How to access Swagger UI, ReDoc, and OpenAPI schema
- [API Documentation](API_DOCUMENTATION.md) - Complete REST API reference
- [Group System](GROUP_SYSTEM.md) - Hierarchical groups and permissions
- [Copilot Instructions](.github/copilot-instructions.md) - AI agent guidance for development
- [Docker Compose](docker-compose.yml) - Container orchestration setup
- [Server Source](server/) - FastAPI backend application
- [Frontend Source](frontend/) - Angular 17 web interface
- [Client Source](client/) - Python agent implementation

## 🚧 Project Status

**Current Version**: v1.0.0 (Initial Release)

This project is in active development. The initial release includes:
- ✅ Complete REST API with full CRUD operations
- ✅ Angular 17 web interface
- ✅ Certificate authority management with rotation
- ✅ Structured firewall rulesets
- ✅ Hierarchical group system with permissions
- ✅ IP pool and IP group management
- ✅ Client agent with auto-rotation
- ✅ Multi-database support (SQLite/PostgreSQL/MySQL)
- ✅ User and user group management
- ✅ Granular client permissions

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Guidelines
1. All database changes must include Alembic migrations
2. API endpoints must use Pydantic schemas from `models/schemas.py`
3. Frontend changes should follow Angular best practices
4. Test coverage for new features is appreciated

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

Built with ❤️ using:
- [Nebula](https://github.com/slackhq/nebula) by Slack - The mesh VPN this project manages
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Angular](https://angular.io/) - Frontend framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Async ORM
- [Alembic](https://alembic.sqlalchemy.org/) - Database migrations
- [Docker](https://www.docker.com/) - Containerization

---

<div align="center">

**[⬆ Back to Top](#-managed-nebula)**

Made by [kumpeapps](https://github.com/kumpeapps)

</div>
