"""Add issued_by_ca_id to client_certificates for CA change detection

Revision ID: e9b13c6295f5
Revises: 9708b2369ee5
Create Date: 2025-12-07 20:41:30.945221

This migration adds the issued_by_ca_id column to track which CA issued each
client certificate. This enables automatic certificate re-issuance when the
signing CA changes (e.g., during CA rotation).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e9b13c6295f5'
down_revision = '9708b2369ee5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add issued_by_ca_id column to client_certificates table (idempotent)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if column already exists
    columns = {col['name'] for col in inspector.get_columns('client_certificates')}
    if 'issued_by_ca_id' not in columns:
        # Add the column
        op.add_column(
            'client_certificates',
            sa.Column(
                'issued_by_ca_id',
                sa.Integer(),
                sa.ForeignKey('ca_certificates.id', ondelete='SET NULL'),
                nullable=True
            )
        )
        
        # Create index for faster lookups
        op.create_index(
            'ix_client_certificates_issued_by_ca_id',
            'client_certificates',
            ['issued_by_ca_id'],
            unique=False
        )


def downgrade() -> None:
    """Remove issued_by_ca_id column from client_certificates table (idempotent)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if index exists
    indexes = {idx['name'] for idx in inspector.get_indexes('client_certificates')}
    if 'ix_client_certificates_issued_by_ca_id' in indexes:
        op.drop_index('ix_client_certificates_issued_by_ca_id', table_name='client_certificates')
    
    # Check if column exists
    columns = {col['name'] for col in inspector.get_columns('client_certificates')}
    if 'issued_by_ca_id' in columns:
        op.drop_column('client_certificates', 'issued_by_ca_id')
