# Enhanced Group System - Technical Specification

## Overview

The group system has been refactored to support:
1. **Hierarchical groups** with colon-separated namespacing (`parent:child:grandchild`)
2. **Group ownership** - Creator becomes owner
3. **Granular permissions** - Add to client, remove from client, create subgroups
4. **User groups** - Collections of users for collective access management
5. **Multi-level access control** - Permissions can be granted to individual users or user groups

## Database Schema

### Groups Table (`groups`)
- `id` - Primary key
- `name` - Hierarchical name (e.g., `kumpeapps:waf:www`) - VARCHAR(255)
- `owner_user_id` - Foreign key to users.id
- `created_at` - Timestamp

### User Groups Table (`user_groups`)
- `id` - Primary key
- `name` - User group name (e.g., "Engineering Team")
- `description` - Optional description
- `owner_user_id` - Foreign key to users.id
- `created_at` - Timestamp

### User Group Memberships (`user_group_memberships`)
- `id` - Primary key
- `user_id` - Foreign key to users.id
- `user_group_id` - Foreign key to user_groups.id
- `added_at` - Timestamp

### Group Permissions (`group_permissions`)
- `id` - Primary key
- `group_id` - Foreign key to groups.id
- `user_id` - Foreign key to users.id (nullable)
- `user_group_id` - Foreign key to user_groups.id (nullable)
- `can_add_to_client` - Boolean (can assign group to clients)
- `can_remove_from_client` - Boolean (can remove group from clients)
- `can_create_subgroup` - Boolean (can create child groups)

**Note**: Either `user_id` OR `user_group_id` must be set, not both.

## Hierarchical Group System

### Naming Convention
Groups use colon (`:`) as a hierarchy separator:
- `kumpeapps` - Root level group
- `kumpeapps:waf` - Subgroup of kumpeapps
- `kumpeapps:waf:www` - Subgroup of kumpeapps:waf

### Creation Rules
1. Root groups can be created by any user (becomes owner)
2. Subgroups require `can_create_subgroup` permission on parent
3. Parent group must exist before creating subgroup
4. Validation ensures hierarchical integrity

### Examples
```
User creates: "kumpeapps"
  → User becomes owner
  → User automatically gets all permissions on this group

User with can_create_subgroup on "kumpeapps" creates: "kumpeapps:waf"
  → New group created
  → Creator becomes owner of the new subgroup

User without permission tries to create "kumpeapps:monitoring"
  → Error: Need can_create_subgroup permission on "kumpeapps"
```

## Permission System

### Permission Types

1. **`can_add_to_client`**
   - Allows user to add this group to any client
   - Default: True for owner
   - Use case: Team lead can assign team group to new clients

2. **`can_remove_from_client`**
   - Allows user to remove this group from clients
   - Default: False (even for owner unless explicitly granted)
   - Use case: Security team can revoke access groups

3. **`can_create_subgroup`**
   - Allows user to create child groups under this group
   - Default: False
   - Use case: Department head can create team-specific subgroups

### Access Hierarchy

```
Admin
  └─ Full access to all groups

Group Owner
  └─ Full access to their group
      └─ Can grant permissions to others

User with permissions (direct)
  └─ Permissions as granted

User Group with permissions
  └─ All members inherit permissions
```

### Permission Inheritance
- Permissions are **NOT automatically inherited** down the hierarchy
- `kumpeapps` permission does NOT grant access to `kumpeapps:waf`
- Each level must be explicitly granted
- This allows fine-grained control (e.g., access to parent but not sensitive subgroups)

## User Groups

### Purpose
User groups allow collective access management:
- Grant permission once to user group
- All members automatically have that permission
- Add/remove users from group to grant/revoke access
- Simplifies management for teams/departments

### Use Cases

**Engineering Team User Group**:
- Members: alice@example.com, bob@example.com, charlie@example.com
- Granted permissions:
  - can_add_to_client on group "production"
  - can_add_to_client on group "staging"
- All members can now add production/staging groups to clients

**Security Team User Group**:
- Members: security1@example.com, security2@example.com
- Granted permissions:
  - can_remove_from_client on group "public"
  - can_add_to_client on group "restricted"
- All members can manage security-related group assignments

## API Endpoints

### Groups
- `GET /api/v1/groups` - List all groups (filtered by access)
- `GET /api/v1/groups/{id}` - Get group details
- `POST /api/v1/groups` - Create group (checks parent permissions for subgroups)
- `PUT /api/v1/groups/{id}` - Update group (owner/admin only)
- `DELETE /api/v1/groups/{id}` - Delete group (owner/admin only, checks for usage)

### Group Permissions
- `GET /api/v1/groups/{id}/permissions` - List permissions (owner/admin)
- `POST /api/v1/groups/{id}/permissions` - Grant permission (owner/admin)
- `DELETE /api/v1/groups/{id}/permissions/{perm_id}` - Revoke permission (owner/admin)

### User Groups
- `GET /api/v1/user-groups` - List user groups
- `POST /api/v1/user-groups` - Create user group
- `PUT /api/v1/user-groups/{id}` - Update user group
- `DELETE /api/v1/user-groups/{id}` - Delete user group
- `GET /api/v1/user-groups/{id}/members` - List members
- `POST /api/v1/user-groups/{id}/members` - Add members
- `DELETE /api/v1/user-groups/{id}/members/{user_id}` - Remove member

## Frontend Features

### Group Management UI
- Tree view showing hierarchical groups
- Visual indicator for subgroups (indentation, icons)
- Create button checks parent permissions
- Ownership display
- Permission management per group

### User Group Management
- List user groups with member count
- Add/remove members
- Assign permissions to user groups
- View effective permissions per user (direct + inherited from user groups)

## Validation Rules

1. **Group Creation**:
   - Name cannot be empty
   - For subgroups: parent must exist
   - For subgroups: user must have `can_create_subgroup` on parent (or be admin)
   - Name must be unique (case-sensitive)

2. **Permission Grants**:
   - Must specify either user_id OR user_group_id, not both
   - User/user group must exist
   - Grantor must be owner or admin

3. **Group Deletion**:
   - Check if used by clients (prevent deletion)
   - Check if used in firewall rules (prevent deletion)
   - Check if has child groups (prevent deletion or cascade)

## Migration Path

Existing groups remain unchanged but gain new fields:
- `owner_user_id` - Set to NULL initially (can be claimed by admin)
- `created_at` - Set to migration timestamp
- Old `can_assign` permission renamed to `can_add_to_client`

## Future Enhancements

1. **Permission inheritance option** - Allow opt-in inheritance down hierarchy
2. **Group templates** - Pre-defined subgroup structures
3. **Bulk operations** - Apply groups to multiple clients at once
4. **Audit logging** - Track who added/removed groups from clients
5. **Group descriptions** - Add metadata to groups
6. **Auto-assignment rules** - Automatically add groups based on client properties
