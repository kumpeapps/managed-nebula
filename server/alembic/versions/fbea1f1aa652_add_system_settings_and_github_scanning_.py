"""
add_system_settings_and_github_scanning_tables

Revision ID: fbea1f1aa652
Revises: a108a79483a9
Create Date: 2025-11-22 04:17:29.409218
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'fbea1f1aa652'
down_revision = 'a108a79483a9'
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
    # Create system_settings table only if it doesn't exist
    if not table_exists('system_settings'):
        op.create_table(
            'system_settings',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('key', sa.String(length=100), nullable=False),
            sa.Column('value', sa.Text(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('updated_by_user_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('key')
        )
    
    # Create index only if it doesn't exist
    if not index_exists('system_settings', 'ix_system_settings_key'):
        op.create_index('ix_system_settings_key', 'system_settings', ['key'])
    
    # Create github_secret_scanning_logs table only if it doesn't exist
    if not table_exists('github_secret_scanning_logs'):
        op.create_table(
            'github_secret_scanning_logs',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('action', sa.String(length=20), nullable=False),
            sa.Column('token_preview', sa.String(length=12), nullable=False),
            sa.Column('github_url', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('client_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # Seed default settings only if table was just created or settings don't exist
    # Check if settings already exist to avoid duplicate key errors
    bind = op.get_bind()
    result = bind.execute(sa.text("SELECT COUNT(*) FROM system_settings WHERE `key` IN ('token_prefix', 'github_webhook_secret')"))
    count = result.scalar()
    
    if count == 0:
        op.execute(
            sa.text(
                "INSERT INTO system_settings (`key`, value, updated_at) VALUES "
                "('token_prefix', 'mnebula_', :now), "
                "('github_webhook_secret', '', :now)"
            ).bindparams(now=datetime.utcnow())
        )


def downgrade() -> None:
    # Drop tables in reverse order only if they exist
    if table_exists('github_secret_scanning_logs'):
        op.drop_table('github_secret_scanning_logs')
    
    if index_exists('system_settings', 'ix_system_settings_key'):
        op.drop_index('ix_system_settings_key', table_name='system_settings')
    
    if table_exists('system_settings'):
        op.drop_table('system_settings')
