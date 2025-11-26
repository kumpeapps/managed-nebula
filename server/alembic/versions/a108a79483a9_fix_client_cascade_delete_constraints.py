"""fix_client_cascade_delete_constraints

Revision ID: a108a79483a9
Revises: 46f243d294ec
Create Date: 2025-11-18 00:09:40.035967

Fixes foreign key constraints on client_certificates, client_tokens, and ip_assignments
to include ON DELETE CASCADE. This resolves issue #55 where deleting a client fails with
IntegrityError due to remaining child records.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a108a79483a9'
down_revision = '46f243d294ec'
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
    """Add ON DELETE CASCADE to client foreign keys
    
    For SQLite: Uses batch mode recreate which handles FK constraints automatically
    For MySQL/PostgreSQL: Drops and recreates foreign key constraints
    """
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    if dialect_name == 'sqlite':
        # SQLite: batch_alter_table with recreate='always' will copy data and
        # recreate tables with proper FKs. We don't need to drop constraints explicitly.
        # Just ensure the table is recreated with proper FKs matching the model definition.
        
        # The recreate='always' option tells Alembic to:
        # 1. Create a temp table with the new schema (CASCADE FKs from model)
        # 2. Copy data from old table to temp table
        # 3. Drop old table
        # 4. Rename temp table to original name
        
        # Since our models already have ondelete='CASCADE', the recreated tables will have it.
        # We just need to trigger the recreation.
        with op.batch_alter_table('client_certificates', schema=None, recreate='always') as batch_op:
            pass  # Recreation happens automatically
        
        with op.batch_alter_table('client_tokens', schema=None, recreate='always') as batch_op:
            pass  # Recreation happens automatically
        
        with op.batch_alter_table('ip_assignments', schema=None, recreate='always') as batch_op:
            pass  # Recreation happens automatically
    else:
        # MySQL/PostgreSQL: Can alter constraints directly
        with op.batch_alter_table('client_certificates', schema=None) as batch_op:
            batch_op.drop_constraint('client_certificates_ibfk_1', type_='foreignkey')
            batch_op.create_foreign_key(
                'client_certificates_ibfk_1',
                'clients',
                ['client_id'],
                ['id'],
                ondelete='CASCADE'
            )
        
        with op.batch_alter_table('client_tokens', schema=None) as batch_op:
            batch_op.drop_constraint('client_tokens_ibfk_1', type_='foreignkey')
            batch_op.create_foreign_key(
                'client_tokens_ibfk_1',
                'clients',
                ['client_id'],
                ['id'],
                ondelete='CASCADE'
            )
        
        with op.batch_alter_table('ip_assignments', schema=None) as batch_op:
            batch_op.drop_constraint('ip_assignments_ibfk_1', type_='foreignkey')
            batch_op.create_foreign_key(
                'ip_assignments_ibfk_1',
                'clients',
                ['client_id'],
                ['id'],
                ondelete='CASCADE'
            )


def downgrade() -> None:
    """Remove ON DELETE CASCADE from client foreign keys
    
    Note: Downgrade is not easily supported for SQLite without recreating tables
    with modified FK constraints. Since the original schema already lacked CASCADE,
    this would require manual intervention.
    """
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    if dialect_name == 'sqlite':
        # SQLite downgrade is complex - would need to recreate tables without CASCADE
        # For now, we'll raise an error suggesting manual intervention
        raise NotImplementedError(
            "SQLite downgrade for FK constraint changes requires manual intervention. "
            "Please restore from backup or manually recreate the tables."
        )
    else:
        # MySQL/PostgreSQL: Remove CASCADE from constraints
        with op.batch_alter_table('ip_assignments', schema=None) as batch_op:
            batch_op.drop_constraint('ip_assignments_ibfk_1', type_='foreignkey')
            batch_op.create_foreign_key(
                'ip_assignments_ibfk_1',
                'clients',
                ['client_id'],
                ['id']
            )
        
        with op.batch_alter_table('client_tokens', schema=None) as batch_op:
            batch_op.drop_constraint('client_tokens_ibfk_1', type_='foreignkey')
            batch_op.create_foreign_key(
                'client_tokens_ibfk_1',
                'clients',
                ['client_id'],
                ['id']
            )
        
        with op.batch_alter_table('client_certificates', schema=None) as batch_op:
            batch_op.drop_constraint('client_certificates_ibfk_1', type_='foreignkey')
            batch_op.create_foreign_key(
                'client_certificates_ibfk_1',
                'clients',
                ['client_id'],
                ['id']
            )
