"""Add revoked_certificates table for persistent revocation tracking

Revision ID: 20260328182643
Revises: 20260324120000
Create Date: 2026-03-28 18:26:43
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260328182643'
down_revision = '20260324120000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create revoked_certificates table for persistent revocation tracking (idempotent)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if table already exists
    if "revoked_certificates" not in inspector.get_table_names():
        op.create_table(
            "revoked_certificates",
            sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
            sa.Column("fingerprint", sa.String(length=128), nullable=False),
            sa.Column("client_id", sa.Integer(), nullable=True),
            sa.Column("client_name", sa.String(length=100), nullable=True),
            sa.Column("not_after", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("revoked_reason", sa.String(length=255), nullable=True),
            sa.Column("revoked_by_user_id", sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        )
        
        # Create unique index on fingerprint
        op.create_index(
            "ix_revoked_certificates_fingerprint",
            "revoked_certificates",
            ["fingerprint"],
            unique=True
        )
        
        # Migrate existing revoked certificates to new table
        # This ensures historical revocations are preserved
        # Use COALESCE to handle null revoked_at (should not happen but fail-safe)
        conn.execute(sa.text("""
            INSERT INTO revoked_certificates (fingerprint, client_id, client_name, not_after, revoked_at, revoked_reason)
            SELECT 
                cc.fingerprint,
                cc.client_id,
                c.name,
                cc.not_after,
                COALESCE(cc.revoked_at, cc.created_at, CURRENT_TIMESTAMP),
                'migrated_from_client_certificates'
            FROM client_certificates cc
            JOIN clients c ON c.id = cc.client_id
            WHERE cc.revoked = TRUE 
                AND cc.fingerprint IS NOT NULL
                AND cc.fingerprint != ''
        """))


def downgrade() -> None:
    """Remove revoked_certificates table (idempotent)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Drop index if exists
    indexes = inspector.get_indexes("revoked_certificates") if "revoked_certificates" in inspector.get_table_names() else []
    if any(idx["name"] == "ix_revoked_certificates_fingerprint" for idx in indexes):
        op.drop_index("ix_revoked_certificates_fingerprint", table_name="revoked_certificates")
    
    # Drop table if exists
    if "revoked_certificates" in inspector.get_table_names():
        op.drop_table("revoked_certificates")
