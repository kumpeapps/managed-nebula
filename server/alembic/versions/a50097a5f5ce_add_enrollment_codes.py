"""add_enrollment_codes_table

Adds the enrollment_codes table for Mobile Nebula device enrollment.

Revision ID: a50097a5f5ce
Revises: fd03ead652bc
Create Date: 2025-11-13 21:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a50097a5f5ce'
down_revision = 'fd03ead652bc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect
    
    # Check if table already exists (idempotent)
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'enrollment_codes' not in tables:
        # Create enrollment_codes table
        op.create_table('enrollment_codes',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('code', sa.String(length=64), nullable=False),
            sa.Column('client_id', sa.Integer(), nullable=False),
            sa.Column('device_name', sa.String(length=255), nullable=True),
            sa.Column('device_id', sa.String(length=255), nullable=True),
            sa.Column('platform', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('used_at', sa.DateTime(), nullable=True),
            sa.Column('is_used', sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code')
        )
        op.create_index(op.f('ix_enrollment_codes_code'), 'enrollment_codes', ['code'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_enrollment_codes_code'), table_name='enrollment_codes')
    op.drop_table('enrollment_codes')
