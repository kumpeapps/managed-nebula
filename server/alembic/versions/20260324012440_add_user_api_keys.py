"""add user_api_keys table

Revision ID: 20260324012440
Revises: e9b13c6295f5
Create Date: 2026-03-24 01:24:40.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260324012440'
down_revision = 'e9b13c6295f5'
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
    """Create user_api_keys table for API key authentication."""
    
    # Only create table if it doesn't exist
    if not table_exists('user_api_keys'):
        op.create_table(
            'user_api_keys',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('key_hash', sa.String(length=255), nullable=False),
            sa.Column('key_prefix', sa.String(length=20), nullable=False),
            sa.Column('scopes', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), default=True, server_default='1', nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('last_used_at', sa.DateTime(), nullable=True),
            sa.Column('usage_count', sa.Integer(), default=0, server_default='0', nullable=False),
        )
        
        # Create index on user_id for efficient lookups
        op.create_index('ix_user_api_keys_user_id', 'user_api_keys', ['user_id'])
        
        # Create unique index on key_hash for authentication
        op.create_index('ix_user_api_keys_key_hash', 'user_api_keys', ['key_hash'], unique=True)
        
        # Create index on key_prefix for preview/listing
        op.create_index('ix_user_api_keys_key_prefix', 'user_api_keys', ['key_prefix'])


def downgrade() -> None:
    """Drop user_api_keys table."""
    
    # Drop indexes first if they exist
    if index_exists('user_api_keys', 'ix_user_api_keys_key_prefix'):
        op.drop_index('ix_user_api_keys_key_prefix', table_name='user_api_keys')
    
    if index_exists('user_api_keys', 'ix_user_api_keys_key_hash'):
        op.drop_index('ix_user_api_keys_key_hash', table_name='user_api_keys')
    
    if index_exists('user_api_keys', 'ix_user_api_keys_user_id'):
        op.drop_index('ix_user_api_keys_user_id', table_name='user_api_keys')
    
    # Drop table if it exists
    if table_exists('user_api_keys'):
        op.drop_table('user_api_keys')
