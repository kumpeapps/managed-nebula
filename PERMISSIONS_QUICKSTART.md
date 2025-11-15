# Permissions System Quick Start

This guide gets you up and running with the new permissions system in 5 minutes.

## What Changed?

The system now has **granular permissions** based on user groups instead of just admin/user roles.

## Quick Setup

### 1. Run Migration (First Time Only)

```bash
cd server
alembic upgrade head
```

This creates:
- ✅ 28 default permissions
- ✅ "Administrators" group (has all permissions)
- ✅ "Users" group (read-only access)
- ✅ Migrates existing admins to Administrators group

### 2. Check Your Permissions

```bash
# List all permissions
curl -X GET http://localhost:8080/api/v1/permissions \
  -H "Cookie: session=YOUR_SESSION_COOKIE"

# List all user groups
curl -X GET http://localhost:8080/api/v1/user-groups \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

## Common Tasks

### Create a New User Group

```bash
curl -X POST http://localhost:8080/api/v1/user-groups \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION" \
  -d '{
    "name": "Developers",
    "description": "Development team",
    "is_admin": false
  }'
```

### Add User to Group

```bash
# Add user ID 5 to group ID 3
curl -X POST "http://localhost:8080/api/v1/user-groups/3/members?user_id=5" \
  -H "Cookie: session=YOUR_SESSION"
```

### Grant Permission to Group

```bash
# Grant clients:create to group 3
curl -X POST http://localhost:8080/api/v1/user-groups/3/permissions \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION" \
  -d '{
    "resource": "clients",
    "action": "create"
  }'
```

### Check User's Permissions (in code)

```python
from app.core.auth import require_permission

@router.get("/clients")
async def list_clients(
    user: User = Depends(require_permission("clients", "read")),
    session: AsyncSession = Depends(get_session)
):
    # User is guaranteed to have clients:read permission
    ...
```

## Available Permissions

| Resource | Actions | What It Controls |
|----------|---------|------------------|
| `clients` | read, create, update, delete, download | Client management |
| `groups` | read, create, update, delete | Nebula groups |
| `firewall_rules` | read, create, update, delete | Firewall rules |
| `ip_pools` | read, create, update, delete | IP pools |
| `ca` | read, create, delete, download | Certificates |
| `users` | read, create, update, delete | User management |
| `lighthouse` | read, update | Lighthouse settings |
| `dashboard` | read | Dashboard access |

## Default Groups

### Administrators
- **Has**: All permissions automatically
- **Cannot**: Be deleted or lose admin status
- **Use for**: Platform administrators

### Users
- **Has**: Read-only access to everything
- **Can**: Be modified or deleted
- **Use for**: Regular users who need view-only access

## Important Safety Features

🔒 **You CANNOT:**
- Delete the Administrators group
- Remove admin status from Administrators group
- Remove the last admin from Administrators group
- Delete the last admin user

These safeguards prevent accidental lockout!

## Best Practices

### ✅ DO:
- Keep at least 2-3 users in the Administrators group
- Create groups for different teams/roles
- Grant only needed permissions (principle of least privilege)
- Regularly audit group memberships

### ❌ DON'T:
- Have only one admin (risk of lockout)
- Give everyone admin access
- Modify permissions on the Administrators group
- Delete system groups (Administrators, Users)

## Troubleshooting

### User Can't Access Something

1. Check user's groups: `GET /api/v1/users/{id}/groups`
2. Check group's permissions: `GET /api/v1/user-groups/{group_id}/permissions`
3. Grant the missing permission to their group

### Can't Delete a User

Error 409 usually means they're the last admin. Add another admin first:

```bash
# Add user 7 to Administrators group (id=1)
POST /api/v1/user-groups/1/members?user_id=7
```

## Example Workflow

### Scenario: Give Developers Access to Manage Clients

```bash
# 1. Create Developers group
curl -X POST http://localhost:8080/api/v1/user-groups \
  -d '{"name": "Developers", "is_admin": false}'

# Response: {"id": 3, "name": "Developers", ...}

# 2. Grant necessary permissions
curl -X POST http://localhost:8080/api/v1/user-groups/3/permissions \
  -d '{"resource": "clients", "action": "read"}'
curl -X POST http://localhost:8080/api/v1/user-groups/3/permissions \
  -d '{"resource": "clients", "action": "update"}'
curl -X POST http://localhost:8080/api/v1/user-groups/3/permissions \
  -d '{"resource": "clients", "action": "create"}'

# 3. Add developers to the group
curl -X POST "http://localhost:8080/api/v1/user-groups/3/members?user_id=5"
curl -X POST "http://localhost:8080/api/v1/user-groups/3/members?user_id=6"

# Done! Users 5 and 6 can now manage clients
```

## Need More Help?

📖 Full documentation: [PERMISSIONS_SYSTEM.md](PERMISSIONS_SYSTEM.md)

📋 Test results: [server/tests/test_permissions_manual.md](server/tests/test_permissions_manual.md)

## Quick Reference Card

```
# Permission Format: resource:action
clients:read          # View clients
clients:create        # Create clients  
clients:update        # Modify clients
clients:delete        # Delete clients
clients:download      # Download configs

users:read            # View users
users:create          # Create users
users:update          # Modify users (includes group membership)
users:delete          # Delete users

# Similar pattern for: groups, firewall_rules, ip_pools, ca, lighthouse, dashboard
```

## Backward Compatibility

✅ **Old code still works!**

Existing `require_admin` checks now verify admin group membership instead of role. No code changes needed for basic compatibility.

---

**System Status**: ✅ Production Ready

Last Updated: 2025-11-15
