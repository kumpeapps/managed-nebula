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


def upgrade() -> None:
    # Add version tracking columns to clients table
    op.add_column('clients', sa.Column('client_version', sa.String(length=50), nullable=True))
    op.add_column('clients', sa.Column('nebula_version', sa.String(length=50), nullable=True))
    op.add_column('clients', sa.Column('last_version_report_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove version tracking columns from clients table
    op.drop_column('clients', 'last_version_report_at')
    op.drop_column('clients', 'nebula_version')
    op.drop_column('clients', 'client_version')
