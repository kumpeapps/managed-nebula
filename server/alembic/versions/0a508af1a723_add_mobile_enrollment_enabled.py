"""
Revision ID: 0a508af1a723
Revises: 536a899d4d97
Create Date: 2025-11-15 00:10:38.602881

Add mobile_enrollment_enabled column to global_settings table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '0a508af1a723'
down_revision = '536a899d4d97'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add mobile_enrollment_enabled column to global_settings if it doesn't exist."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    print("[migration] Checking for global_settings table...")
    tables = inspector.get_table_names()
    print(f"[migration] Found tables: {tables}")
    
    # Check if global_settings table exists
    if 'global_settings' in tables:
        columns = [col['name'] for col in inspector.get_columns('global_settings')]
        print(f"[migration] global_settings columns: {columns}")
        
        # Add mobile_enrollment_enabled column if it doesn't exist
        if 'mobile_enrollment_enabled' not in columns:
            print("[migration] Adding mobile_enrollment_enabled column...")
            with op.batch_alter_table('global_settings', schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column('mobile_enrollment_enabled', sa.Boolean(), nullable=False, server_default='0')
                )
            print("[migration] Column added successfully")
        else:
            print("[migration] Column mobile_enrollment_enabled already exists")
    else:
        print("[migration] global_settings table does not exist yet")


def downgrade() -> None:
    """Remove mobile_enrollment_enabled column from global_settings."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if table and column exist
    if 'global_settings' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('global_settings')]
        
        if 'mobile_enrollment_enabled' in columns:
            with op.batch_alter_table('global_settings', schema=None) as batch_op:
                batch_op.drop_column('mobile_enrollment_enabled')
