"""
Revision ID: ad6d47fa9bce
Revises: fbea1f1aa652
Create Date: 2025-11-23 18:16:39.757659
"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'ad6d47fa9bce'
down_revision = 'fbea1f1aa652'
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
    # Add version tracking columns to clients table
    if not column_exists('clients', 'client_version'):

        op.add_column('clients', sa.Column('client_version', sa.String(length=50), nullable=True))
    if not column_exists('clients', 'nebula_version'):

        op.add_column('clients', sa.Column('nebula_version', sa.String(length=50), nullable=True))
    if not column_exists('clients', 'last_version_report_at'):

        op.add_column('clients', sa.Column('last_version_report_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove version tracking columns from clients table
    op.drop_column('clients', 'last_version_report_at')
    op.drop_column('clients', 'nebula_version')
    op.drop_column('clients', 'client_version')
