"""
Revision ID: 217d0bd7b984
Revises: ad6d47fa9bce
Create Date: 2025-11-26 15:15:43.499349
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '217d0bd7b984'
down_revision = 'ad6d47fa9bce'
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


def upgrade() -> None:
    # Add os_type column to clients table (idempotent)
    if not column_exists('clients', 'os_type'):
        op.add_column('clients', sa.Column('os_type', sa.String(20), nullable=False, server_default='docker'))


def downgrade() -> None:
    # Remove os_type column (idempotent)
    if column_exists('clients', 'os_type'):
        op.drop_column('clients', 'os_type')
