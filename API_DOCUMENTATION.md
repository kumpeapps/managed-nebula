# Managed Nebula API Documentation

## Overview

The Managed Nebula server provides a RESTful JSON API for managing the Nebula mesh VPN network. All endpoints return JSON responses and require authentication via session cookies (except the client config download endpoint which uses token authentication).

**Base URL:** `/api/v1`

## Authentication

### Web GUI Authentication
- **Method:** Session-based (cookies)
- **Login:** `POST /api/v1/auth/login`
- **Logout:** `POST /api/v1/auth/logout`
- **Current User:** `GET /api/v1/auth/me`
- **Role-based Access:** Most admin endpoints require `admin` role

### Client Agent Authentication
- **Method:** Token-based (in request body)
- **Endpoint:** `POST /api/v1/client/config`
- **Token:** Created per-client in database, validated via `ClientToken` table

## API Endpoints

### Health Check
- `GET /api/v1/healthz` - Health check endpoint (no auth required)

### Client Agent (Used by nebula-client)
- `POST /api/v1/client/config` - Download Nebula configuration, certificates, and CA chain
  - **Request Body:** `{token: string, public_key: string}`
  - **Returns:** `{config: string, client_cert_pem: string, ca_chain_pems: string[], cert_not_before: string, cert_not_after: string, lighthouse: boolean, key_path: string}`
  - **Used By:** Client agent polling every POLL_INTERVAL_HOURS (default 24)

---

## REST API Resources

### Clients (`/clients`)

Manage Nebula network clients (nodes).

#### List All Clients
```
GET /api/v1/clients
```
**Returns:** Array of ClientResponse objects with groups and tokens (admin only sees tokens)

**Response Schema:**
```json
[{
  "id": 1,
  "name": "client-name",
  "ip_address": "10.100.0.1",
  "is_lighthouse": false,
  "public_ip": null,
  "is_blocked": false,
  "created_at": "2025-11-01T00:00:00",
  "config_last_changed_at": null,
  "last_config_download_at": null,
  "groups": [{"id": 1, "name": "group-name"}],
  "token": "abc123..." // Admin only
}]
```

#### Get Single Client
```
GET /api/v1/clients/{client_id}
```
**Returns:** ClientResponse object

#### Update Client
```
PUT /api/v1/clients/{client_id}
```
**Request Body (all fields optional):**
```json
{
  "name": "new-name",
  "is_lighthouse": false,
  "public_ip": "1.2.3.4",
  "is_blocked": false,
  "group_ids": [1, 2],
  "firewall_rule_ids": [1, 2]
}
```
**Returns:** Updated ClientResponse
**Note:** Automatically updates `config_last_changed_at` timestamp when groups or firewall rules change

#### Delete Client
```
DELETE /api/v1/clients/{client_id}
```
**Returns:** `{"status": "deleted", "id": client_id}`

---

### Groups (`/groups`)

Manage client groups for organizing and applying firewall rules.

#### List All Groups
```
GET /api/v1/groups
```
**Returns:** Array of GroupResponse objects with client counts

**Response Schema:**
```json
[{
  "id": 1,
  "name": "group-name",
  "client_count": 5
}]
```

#### Get Single Group
```
GET /api/v1/groups/{group_id}
```
**Returns:** GroupResponse object

#### Create Group
```
POST /api/v1/groups
```
**Request Body:**
```json
{
  "name": "new-group-name"
}
```
**Returns:** Created GroupResponse

#### Update Group
```
PUT /api/v1/groups/{group_id}
```
**Request Body:**
```json
{
  "name": "updated-name"
}
```
**Returns:** Updated GroupResponse

#### Delete Group
```
DELETE /api/v1/groups/{group_id}
```
**Returns:** `{"status": "deleted", "id": group_id}`
**Error:** 409 Conflict if any clients still use this group

---

### Firewall Rules (`/firewall-rules`)

Manage Nebula firewall rules (YAML format).

#### List All Firewall Rules
```
GET /api/v1/firewall-rules
```
**Returns:** Array of FirewallRuleResponse objects

**Response Schema:**
```json
[{
  "id": 1,
  "name": "rule-name",
  "rule": "outbound:\n  - port: 80\n    proto: tcp",
  "client_count": 3
}]
```

#### Get Single Firewall Rule
```
GET /api/v1/firewall-rules/{rule_id}
```
**Returns:** FirewallRuleResponse object

#### Create Firewall Rule
```
POST /api/v1/firewall-rules
```
**Request Body:**
```json
{
  "name": "new-rule-name",
  "rule": "outbound:\n  - port: 80\n    proto: tcp"
}
```
**Returns:** Created FirewallRuleResponse
**Validation:** YAML format validated via `yaml.safe_load()`

#### Update Firewall Rule
```
PUT /api/v1/firewall-rules/{rule_id}
```
**Request Body:**
```json
{
  "name": "updated-name",
  "rule": "outbound:\n  - port: 443\n    proto: tcp"
}
```
**Returns:** Updated FirewallRuleResponse
**Validation:** YAML format validated via `yaml.safe_load()`

#### Delete Firewall Rule
```
DELETE /api/v1/firewall-rules/{rule_id}
```
**Returns:** `{"status": "deleted", "id": rule_id}`
**Error:** 409 Conflict if any clients still reference this rule

---

### IP Pools (`/ip-pools`)

Manage IP address pools (CIDR ranges) for client IP allocation.

#### List All IP Pools
```
GET /api/v1/ip-pools
```
**Returns:** Array of IPPoolResponse objects

**Response Schema:**
```json
[{
  "id": 1,
  "cidr": "10.100.0.0/16",
  "description": "Default pool",
  "allocated_count": 15
}]
```

#### Get Single IP Pool
```
GET /api/v1/ip-pools/{pool_id}
```
**Returns:** IPPoolResponse object

#### Create IP Pool
```
POST /api/v1/ip-pools
```
**Request Body:**
```json
{
  "cidr": "10.200.0.0/16",
  "description": "Secondary pool"
}
```
**Returns:** Created IPPoolResponse
**Validation:** CIDR format validated via `ipaddress.ip_network()`

#### Update IP Pool
```
PUT /api/v1/ip-pools/{pool_id}
```
**Request Body (all fields optional):**
```json
{
  "cidr": "10.200.0.0/16",
  "description": "Updated description"
}
```
**Returns:** Updated IPPoolResponse
**Note:** Cannot change CIDR if any IPs are allocated (400 error)

#### Delete IP Pool
```
DELETE /api/v1/ip-pools/{pool_id}
```
**Returns:** `{"status": "deleted", "id": pool_id}`
**Error:** 409 Conflict if any IPs are allocated from this pool

---

### Certificate Authorities (`/ca`)

Manage Nebula CA certificates (lifecycle, rotation, import).

#### List All CAs
```
GET /api/v1/ca
```
**Returns:** Array of CAResponse objects with status classification

**Response Schema:**
```json
[{
  "id": 1,
  "name": "Production CA",
  "not_before": "2025-01-01T00:00:00",
  "not_after": "2026-07-01T00:00:00",
  "is_active": true,
  "is_previous": false,
  "can_sign": true,
  "include_in_config": true,
  "created_at": "2025-01-01T00:00:00",
  "status": "current"
}]
```

**Status Values:**
- `current` - Active CA in use
- `previous` - Previous CA during rotation overlap window
- `expired` - CA past not_after date
- `inactive` - Deactivated CA

#### Create CA
```
POST /api/v1/ca/create
```
**Request Body:**
```json
{
  "name": "Production CA",
  "validity_months": 18
}
```
**Returns:** Created CAResponse
**Note:** Creates new CA via `CertManager.create_new_ca()`, marks previous CAs as `is_previous=True`

#### Import CA
```
POST /api/v1/ca/import
```
**Request Body:**
```json
{
  "name": "Imported CA",
  "pem_cert": "-----BEGIN NEBULA CERTIFICATE-----\n...",
  "pem_key": "-----BEGIN NEBULA PRIVATE KEY-----\n..." // Optional
}
```
**Returns:** Imported CAResponse

#### Delete CA
```
DELETE /api/v1/ca/{ca_id}
```
**Returns:** `{"status": "deleted", "id": ca_id}`
**Error:** 409 Conflict if attempting to delete active CA
**Auth:** Admin only

---

### Users (`/users`)

Manage user accounts and roles (admin only).

#### List All Users
```
GET /api/v1/users
```
**Returns:** Array of UserResponse objects
**Auth:** Admin only

**Response Schema:**
```json
[{
  "id": 1,
  "email": "admin@example.com",
  "is_active": true,
  "role": {"id": 1, "name": "admin"},
  "created_at": "2025-01-01T00:00:00"
}]
```

#### Get Single User
```
GET /api/v1/users/{user_id}
```
**Returns:** UserResponse object
**Auth:** Admin only

#### Create User
```
POST /api/v1/users
```
**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure-password",
  "role_name": "user", // "admin" or "user"
  "is_active": true
}
```
**Returns:** Created UserResponse
**Auth:** Admin only
**Note:** Password is hashed via `auth.hash_password()` using bcrypt_sha256

#### Update User
```
PUT /api/v1/users/{user_id}
```
**Request Body (all fields optional):**
```json
{
  "email": "newemail@example.com",
  "password": "new-password",
  "role_name": "admin",
  "is_active": false
}
```
**Returns:** Updated UserResponse
**Auth:** Admin only
**Note:** Password is re-hashed if provided

#### Delete User
```
DELETE /api/v1/users/{user_id}
```
**Returns:** `{"status": "deleted", "id": user_id}`
**Error:** 409 Conflict if attempting to delete yourself
**Auth:** Admin only

---

## Error Responses

All endpoints return standard HTTP status codes with JSON error details:

```json
{
  "detail": "Error message here"
}
```

**Common Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid input (e.g., invalid CIDR, invalid YAML)
- `401 Unauthorized` - Not authenticated
- `403 Forbidden` - Authenticated but insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Cannot delete resource still in use
- `503 Service Unavailable` - No active CA configured

---

## Removed Legacy Endpoints

The following endpoints were removed during the API refactoring:

**API Endpoints:**
- ❌ `GET /api/v1/ip-choices` - Use frontend IP picker with pool data instead
- ❌ `POST /api/v1/admin/client/create` - Use `POST /clients` with proper REST pattern
- ❌ `POST /api/v1/admin/ip-pool/create` - Use `POST /ip-pools` instead

**HTML Endpoints (replaced by Angular SPA):**
- ❌ `GET /login` - HTML login page (use `POST /api/v1/auth/login` instead)
- ❌ `POST /login` - HTML form login (use `POST /api/v1/auth/login` instead)
- ❌ `GET /logout` - HTML logout redirect (use `POST /api/v1/auth/logout` instead)
- ❌ `GET /setup` - HTML setup page (manual user creation via REST API or direct DB)
- ❌ `POST /setup` - HTML setup form (manual user creation via REST API or direct DB)

---

## Client Agent Workflow

The Python client agent (`client/agent.py`) follows this workflow:

1. **Startup:**
   - Generate keypair if not exists: `nebula-cert keygen`
   - Read token from environment variable or config file

2. **Config Download:**
   - `POST /api/v1/client/config` with `{token, public_key}`
   - Receive config YAML, client certificate PEM, CA chain PEMs

3. **File Management:**
   - Write `/etc/nebula/config.yml` (YAML config)
   - Write `/etc/nebula/host.crt` (client certificate)
   - Write `/etc/nebula/ca.crt` (CA bundle)
   - Keep `/var/lib/nebula/host.key` (private key)

4. **Daemon Management:**
   - Start `nebula` daemon via `entrypoint.sh`
   - Poll server every `POLL_INTERVAL_HOURS` (default 24) for config updates

5. **Certificate Rotation:**
   - Server automatically reissues certificates if expiry within 3 months
   - Client receives new certificate on next poll
   - Only reissues if IP/CIDR/groups changed (otherwise reuses existing cert)

---

## Security Notes

1. **Password Storage:** Uses `bcrypt_sha256` (not plain bcrypt) to avoid 72-byte truncation
2. **Session Auth:** Session cookies with secure flags (production should use HTTPS)
3. **Role-Based Access:** Admin role required for most management endpoints
4. **Token Validation:** Client tokens validated via database lookup, must be active
5. **Certificate Security:** Client private keys never leave the client, server only receives public keys
6. **CIDR Validation:** All IP addresses and CIDR ranges validated before storage
7. **YAML Validation:** Firewall rules validated for parseable YAML syntax

---

## Database Models

**Primary Tables:**
- `clients` - Nebula network nodes
- `groups` - Client groups for organization
- `firewall_rules` - YAML firewall rule definitions
- `ip_pools` - CIDR ranges for IP allocation
- `ip_assignments` - Client IP address assignments
- `ca_certificates` - Nebula CA certificates
- `client_certificates` - Issued client certificates
- `client_tokens` - Authentication tokens for client agents
- `users` - Web GUI user accounts
- `roles` - User roles (admin, user)

**Association Tables:**
- `client_groups` - Many-to-many: clients ↔ groups
- `client_firewall_rules` - Many-to-many: clients ↔ firewall rules

---

## Configuration Building

The `build_nebula_config()` function (`services/config_builder.py`) generates Nebula YAML configs with:

- **Static Host Maps:** Lighthouse public IPs for NAT traversal
- **Lighthouse Configuration:** Lighthouse hosts and intervals
- **Firewall Rules:** Merged from client's assigned rules
- **Groups:** Client group memberships
- **CA Bundle:** Concatenated PEM certs from all active/previous CAs
- **Certificate Paths:** References to local filesystem paths
- **Punchy Settings:** UDP hole-punching configuration

---

## Example: Complete Client Lifecycle

```bash
# 1. Create IP Pool (if none exists)
curl -X POST http://localhost:8080/api/v1/ip-pools \
  -H "Content-Type: application/json" \
  -d '{"cidr": "10.100.0.0/16", "description": "Main pool"}'

# 2. Create Groups
curl -X POST http://localhost:8080/api/v1/groups \
  -H "Content-Type: application/json" \
  -d '{"name": "web-servers"}'

# 3. Create Firewall Rule
curl -X POST http://localhost:8080/api/v1/firewall-rules \
  -H "Content-Type: application/json" \
  -d '{"name": "allow-http", "rule": "outbound:\n  - port: 80\n    proto: tcp\n    host: any"}'

# 4. Create Client (via database/setup UI)
# This creates client record and assigns IP

# 5. Update Client with Groups and Firewall Rules
curl -X PUT http://localhost:8080/api/v1/clients/1 \
  -H "Content-Type: application/json" \
  -d '{"group_ids": [1], "firewall_rule_ids": [1]}'

# 6. Client Agent Downloads Config
curl -X POST http://localhost:8080/api/v1/client/config \
  -H "Content-Type: application/json" \
  -d '{"token": "abc123...", "public_key": "..."}'
```

---

**Last Updated:** 2025-11-08  
**API Version:** v1  
**Server:** FastAPI with SQLAlchemy async  
**Authentication:** Session-based (web) + Token-based (client agent)
