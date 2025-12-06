"""
Revision ID: 9708b2369ee5
Revises: c9cffae0e7d0
Create Date: 2025-12-05 18:41:44.681440
"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '9708b2369ee5'
down_revision = 'c9cffae0e7d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add issued_for_all_ips column to client_certificates table (idempotent)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if column exists before adding
    columns = {col['name'] for col in inspector.get_columns('client_certificates')}
    if 'issued_for_all_ips' not in columns:
        op.add_column('client_certificates', 
            sa.Column('issued_for_all_ips', sa.String(512), nullable=True)
        )


def downgrade() -> None:
    # Remove issued_for_all_ips column (idempotent)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if column exists before dropping
    columns = {col['name'] for col in inspector.get_columns('client_certificates')}
    if 'issued_for_all_ips' in columns:
        op.drop_column('client_certificates', 'issued_for_all_ips')
