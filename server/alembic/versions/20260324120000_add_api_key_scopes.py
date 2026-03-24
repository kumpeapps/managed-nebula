"""add_api_key_scopes

Revision ID: 20260324120000
Revises: 20260324012440
Create Date: 2026-03-24 12:00:00.000000

Adds scope restrictions and client tracking for API keys:
- Association table for API key <-> Group restrictions
- Association table for API key <-> IPPool restrictions  
- restrict_to_created_clients flag on API keys
- parent_key_id for tracking key regeneration lineage
- created_by_api_key_id on clients for tracking creation source
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260324120000'
down_revision: Union[str, None] = '20260324012440'
branch_labels: Union[str, Sequence[str], None] = None


def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists."""
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    inspector = sa.inspect(conn)
    if not table_exists(conn, table_name):
        return False
    columns = {col['name'] for col in inspector.get_columns(table_name)}
    return column_name in columns


def index_exists(conn, table_name: str, index_name: str) -> bool:
    """Check if an index exists."""
    inspector = sa.inspect(conn)
    if not table_exists(conn, table_name):
        return False
    indexes = {idx['name'] for idx in inspector.get_indexes(table_name)}
    return index_name in indexes


def foreign_key_exists(conn, table_name: str, fk_name: str) -> bool:
    """Check if a foreign key constraint exists on a table."""
    inspector = sa.inspect(conn)
    if not table_exists(conn, table_name):
        return False
    fkeys = {fk['name'] for fk in inspector.get_foreign_keys(table_name) if fk.get('name')}
    return fk_name in fkeys


def upgrade() -> None:
    conn = op.get_bind()
    
    # Create api_key_groups association table
    if not table_exists(conn, 'api_key_groups'):
        op.create_table(
            'api_key_groups',
            sa.Column('api_key_id', sa.Integer(), nullable=False),
            sa.Column('group_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['api_key_id'], ['user_api_keys.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('api_key_id', 'group_id')
        )
    
    # Create api_key_ip_pools association table
    if not table_exists(conn, 'api_key_ip_pools'):
        op.create_table(
            'api_key_ip_pools',
            sa.Column('api_key_id', sa.Integer(), nullable=False),
            sa.Column('ip_pool_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['api_key_id'], ['user_api_keys.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['ip_pool_id'], ['ip_pools.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('api_key_id', 'ip_pool_id')
        )
    
    # Add restrict_to_created_clients column to user_api_keys
    if not column_exists(conn, 'user_api_keys', 'restrict_to_created_clients'):
        op.add_column(
            'user_api_keys',
            sa.Column('restrict_to_created_clients', sa.Boolean(), nullable=False, server_default='0')
        )
    
    # Add parent_key_id column to user_api_keys for tracking regeneration
    if not column_exists(conn, 'user_api_keys', 'parent_key_id'):
        op.add_column(
            'user_api_keys',
            sa.Column('parent_key_id', sa.Integer(), nullable=True)
        )
        # Add foreign key constraint if table has data
        if table_exists(conn, 'user_api_keys'):
            try:
                op.create_foreign_key(
                    'fk_user_api_keys_parent_key_id',
                    'user_api_keys',
                    'user_api_keys',
                    ['parent_key_id'],
                    ['id'],
                    ondelete='SET NULL'
                )
            except Exception:
                # Constraint may already exist
                pass
    
    # Add created_by_api_key_id column to clients
    if not column_exists(conn, 'clients', 'created_by_api_key_id'):
        op.add_column(
            'clients',
            sa.Column('created_by_api_key_id', sa.Integer(), nullable=True)
        )
        # Add foreign key constraint
        if table_exists(conn, 'clients') and table_exists(conn, 'user_api_keys'):
            try:
                op.create_foreign_key(
                    'fk_clients_created_by_api_key_id',
                    'clients',
                    'user_api_keys',
                    ['created_by_api_key_id'],
                    ['id'],
                    ondelete='SET NULL'
                )
            except Exception:
                # Constraint may already exist
                pass
    
    # Add index on created_by_api_key_id for faster lookups
    if not index_exists(conn, 'clients', 'ix_clients_created_by_api_key_id'):
        op.create_index(
            'ix_clients_created_by_api_key_id',
            'clients',
            ['created_by_api_key_id']
        )


def downgrade() -> None:
    conn = op.get_bind()
    
    # Drop index
    if index_exists(conn, 'clients', 'ix_clients_created_by_api_key_id'):
        op.drop_index('ix_clients_created_by_api_key_id', table_name='clients')
    
    # Drop foreign keys before dropping columns (only if they exist)
    if foreign_key_exists(conn, 'clients', 'fk_clients_created_by_api_key_id'):
        op.drop_constraint('fk_clients_created_by_api_key_id', 'clients', type_='foreignkey')
    
    if foreign_key_exists(conn, 'user_api_keys', 'fk_user_api_keys_parent_key_id'):
        op.drop_constraint('fk_user_api_keys_parent_key_id', 'user_api_keys', type_='foreignkey')
    
    # Drop columns
    if column_exists(conn, 'clients', 'created_by_api_key_id'):
        op.drop_column('clients', 'created_by_api_key_id')
    
    if column_exists(conn, 'user_api_keys', 'parent_key_id'):
        op.drop_column('user_api_keys', 'parent_key_id')
    
    if column_exists(conn, 'user_api_keys', 'restrict_to_created_clients'):
        op.drop_column('user_api_keys', 'restrict_to_created_clients')
    
    # Drop association tables
    if table_exists(conn, 'api_key_ip_pools'):
        op.drop_table('api_key_ip_pools')
    
    if table_exists(conn, 'api_key_groups'):
        op.drop_table('api_key_groups')
