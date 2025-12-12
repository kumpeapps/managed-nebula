"""
Revision ID: ff597cb8fa1b
Revises: 217d0bd7b984
Create Date: 2025-12-05 00:40:15.923735
"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'ff597cb8fa1b'
down_revision = '217d0bd7b984'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    """Helper to check if a column exists in a table."""
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    """Add v2 certificate support and multi-IP columns (idempotent)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # ca_certificates
    if not _has_column(inspector, "ca_certificates", "cert_version"):
        op.add_column(
            "ca_certificates",
            sa.Column("cert_version", sa.String(length=10), server_default="v1", nullable=False),
        )
    
    nebula_added = False
    if not _has_column(inspector, "ca_certificates", "nebula_version"):
        nebula_added = True
        op.add_column(
            "ca_certificates",
            sa.Column("nebula_version", sa.String(length=50), nullable=True),
        )
    if nebula_added:
        op.execute(
            "UPDATE ca_certificates SET nebula_version = '1.10.0' WHERE nebula_version IS NULL"
        )
    
    # clients
    if not _has_column(inspector, "clients", "ip_version"):
        op.add_column(
            "clients",
            sa.Column("ip_version", sa.String(length=20), server_default="ipv4_only", nullable=False),
        )
    
    # client_certificates
    if not _has_column(inspector, "client_certificates", "cert_version"):
        op.add_column(
            "client_certificates",
            sa.Column("cert_version", sa.String(length=10), server_default="v1", nullable=False),
        )
    
    # ip_assignments
    ip_version_added = False
    if not _has_column(inspector, "ip_assignments", "ip_version"):
        ip_version_added = True
        op.add_column(
            "ip_assignments",
            sa.Column("ip_version", sa.String(length=10), server_default="ipv4", nullable=False),
        )
    
    is_primary_added = False
    if not _has_column(inspector, "ip_assignments", "is_primary"):
        is_primary_added = True
        op.add_column(
            "ip_assignments",
            sa.Column("is_primary", sa.Boolean(), server_default="0", nullable=False),
        )
    
    if ip_version_added or is_primary_added:
        op.execute("UPDATE ip_assignments SET is_primary = 1, ip_version = 'ipv4'")
    
    # global_settings
    if not _has_column(inspector, "global_settings", "cert_version"):
        op.add_column(
            "global_settings",
            sa.Column("cert_version", sa.String(length=20), server_default="v1", nullable=False),
        )


def downgrade() -> None:
    """Remove v2 certificate support and multi-IP columns (idempotent)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if _has_column(inspector, "global_settings", "cert_version"):
        op.drop_column("global_settings", "cert_version")
    
    if _has_column(inspector, "ip_assignments", "is_primary"):
        op.drop_column("ip_assignments", "is_primary")
    if _has_column(inspector, "ip_assignments", "ip_version"):
        op.drop_column("ip_assignments", "ip_version")
    
    if _has_column(inspector, "client_certificates", "cert_version"):
        op.drop_column("client_certificates", "cert_version")
    
    if _has_column(inspector, "clients", "ip_version"):
        op.drop_column("clients", "ip_version")
    
    if _has_column(inspector, "ca_certificates", "nebula_version"):
        op.drop_column("ca_certificates", "nebula_version")
    if _has_column(inspector, "ca_certificates", "cert_version"):
        op.drop_column("ca_certificates", "cert_version")
