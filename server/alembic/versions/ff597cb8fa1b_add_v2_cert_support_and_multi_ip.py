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


def upgrade() -> None:
    # Get database connection to check for existing columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Add cert_version and nebula_version to ca_certificates
    ca_columns = {col['name'] for col in inspector.get_columns('ca_certificates')}
    if 'cert_version' not in ca_columns:
        op.add_column('ca_certificates', sa.Column('cert_version', sa.String(length=10), server_default='v1', nullable=False))
    if 'nebula_version' not in ca_columns:
        op.add_column('ca_certificates', sa.Column('nebula_version', sa.String(length=50), nullable=True))
        # Set nebula_version to 1.10.0 for all existing CAs
        op.execute("UPDATE ca_certificates SET nebula_version = '1.10.0' WHERE nebula_version IS NULL")
    
    # Add ip_version to clients
    client_columns = {col['name'] for col in inspector.get_columns('clients')}
    if 'ip_version' not in client_columns:
        op.add_column('clients', sa.Column('ip_version', sa.String(length=20), server_default='ipv4_only', nullable=False))
    
    # Add cert_version to client_certificates
    client_cert_columns = {col['name'] for col in inspector.get_columns('client_certificates')}
    if 'cert_version' not in client_cert_columns:
        op.add_column('client_certificates', sa.Column('cert_version', sa.String(length=10), server_default='v1', nullable=False))
    
    # Add ip_version and is_primary to ip_assignments
    ip_assignment_columns = {col['name'] for col in inspector.get_columns('ip_assignments')}
    if 'ip_version' not in ip_assignment_columns:
        op.add_column('ip_assignments', sa.Column('ip_version', sa.String(length=10), server_default='ipv4', nullable=False))
    if 'is_primary' not in ip_assignment_columns:
        op.add_column('ip_assignments', sa.Column('is_primary', sa.Boolean(), server_default='0', nullable=False))
        # Set existing IP assignments as primary IPv4 (only run once when column is first added)
        op.execute("UPDATE ip_assignments SET is_primary = 1, ip_version = 'ipv4'")
    
    # Add cert_version to global_settings
    global_settings_columns = {col['name'] for col in inspector.get_columns('global_settings')}
    if 'cert_version' not in global_settings_columns:
        op.add_column('global_settings', sa.Column('cert_version', sa.String(length=20), server_default='v1', nullable=False))


def downgrade() -> None:
    # Get database connection to check for existing columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Remove new columns only if they exist
    global_settings_columns = {col['name'] for col in inspector.get_columns('global_settings')}
    if 'cert_version' in global_settings_columns:
        op.drop_column('global_settings', 'cert_version')
    
    ip_assignment_columns = {col['name'] for col in inspector.get_columns('ip_assignments')}
    if 'is_primary' in ip_assignment_columns:
        op.drop_column('ip_assignments', 'is_primary')
    if 'ip_version' in ip_assignment_columns:
        op.drop_column('ip_assignments', 'ip_version')
    
    client_cert_columns = {col['name'] for col in inspector.get_columns('client_certificates')}
    if 'cert_version' in client_cert_columns:
        op.drop_column('client_certificates', 'cert_version')
    
    client_columns = {col['name'] for col in inspector.get_columns('clients')}
    if 'ip_version' in client_columns:
        op.drop_column('clients', 'ip_version')
    
    ca_columns = {col['name'] for col in inspector.get_columns('ca_certificates')}
    if 'nebula_version' in ca_columns:
        op.drop_column('ca_certificates', 'nebula_version')
    if 'cert_version' in ca_columns:
        op.drop_column('ca_certificates', 'cert_version')
