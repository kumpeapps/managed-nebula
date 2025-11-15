"""add_missing_rbac_permissions

Adds missing permissions for ip_groups, user_groups, and settings resources.

Revision ID: 2790ea32864b
Revises: f40acab05062
Create Date: 2025-11-15 17:30:34.675898
"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '2790ea32864b'
down_revision = 'f40acab05062'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing permissions
    conn = op.get_bind()
    
    missing_permissions = [
        # IP Groups permissions (separate from IP Pools)
        ('ip_groups', 'read', 'View IP groups'),
        ('ip_groups', 'create', 'Create IP groups'),
        ('ip_groups', 'update', 'Update IP groups'),
        ('ip_groups', 'delete', 'Delete IP groups'),
        
        # User Groups permissions (for managing user groups themselves)
        ('user_groups', 'read', 'View user groups'),
        ('user_groups', 'create', 'Create user groups'),
        ('user_groups', 'update', 'Update user groups'),
        ('user_groups', 'delete', 'Delete user groups'),
        ('user_groups', 'manage_members', 'Add/remove members from user groups'),
        ('user_groups', 'manage_permissions', 'Assign/revoke permissions to user groups'),
        
        # Settings permissions
        ('settings', 'read', 'View system settings'),
        ('settings', 'update', 'Update system settings'),
        ('settings', 'docker_compose', 'Manage Docker Compose templates'),
    ]
    
    for resource, action, description in missing_permissions:
        # Check if permission already exists to avoid duplicate key errors
        result = conn.execute(
            sa.text("SELECT id FROM permissions WHERE resource = :resource AND action = :action"),
            {"resource": resource, "action": action}
        ).fetchone()
        
        if not result:
            conn.execute(
                sa.text("INSERT INTO permissions (resource, action, description) VALUES (:resource, :action, :description)"),
                {"resource": resource, "action": action, "description": description}
            )
    
    # Grant read permissions for new resources to the default "Users" group
    users_group_result = conn.execute(sa.text("SELECT id FROM user_groups WHERE name = 'Users'")).fetchone()
    
    if users_group_result:
        users_group_id = users_group_result[0]
        
        # Grant read-only access for new resources
        read_resources = ['ip_groups', 'user_groups', 'settings']
        for resource in read_resources:
            perm_result = conn.execute(
                sa.text("SELECT id FROM permissions WHERE resource = :resource AND action = 'read'"),
                {"resource": resource}
            ).fetchone()
            
            if perm_result:
                perm_id = perm_result[0]
                # Check if already granted
                existing = conn.execute(
                    sa.text("SELECT 1 FROM user_group_permissions WHERE user_group_id = :group_id AND permission_id = :perm_id"),
                    {"group_id": users_group_id, "perm_id": perm_id}
                ).fetchone()
                
                if not existing:
                    conn.execute(
                        sa.text("INSERT INTO user_group_permissions (user_group_id, permission_id) VALUES (:group_id, :perm_id)"),
                        {"group_id": users_group_id, "perm_id": perm_id}
                    )


def downgrade() -> None:
    # Remove the added permissions
    conn = op.get_bind()
    
    resources_to_remove = ['ip_groups', 'user_groups', 'settings']
    for resource in resources_to_remove:
        conn.execute(
            sa.text("DELETE FROM permissions WHERE resource = :resource"),
            {"resource": resource}
        )
