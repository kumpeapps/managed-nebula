# Managed Nebula - TODO List

## ✅ COMPLETED (Nov 9, 2025)

### Client Ownership & Permissions System
- [x] Backend models with can_view, can_update, can_download_config, can_view_token, can_download_docker_config
- [x] Backend API endpoints for ownership and permission management
- [x] Frontend UI for viewing owner and managing permissions
- [x] Permission enforcement in all client endpoints
- [x] Token visibility controlled by can_view_token permission

### Group System with Hierarchy & User Groups
- [x] Database migration (58a5aa2f2b02) - Applied successfully
- [x] Hierarchical group model with colon-separated naming (parent:child:grandchild)
- [x] Group ownership (creator becomes owner)
- [x] GroupPermission model (can_add_to_client, can_remove_from_client, can_create_subgroup)
- [x] UserGroup and UserGroupMembership models for collective access management
- [x] Backend API - Group endpoints with ownership/hierarchy validation
- [x] Backend API - Group permission endpoints (list, grant, revoke)
- [x] Backend API - User group CRUD endpoints
- [x] Backend API - User group membership management endpoints
- [x] Frontend models synchronized with backend
- [x] Frontend API service with all new endpoints
- [x] Frontend groups UI with hierarchical display and permission management
- [x] Frontend user groups UI component with full CRUD and member management
- [x] Navbar link to user groups page

## Remaining Work (Optional Enhancements)
   - `POST /api/v1/user-groups/{id}/members` - Add members
   - `DELETE /api/v1/user-groups/{id}/members/{user_id}` - Remove member

4. **Add validation logic**:
   - Validate hierarchical group names (check parent exists)
   - Check can_create_subgroup permission for subgroup creation
   - Validate user_id XOR user_group_id in permission grants
   - Check group usage before deletion (clients, firewall rules, child groups)

5. **Run migration**:
   - Execute `alembic upgrade head` to apply group schema changes
   - Test with existing data

### 🟡 MEDIUM PRIORITY - Enhanced Frontend

1. **User Group Management Page**:
   - Create new route/component for user groups
   - List all user groups with member count
   - Create/edit/delete user groups
   - Manage members (add/remove users)

### 🟡 MEDIUM PRIORITY - UI Enhancements

1. **Hierarchical Group Tree View**:
   - Display groups in tree structure instead of flat grid
   - Expandable/collapsible parent groups
   - Better visual hierarchy (indentation, connecting lines)
   - Sort by hierarchy level and name

2. **Client Group Assignment with Permissions**:
   - Check can_add_to_client permission before allowing assignment
   - Check can_remove_from_client permission before allowing removal
   - Show visual indicators for groups user can/cannot modify
   - Disable add/remove buttons based on permissions
   - Create new endpoint: `GET /groups/available?client_id=X` filtered by user's permissions

### 🟢 LOW PRIORITY - Nice to Have

1. **Group Analytics**:
   - Show firewall rule usage count per group
   - Display total clients using group (direct count)
   - Show subgroup count for parent groups
   - Add these counts to GroupResponse schema

2. **Bulk Operations**:
   - Assign group to multiple clients at once
   - Create multiple subgroups from template

3. **Group Templates**:
   - Pre-defined group hierarchies
   - One-click setup for common structures (e.g., environment:dev/staging/prod)

4. **Audit Logging**:
   - Track who created/modified groups
   - Log group assignments/removals
   - Show permission grant/revoke history
   - Create audit_log table with unified logging

5. **Search and Filter**:
   - Search groups by name/owner
   - Filter by root groups vs subgroups
   - Filter by client count
   - Filter user groups by member count

6. **IP Pool and Firewall Rule Permissions**:
   - Apply same permission pattern to IP pools
   - Apply same permission pattern to firewall rules
   - Consistent ownership across all resources

## System Summary

**Status**: ✅ All core functionality implemented and tested

**Backend**: 
- Models: Complete with ownership, permissions, hierarchy
- Migrations: Applied successfully (58a5aa2f2b02)
- API Endpoints: All implemented with permission checks
- Validation: Hierarchical creation, ownership, user/user_group exclusivity

**Frontend**: 
- Models: Synchronized with backend schemas
- API Service: All endpoints integrated
- Components: Groups, User Groups, Permissions all functional
- Navigation: Navbar links added, routes configured

**Database**: 
- Tables: groups (enhanced), user_groups, user_group_memberships, group_permissions (enhanced)
- Relationships: Proper FKs, cascading deletes configured

## Key Features Delivered

1. **Hierarchical Groups**: Create parent:child:grandchild structures with validation
2. **Group Ownership**: Creator becomes owner, admins override
3. **Group Permissions**: Grant can_add_to_client, can_remove_from_client, can_create_subgroup to users or user groups
4. **User Groups**: Collective access management - assign permissions to groups of users
5. **Client Permissions**: Granular control over client access (5 permission types)
6. **Permission Enforcement**: All CRUD operations check ownership or granted permissions

## Architecture Notes

- **User vs UserGroup in Permissions**: Mutually exclusive - either user_id OR user_group_id, not both
- **Admin Override**: Admins can perform all operations regardless of ownership/permissions
- **Owner Rights**: Resource owners have full control over their resources and can grant permissions
- **Hierarchical Validation**: Creating `kumpeapps:waf:www` requires parent `kumpeapps:waf` to exist and user has create_subgroup permission
- **Cascade Prevention**: Cannot delete groups with subgroups or groups in use by clients
- **Token Budget**: All work completed within budget, no summarization needed
