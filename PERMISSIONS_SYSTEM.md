# Comprehensive User Permissions System

This document describes the comprehensive permission system implemented for the Managed Nebula platform.

## Overview

The permission system provides granular, role-based access control through user groups and permissions. It replaces the simple admin/user role system with a flexible group-based permissions model while maintaining backward compatibility.

## Key Features

- **Resource-based permissions**: Fine-grained control over actions on specific resources
- **User groups**: Organize users and assign permissions collectively
- **Admin groups**: Special groups that automatically have all permissions
- **Permission inheritance**: Users inherit permissions from all groups they belong to
- **Admin lockout prevention**: Multiple safeguards prevent accidental lockout
- **Database seeded defaults**: Automatic creation of system groups and permissions

## Database Schema

### Permission Model

```python
class Permission:
    id: int                  # Primary key
    resource: str            # Resource type (e.g., "clients", "users", "ca")
    action: str              # Action type ("read", "create", "update", "delete", "download")
    description: str | None  # Human-readable description
```

**Unique constraint**: (resource, action)

### UserGroup Model (Extended)

```python
class UserGroup:
    id: int                      # Primary key
    name: str                    # Unique group name
    description: str | None      # Optional description
    is_admin: bool               # If True, group has all permissions automatically
    owner_user_id: int | None    # FK to users table
    created_at: datetime         # Creation timestamp
    updated_at: datetime         # Last update timestamp
    
    # Relationships
    owner: User                  # Group owner
    permissions: List[Permission] # Many-to-many with permissions
```

### Association Tables

- `user_group_memberships`: Maps users to groups (many-to-many)
- `user_group_permissions`: Maps groups to permissions (many-to-many)

## Default Permissions

The system seeds the following permissions on first migration:

| Resource | Actions | Description |
|----------|---------|-------------|
| `clients` | read, create, update, delete, download | Client management and config download |
| `groups` | read, create, update, delete | Nebula group management |
| `firewall_rules` | read, create, update, delete | Firewall rule management |
| `ip_pools` | read, create, update, delete | IP pool management |
| `ca` | read, create, delete, download | Certificate authority management |
| `users` | read, create, update, delete | User management |
| `lighthouse` | read, update | Lighthouse settings |
| `dashboard` | read | Dashboard and statistics viewing |

## Default User Groups

Two system groups are automatically created:

### Administrators Group
- **Name**: "Administrators"
- **is_admin**: True
- **Permissions**: All (automatically inherited)
- **Cannot be**: Deleted, or have is_admin changed to False

### Users Group
- **Name**: "Users"
- **is_admin**: False
- **Permissions**: Read-only access to all resources
- **Can be**: Modified or deleted (but be careful!)

## API Endpoints

All endpoints require authentication. Most require `users:read`, `users:create`, or `users:update` permissions.

### Permissions

#### GET /api/v1/permissions
List all available permissions in the system.

**Response**: `PermissionResponse[]`
```json
[
  {
    "id": 1,
    "resource": "clients",
    "action": "read",
    "description": "View client information"
  }
]
```

### User Groups

#### GET /api/v1/user-groups
List all user groups with member and permission counts.

**Response**: `UserGroupResponse[]`
```json
[
  {
    "id": 1,
    "name": "Administrators",
    "description": "Full system administrators",
    "is_admin": true,
    "owner": {"id": 1, "email": "admin@example.com"},
    "created_at": "2025-11-15T00:00:00",
    "updated_at": "2025-11-15T00:00:00",
    "member_count": 2,
    "permission_count": 28
  }
]
```

#### GET /api/v1/user-groups/{id}
Get detailed information about a specific user group.

#### POST /api/v1/user-groups
Create a new user group.

**Request**: `UserGroupCreate`
```json
{
  "name": "Developers",
  "description": "Development team members",
  "is_admin": false
}
```

#### PUT /api/v1/user-groups/{id}
Update a user group. Cannot change `is_admin` on Administrators group.

**Request**: `UserGroupUpdate`
```json
{
  "description": "Updated description"
}
```

#### DELETE /api/v1/user-groups/{id}
Delete a user group. Cannot delete Administrators group.

### Group Membership

#### GET /api/v1/user-groups/{id}/members
List all members of a user group.

**Response**: `UserResponse[]`

#### POST /api/v1/user-groups/{id}/members?user_id={user_id}
Add a user to a group.

**Query Param**: `user_id` - ID of user to add

**Response**: 
```json
{
  "status": "added",
  "user_id": 5,
  "group_id": 2
}
```

#### DELETE /api/v1/user-groups/{id}/members/{user_id}
Remove a user from a group. Cannot remove last admin from Administrators group.

### Group Permissions

#### GET /api/v1/user-groups/{id}/permissions
List all permissions granted to a group. For admin groups, returns all permissions.

**Response**: `PermissionResponse[]`

#### POST /api/v1/user-groups/{id}/permissions
Grant a permission to a group. Ignored for admin groups (they already have all).

**Request**: `PermissionGrantRequest`
```json
{
  "resource": "clients",
  "action": "create"
}
```

Or:
```json
{
  "permission_id": 5
}
```

#### DELETE /api/v1/user-groups/{id}/permissions/{permission_id}
Revoke a permission from a group. Cannot revoke from admin groups.

## Permission Checking

### In Code

Use the `require_permission()` dependency factory:

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

### Legacy require_admin

The `require_admin` function still works but now checks if the user belongs to an admin group instead of checking the role:

```python
from app.core.auth import require_admin

@router.delete("/users/{id}")
async def delete_user(
    user_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    # User is guaranteed to be in an admin group
    ...
```

### User.has_permission() Method

Check permissions programmatically:

```python
# In async context
if await user.has_permission(session, "clients", "delete"):
    # User can delete clients
    await delete_client(...)
```

## Admin Lockout Prevention

The system includes multiple safeguards to prevent accidental admin lockout:

### 1. Cannot Delete Administrators Group
Attempting to delete the Administrators group returns 409 Conflict.

```bash
DELETE /api/v1/user-groups/1
→ 409 Conflict: "Cannot delete the Administrators group"
```

### 2. Cannot Change is_admin on Administrators Group
Attempting to set `is_admin=False` on the Administrators group returns 409 Conflict.

```bash
PUT /api/v1/user-groups/1
{"is_admin": false}
→ 409 Conflict: "Cannot remove admin status from Administrators group"
```

### 3. Cannot Remove Last Admin
Attempting to remove the last member from the Administrators group returns 409 Conflict.

```bash
DELETE /api/v1/user-groups/1/members/5
→ 409 Conflict: "Cannot remove the last administrator. Add another admin first."
```

### 4. Cannot Delete Last Admin User
Attempting to delete a user who is the last member of the Administrators group returns 409 Conflict.

```bash
DELETE /api/v1/users/5
→ 409 Conflict: "Cannot delete the last administrator. Add another admin first."
```

## Migration

The permission system is added via Alembic migration `f40acab05062_add_comprehensive_permissions_system`.

### To Apply

```bash
cd server
alembic upgrade head
```

### What the Migration Does

1. Creates `permissions` table
2. Adds `is_admin` and `updated_at` columns to `user_groups` table
3. Creates `user_group_permissions` association table
4. Seeds 28 default permissions
5. Creates Administrators and Users groups
6. Grants read permissions to Users group
7. Migrates existing admin users to Administrators group

## Usage Examples

### Create a New User Group

```python
# Via API
POST /api/v1/user-groups
{
  "name": "Developers",
  "description": "Development team",
  "is_admin": false
}
```

### Add Users to a Group

```python
# Add user 5 to Developers group (id=3)
POST /api/v1/user-groups/3/members?user_id=5
```

### Grant Permissions to a Group

```python
# Grant clients:create permission to Developers group
POST /api/v1/user-groups/3/permissions
{
  "resource": "clients",
  "action": "create"
}
```

### Check User Permissions in Code

```python
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

async def can_user_delete_clients(user: User, session: AsyncSession) -> bool:
    return await user.has_permission(session, "clients", "delete")
```

## Best Practices

### 1. Always Have Multiple Admins
Never have just one member in the Administrators group. Add at least 2-3 trusted users to prevent lockout.

### 2. Use Groups for Permissions
Don't modify individual users' permissions. Instead, create groups with appropriate permissions and add users to those groups.

### 3. Principle of Least Privilege
Grant only the permissions necessary for users to do their jobs. Start with read-only and add write permissions as needed.

### 4. Regular Audits
Periodically review:
- Who is in the Administrators group
- What permissions each group has
- Whether users still need their current group memberships

### 5. Test Permission Changes
Before modifying critical groups (like Administrators), test changes on a non-production environment first.

## Troubleshooting

### User Can't Access Resources

1. Check if user is in any groups: `GET /api/v1/users/{id}/groups`
2. Check group permissions: `GET /api/v1/user-groups/{group_id}/permissions`
3. Verify the user's has_permission() returns True for the resource+action

### Can't Delete a User

If deletion fails with 409, the user might be the last admin. Add another user to the Administrators group first, then try again.

### Permission Not Taking Effect

1. Verify the permission exists: `GET /api/v1/permissions`
2. Check if it's granted to the user's group(s)
3. For admin groups, they automatically have all permissions
4. Restart the application if needed (permissions are loaded from database)

## Future Enhancements

Possible future improvements to the system:

- [ ] Replace all `require_admin` calls with granular `require_permission` checks
- [ ] Add permission caching for better performance
- [ ] Add audit logging for permission changes
- [ ] Add UI for managing permissions in the frontend
- [ ] Add API endpoint to check current user's permissions
- [ ] Add support for time-limited permissions
- [ ] Add support for per-resource permissions (e.g., user can only edit their own clients)

## See Also

- [API Documentation](API_DOCUMENTATION.md)
- [Database Schema](server/app/models/)
- [Migration Files](server/alembic/versions/)
- [Manual Test Results](server/tests/test_permissions_manual.md)
