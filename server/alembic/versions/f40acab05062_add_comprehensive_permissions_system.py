"""Add comprehensive permissions system

Creates Permission model and extends UserGroup with is_admin and permissions.
Seeds default permissions and creates default Administrators and Users groups.

Revision ID: f40acab05062
Revises: 202511132147
Create Date: 2025-11-15 04:07:04.058457
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'f40acab05062'
down_revision = '202511132147'
branch_labels = None
depends_on = None


def table_exists(table_name):
    """Check if a table exists in the database."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    if not table_exists(table_name):
        return False
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name, index_name):
    """Check if an index exists on a table."""
    if not table_exists(table_name):
        return False
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)



def upgrade() -> None:
    # Create permissions table
    # For SQLite compatibility, we'll use String instead of Enum
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create unique index on resource + action
    op.create_index('ix_permissions_resource_action', 'permissions', ['resource', 'action'], unique=True)
    
    # Add new columns to user_groups table
    if not column_exists('user_groups', 'is_admin'):
        op.add_column('user_groups', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'))
    if not column_exists('user_groups', 'updated_at'):
        # SQLite doesn't support server_default with functions in ALTER TABLE
        # Add as nullable, set defaults manually, then rely on application-level defaults
        op.add_column('user_groups', sa.Column('updated_at', sa.DateTime(), nullable=True))
        # Set default value for existing rows
        op.execute(sa.text("UPDATE user_groups SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"))
    
    # Create user_group_permissions association table
    op.create_table(
        'user_group_permissions',
        sa.Column('user_group_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_group_id'], ['user_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_group_id', 'permission_id')
    )
    
    # Seed default permissions
    conn = op.get_bind()
    
    permissions_data = [
        # Clients permissions
        ('clients', 'read', 'View client information'),
        ('clients', 'create', 'Create new clients'),
        ('clients', 'update', 'Update client settings'),
        ('clients', 'delete', 'Delete clients'),
        ('clients', 'download', 'Download client configurations'),
        
        # Groups permissions (Nebula groups, not user groups)
        ('groups', 'read', 'View Nebula groups'),
        ('groups', 'create', 'Create new Nebula groups'),
        ('groups', 'update', 'Update Nebula groups'),
        ('groups', 'delete', 'Delete Nebula groups'),
        
        # Firewall rules permissions
        ('firewall_rules', 'read', 'View firewall rules'),
        ('firewall_rules', 'create', 'Create firewall rules'),
        ('firewall_rules', 'update', 'Update firewall rules'),
        ('firewall_rules', 'delete', 'Delete firewall rules'),
        
        # IP pools permissions
        ('ip_pools', 'read', 'View IP pools'),
        ('ip_pools', 'create', 'Create IP pools'),
        ('ip_pools', 'update', 'Update IP pools'),
        ('ip_pools', 'delete', 'Delete IP pools'),
        
        # CA permissions
        ('ca', 'read', 'View certificate authorities'),
        ('ca', 'create', 'Create certificate authorities'),
        ('ca', 'delete', 'Delete certificate authorities'),
        ('ca', 'download', 'Download CA certificates'),
        
        # Users permissions
        ('users', 'read', 'View users'),
        ('users', 'create', 'Create new users'),
        ('users', 'update', 'Update user settings'),
        ('users', 'delete', 'Delete users'),
        
        # Lighthouse permissions
        ('lighthouse', 'read', 'View lighthouse settings'),
        ('lighthouse', 'update', 'Update lighthouse settings'),
        
        # Dashboard permissions
        ('dashboard', 'read', 'View dashboard and statistics'),
    ]
    
    for resource, action, description in permissions_data:
        conn.execute(
            sa.text("INSERT INTO permissions (resource, action, description) VALUES (:resource, :action, :description)"),
            {"resource": resource, "action": action, "description": description}
        )
    
    # Create default user groups
    now = datetime.utcnow().isoformat()
    
    # Create Administrators group (is_admin=True)
    conn.execute(
        sa.text("INSERT INTO user_groups (name, description, is_admin, created_at, updated_at) VALUES (:name, :desc, :is_admin, :created, :updated)"),
        {
            "name": "Administrators",
            "desc": "Full system administrators with all permissions",
            "is_admin": True,
            "created": now,
            "updated": now
        }
    )
    
    # Create Users group with basic read permissions
    conn.execute(
        sa.text("INSERT INTO user_groups (name, description, is_admin, created_at, updated_at) VALUES (:name, :desc, :is_admin, :created, :updated)"),
        {
            "name": "Users",
            "desc": "Standard users with read-only access",
            "is_admin": False,
            "created": now,
            "updated": now
        }
    )
    
    # Grant basic read permissions to Users group
    # Get the Users group ID and read permission IDs
    users_group_result = conn.execute(sa.text("SELECT id FROM user_groups WHERE name = 'Users'"))
    users_group_id = users_group_result.fetchone()[0]
    
    read_permissions = conn.execute(sa.text("SELECT id FROM permissions WHERE action = 'read'"))
    for perm_row in read_permissions:
        conn.execute(
            sa.text("INSERT INTO user_group_permissions (user_group_id, permission_id) VALUES (:group_id, :perm_id)"),
            {"group_id": users_group_id, "perm_id": perm_row[0]}
        )
    
    # Migrate existing admin users to Administrators group
    admins_group_result = conn.execute(sa.text("SELECT id FROM user_groups WHERE name = 'Administrators'"))
    admins_group_id = admins_group_result.fetchone()[0]
    
    # Get all admin users (users with role_id pointing to admin role)
    admin_role_result = conn.execute(sa.text("SELECT id FROM roles WHERE name = 'admin'"))
    admin_role_row = admin_role_result.fetchone()
    
    if admin_role_row:
        admin_role_id = admin_role_row[0]
        admin_users = conn.execute(
            sa.text("SELECT id FROM users WHERE role_id = :role_id"),
            {"role_id": admin_role_id}
        )
        
        for user_row in admin_users:
            user_id = user_row[0]
            # Check if membership already exists
            existing = conn.execute(
                sa.text("SELECT id FROM user_group_memberships WHERE user_id = :user_id AND user_group_id = :group_id"),
                {"user_id": user_id, "group_id": admins_group_id}
            ).fetchone()
            
            if not existing:
                conn.execute(
                    sa.text("INSERT INTO user_group_memberships (user_id, user_group_id, added_at) VALUES (:user_id, :group_id, :added_at)"),
                    {"user_id": user_id, "group_id": admins_group_id, "added_at": now}
                )


def downgrade() -> None:
    # Drop association table
    op.drop_table('user_group_permissions')
    
    # Remove added columns from user_groups
    op.drop_column('user_groups', 'updated_at')
    op.drop_column('user_groups', 'is_admin')
    
    # Drop permissions table
    op.drop_index('ix_permissions_resource_action', table_name='permissions')
    op.drop_table('permissions')
    
    # Drop enum type (PostgreSQL only, SQLite ignores this)
    op.execute("DROP TYPE IF EXISTS permissionaction")
