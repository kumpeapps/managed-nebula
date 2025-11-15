# Comprehensive RBAC Permissions System Implementation

## Overview
This document describes the comprehensive Role-Based Access Control (RBAC) permissions system implemented for the Managed Nebula platform. The system provides granular control over user access to all platform resources.

## Architecture

### Backend (Server)

#### Permission Model
- **Permission**: Defines a single permission with `resource` (e.g., "clients", "groups") and `action` (e.g., "read", "create", "update", "delete")
- **UserGroup**: Groups of users with assigned permissions; groups with `is_admin=True` bypass all permission checks
- **UserGroupMembership**: Associates users with user groups
- **user_group_permissions**: Association table linking user groups to permissions

#### Database Migrations
1. **f40acab05062_add_comprehensive_permissions_system.py**: Initial permissions infrastructure
   - Creates `permissions` table
   - Adds `is_admin` column to `user_groups`
   - Seeds 28 default permissions for core resources
   - Creates default "Administrators" and "Users" groups
   
2. **2790ea32864b_add_missing_rbac_permissions.py**: Additional permissions
   - Adds permissions for `ip_groups`, `user_groups`, and `settings` resources
   - Grants read permissions to default "Users" group

#### Seeded Permissions

**Clients** (5 permissions):
- `clients:read` - View client information
- `clients:create` - Create new clients
- `clients:update` - Update client settings
- `clients:delete` - Delete clients
- `clients:download` - Download client configurations

**Groups** (4 permissions):
- `groups:read` - View Nebula groups
- `groups:create` - Create new Nebula groups
- `groups:update` - Update Nebula groups
- `groups:delete` - Delete Nebula groups

**Firewall Rules** (4 permissions):
- `firewall_rules:read` - View firewall rules
- `firewall_rules:create` - Create firewall rules
- `firewall_rules:update` - Update firewall rules
- `firewall_rules:delete` - Delete firewall rules

**IP Pools** (4 permissions):
- `ip_pools:read` - View IP pools
- `ip_pools:create` - Create IP pools
- `ip_pools:update` - Update IP pools
- `ip_pools:delete` - Delete IP pools

**IP Groups** (4 permissions):
- `ip_groups:read` - View IP groups
- `ip_groups:create` - Create IP groups
- `ip_groups:update` - Update IP groups
- `ip_groups:delete` - Delete IP groups

**CA** (4 permissions):
- `ca:read` - View certificate authorities
- `ca:create` - Create certificate authorities
- `ca:delete` - Delete certificate authorities
- `ca:download` - Download CA certificates

**Users** (4 permissions):
- `users:read` - View users
- `users:create` - Create new users
- `users:update` - Update user settings
- `users:delete` - Delete users

**User Groups** (5 permissions):
- `user_groups:read` - View user groups
- `user_groups:create` - Create user groups
- `user_groups:update` - Update user groups
- `user_groups:delete` - Delete user groups
- `user_groups:manage_members` - Add/remove members from user groups
- `user_groups:manage_permissions` - Assign/revoke permissions to user groups

**Settings** (3 permissions):
- `settings:read` - View system settings
- `settings:update` - Update system settings
- `settings:docker_compose` - Manage Docker Compose templates

**Dashboard** (1 permission):
- `dashboard:read` - View dashboard and statistics

**Lighthouse** (2 permissions):
- `lighthouse:read` - View lighthouse settings
- `lighthouse:update` - Update lighthouse settings

**Total: 44 permissions**

#### Permission Enforcement

**Authentication Dependency: `require_permission(resource, action)`**
- Factory function that creates a FastAPI dependency
- Checks if user has required permission via `User.has_permission()`
- Admin groups (is_admin=True) automatically have all permissions
- Returns 403 error if permission denied

**Replaced `require_admin` calls:**
All API endpoints now use `require_permission` instead of `require_admin`:
- Settings endpoints: `settings:read`, `settings:update`, `settings:docker_compose`
- Client endpoints: `clients:read`, `clients:create`, `clients:update`, `clients:delete`
- Group endpoints: `groups:read`, `groups:create`, `groups:update`, `groups:delete`
- Firewall ruleset endpoints: `firewall_rules:*`
- IP pool endpoints: `ip_pools:*`
- IP group endpoints: `ip_groups:*`
- CA endpoints: `ca:*`
- User endpoints: `users:*`
- User group endpoints: `user_groups:*`

#### API Endpoints

**Permission Management:**
- `GET /api/v1/permissions` - List all available permissions (requires `user_groups:read`)
- `GET /api/v1/user-groups/{id}/permissions` - List permissions for a user group
- `POST /api/v1/user-groups/{id}/permissions` - Grant permission to user group (requires `user_groups:manage_permissions`)
- `DELETE /api/v1/user-groups/{id}/permissions/{perm_id}` - Revoke permission from user group (requires `user_groups:manage_permissions`)

### Frontend (Angular)

#### New Components

**PermissionsComponent** (`/permissions`):
- Two-panel interface: user groups list + permissions grid
- Groups displayed with admin badge and member count
- Permissions organized by resource (collapsible sections)
- Toggle switches to grant/revoke permissions
- Admin groups display notice that they have all permissions
- Real-time updates via API calls

#### Updated Services

**ApiService** additions:
- `getPermissions()`: Fetch all permissions
- `getUserGroupPermissions(groupId)`: Fetch permissions for specific group
- `grantPermissionToUserGroup(groupId, permissionId)`: Grant permission
- `revokePermissionFromUserGroup(groupId, permissionId)`: Revoke permission

#### Updated Models

**Permission interface:**
```typescript
interface Permission {
  id: number;
  resource: string;
  action: string;
  description: string;
}
```

#### Navigation
- Added "Permissions" link to navbar (admin-only)
- Route: `/permissions` with AuthGuard protection

## Default User Groups

### Administrators Group
- **is_admin**: `true`
- **Permissions**: All (bypasses permission checks)
- **Description**: Full system administrators with all permissions
- **Members**: Automatically includes users with `admin` role

### Users Group
- **is_admin**: `false`
- **Permissions**: Read-only access to all resources
  - `clients:read`
  - `groups:read`
  - `firewall_rules:read`
  - `ip_pools:read`
  - `ip_groups:read`
  - `ca:read`
  - `users:read`
  - `user_groups:read`
  - `settings:read`
  - `dashboard:read`
  - `lighthouse:read`
- **Description**: Standard users with read-only access

## Permission Check Flow

1. **User makes API request** → Request includes session cookie
2. **FastAPI dependency injection** → `require_permission("resource", "action")` dependency executes
3. **User lookup** → `get_current_user()` retrieves user from session
4. **Permission check** → `user.has_permission(session, resource, action)` runs:
   - Fetch user's groups with `selectinload(UserGroup.permissions)`
   - If user belongs to any group with `is_admin=True` → ALLOW
   - Check if any group has the specific permission → ALLOW if found
   - Otherwise → DENY
5. **Response** → 200 OK if allowed, 403 Forbidden if denied

## Usage Examples

### Creating a New User Group with Specific Permissions

```bash
# Create group
curl -X POST https://localhost:4200/api/v1/user-groups \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name": "Operators", "description": "Can manage clients and view settings", "is_admin": false}'

# Grant permissions (get permission IDs from GET /api/v1/permissions)
curl -X POST https://localhost:4200/api/v1/user-groups/3/permissions \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"permission_id": 1}'  # clients:read

curl -X POST https://localhost:4200/api/v1/user-groups/3/permissions \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"permission_id": 2}'  # clients:create
```

### Adding User to Group

```bash
curl -X POST https://localhost:4200/api/v1/user-groups/3/members?user_id=5 \
  -b cookies.txt
```

### Testing Permission Denial

```bash
# User in "Operators" group tries to delete CA (no ca:delete permission)
curl -X DELETE https://localhost:4200/api/v1/ca/1 \
  -b operator-cookies.txt

# Response: 403 Forbidden
# {"detail": "Insufficient permissions: ca:delete required"}
```

## Testing Strategy

### Unit Tests
- Test `User.has_permission()` method with various group configurations
- Test `require_permission()` dependency with admin and non-admin users
- Test permission inheritance (admin groups have all permissions)

### Integration Tests
1. Create non-admin user and assign to "Users" group
2. Verify user can GET /api/v1/clients (has clients:read)
3. Verify user cannot POST /api/v1/clients (lacks clients:create) → 403
4. Grant clients:create to "Users" group
5. Verify user can now POST /api/v1/clients → 200

### Frontend Tests
1. Login as admin, navigate to /permissions
2. Verify all permissions are displayed grouped by resource
3. Select "Users" group
4. Toggle off clients:read permission
5. Login as regular user
6. Verify GET /api/v1/clients returns 403

## Migration Path from Legacy `require_admin`

1. **Identify admin-only endpoints** → All endpoints using `require_admin`
2. **Map to resources** → Determine which resource each endpoint operates on
3. **Replace dependency** → `Depends(require_admin)` → `Depends(require_permission("resource", "action"))`
4. **Test backwards compatibility** → Admin groups still have full access via `is_admin=True`
5. **Grant permissions to non-admin groups** → Use Permissions UI to configure

## Security Considerations

- **Admin bypass**: Groups with `is_admin=True` automatically pass all permission checks
- **Permission checks are mandatory**: All protected endpoints must have authentication + permission check
- **Database-driven**: Permissions stored in database, can be modified at runtime
- **Async-safe**: Uses `AsyncSession` and `await` for all database operations
- **Eager loading**: Relationships use `selectinload()` to avoid lazy-load issues

## Future Enhancements

1. **Permission inheritance**: Hierarchical permissions (e.g., `create` implies `read`)
2. **Resource-level permissions**: Per-resource permissions (e.g., "can manage client #5")
3. **Time-based permissions**: Temporary permission grants with expiration
4. **Audit logging**: Track permission changes and access attempts
5. **Frontend permission checks**: Proactively hide UI elements user can't access
6. **API scopes**: OAuth-style scopes for API tokens
7. **Permission templates**: Pre-configured permission sets for common roles

## Files Modified

### Backend
- `server/alembic/versions/f40acab05062_add_comprehensive_permissions_system.py`
- `server/alembic/versions/2790ea32864b_add_missing_rbac_permissions.py`
- `server/app/models/permissions.py`
- `server/app/models/user.py` (added `has_permission()` method)
- `server/app/core/auth.py` (added `require_permission()` dependency)
- `server/app/routers/api.py` (replaced all `require_admin` with `require_permission`)

### Frontend
- `frontend/src/app/components/permissions.component.ts` (new)
- `frontend/src/app/models/index.ts` (added Permission interface)
- `frontend/src/app/services/api.service.ts` (added permission methods)
- `frontend/src/app/app-routing.module.ts` (added /permissions route)
- `frontend/src/app/components/navbar.component.ts` (added Permissions link)

## Summary

The comprehensive RBAC system provides:
- ✅ 44 granular permissions across 11 resources
- ✅ Permission enforcement on all API endpoints
- ✅ Admin groups with unrestricted access
- ✅ Default "Users" group with read-only access
- ✅ Web UI for managing permissions
- ✅ Backward compatible with existing admin role
- ✅ Database-driven, runtime-configurable
- ✅ Async-safe implementation
- ✅ RESTful API endpoints for programmatic management

Users can now be organized into groups with fine-grained permissions, enabling secure delegation of administrative tasks without granting full admin access.
