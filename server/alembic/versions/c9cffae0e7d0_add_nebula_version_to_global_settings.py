"""
Revision ID: c9cffae0e7d0
Revises: ff597cb8fa1b
Create Date: 2025-12-04 20:28:00.578290
"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'c9cffae0e7d0'
down_revision = 'ff597cb8fa1b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get database connection to check for existing columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Add nebula_version to global_settings
    global_settings_columns = {col['name'] for col in inspector.get_columns('global_settings')}
    if 'nebula_version' not in global_settings_columns:
        # Use 1.10.0 as the DB default to align with runtime defaults and ensure v2 capability
        op.add_column(
            'global_settings',
            sa.Column(
                'nebula_version',
                sa.String(length=50),
                server_default='1.10.0',
                nullable=False,
            ),
        )
        # Set nebula_version to 1.10.0 for existing installations to allow v2 support
        op.execute("UPDATE global_settings SET nebula_version = '1.10.0'")


def downgrade() -> None:
    # Get database connection to check for existing columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Remove nebula_version from global_settings only if it exists
    global_settings_columns = {col['name'] for col in inspector.get_columns('global_settings')}
    if 'nebula_version' in global_settings_columns:
        op.drop_column('global_settings', 'nebula_version')
