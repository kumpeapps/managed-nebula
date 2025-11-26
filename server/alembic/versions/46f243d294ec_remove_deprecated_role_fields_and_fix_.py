"""remove_deprecated_role_fields_and_fix_timestamps

Remove deprecated Role model and role_id column from users table.
Add server_default=func.now() to all created_at timestamp fields.

Revision ID: 46f243d294ec
Revises: 2790ea32864b
Create Date: 2025-11-16 05:23:37.433043
"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '46f243d294ec'
down_revision = '2790ea32864b'
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
    # Remove role_id column from users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('role_id')
    
    # Drop roles table
    op.drop_index('ix_roles_name', table_name='roles')
    op.drop_table('roles')
    
    # Add server_default to created_at columns for all tables
    # Note: SQLite doesn't support ALTER COLUMN, so we use batch mode
    # For other databases, this will work directly
    
    # Users table - already has created_at, just update default
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=sa.text('CURRENT_TIMESTAMP'),
                              existing_nullable=False)
    
    # Groups table
    with op.batch_alter_table('groups', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=sa.text('CURRENT_TIMESTAMP'),
                              existing_nullable=False)
    
    # Clients table
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=sa.text('CURRENT_TIMESTAMP'),
                              existing_nullable=False)
    
    # Client tokens table
    with op.batch_alter_table('client_tokens', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=sa.text('CURRENT_TIMESTAMP'),
                              existing_nullable=False)
    
    # Client certificates table
    with op.batch_alter_table('client_certificates', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=sa.text('CURRENT_TIMESTAMP'),
                              existing_nullable=False)
    
    # CA certificates table
    with op.batch_alter_table('ca_certificates', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=sa.text('CURRENT_TIMESTAMP'),
                              existing_nullable=False)
    
    # User groups table
    with op.batch_alter_table('user_groups', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=sa.text('CURRENT_TIMESTAMP'),
                              existing_nullable=False)
        batch_op.alter_column('updated_at',
                              existing_type=sa.DateTime(),
                              server_default=sa.text('CURRENT_TIMESTAMP'),
                              existing_nullable=False)
    
    # User group memberships table
    with op.batch_alter_table('user_group_memberships', schema=None) as batch_op:
        batch_op.alter_column('added_at',
                              existing_type=sa.DateTime(),
                              server_default=sa.text('CURRENT_TIMESTAMP'),
                              existing_nullable=False)


def downgrade() -> None:
    # Recreate roles table
    if not table_exists('roles'):

        op.create_table('roles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)
    
    # Add role_id column back to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('users_role_id_fkey', 'roles', ['role_id'], ['id'], ondelete='SET NULL')
    
    # Remove server_default from created_at columns
    # (This is optional - leaving server_default doesn't break anything)
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=None,
                              existing_nullable=False)
    
    with op.batch_alter_table('groups', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=None,
                              existing_nullable=False)
    
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=None,
                              existing_nullable=False)
    
    with op.batch_alter_table('client_tokens', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=None,
                              existing_nullable=False)
    
    with op.batch_alter_table('client_certificates', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=None,
                              existing_nullable=False)
    
    with op.batch_alter_table('ca_certificates', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=None,
                              existing_nullable=False)
    
    with op.batch_alter_table('user_groups', schema=None) as batch_op:
        batch_op.alter_column('created_at',
                              existing_type=sa.DateTime(),
                              server_default=None,
                              existing_nullable=False)
        batch_op.alter_column('updated_at',
                              existing_type=sa.DateTime(),
                              server_default=None,
                              existing_nullable=False)
    
    with op.batch_alter_table('user_group_memberships', schema=None) as batch_op:
        batch_op.alter_column('added_at',
                              existing_type=sa.DateTime(),
                              server_default=None,
                              existing_nullable=False)
