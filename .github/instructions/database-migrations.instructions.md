---
applies_to:
  - "server/alembic/**"
  - "**/alembic.ini"
  - "server/alembic/env.py"
  - "server/alembic/versions/*.py"
---

# Database Migrations (Alembic) Instructions

## Overview
Managed Nebula uses Alembic for database schema versioning and migrations. This ensures database changes are tracked, reversible, and can be applied consistently across environments.

## Alembic Basics

### Migration Files Location
- **Config**: `server/alembic.ini`
- **Environment**: `server/alembic/env.py`
- **Versions**: `server/alembic/versions/`
- **Models**: `server/app/models/models.py` (SQLAlchemy models)

### Database Support
Alembic works with all supported databases:
- SQLite (default for development)
- PostgreSQL (recommended for production)
- MySQL (alternative for production)

## CRITICAL: Idempotent Migrations

**ALL migrations MUST be idempotent** - they must be safe to run multiple times without errors.

### Why Idempotent Migrations Matter
- Prevents failures when migrations are accidentally run multiple times
- Allows safe migration reruns during development and testing
- Essential for CI/CD pipelines and automated deployments
- Protects against data corruption from duplicate operations

### Required Pattern for All Migrations

**ALWAYS** use SQLAlchemy inspector to check if schema elements exist before adding or dropping them:

```python
def upgrade() -> None:
    # Get database connection and inspector
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if column exists before adding
    columns = {col['name'] for col in inspector.get_columns('table_name')}
    if 'new_column' not in columns:
        op.add_column('table_name', sa.Column('new_column', sa.String(50)))
    
    # Check if table exists before creating
    tables = inspector.get_table_names()
    if 'new_table' not in tables:
        op.create_table(
            'new_table',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(100))
        )
    
    # Check if index exists before creating
    indexes = {idx['name'] for idx in inspector.get_indexes('table_name')}
    if 'idx_name' not in indexes:
        op.create_index('idx_name', 'table_name', ['column_name'])

def downgrade() -> None:
    # Get database connection and inspector
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if index exists before dropping
    indexes = {idx['name'] for idx in inspector.get_indexes('table_name')}
    if 'idx_name' in indexes:
        op.drop_index('idx_name', table_name='table_name')
    
    # Check if table exists before dropping
    tables = inspector.get_table_names()
    if 'new_table' in tables:
        op.drop_table('new_table')
    
    # Check if column exists before dropping
    columns = {col['name'] for col in inspector.get_columns('table_name')}
    if 'new_column' in columns:
        op.drop_column('table_name', 'new_column')
```

### Checking Different Schema Elements

```python
# Columns
columns = {col['name'] for col in inspector.get_columns('table_name')}
if 'column_name' not in columns:
    # Add column
if 'column_name' in columns:
    # Drop column

# Tables
tables = inspector.get_table_names()
if 'table_name' not in tables:
    # Create table
if 'table_name' in tables:
    # Drop table

# Indexes
indexes = {idx['name'] for idx in inspector.get_indexes('table_name')}
if 'index_name' not in indexes:
    # Create index
if 'index_name' in indexes:
    # Drop index

# Foreign Keys
fks = {fk['name'] for fk in inspector.get_foreign_keys('table_name')}
if 'fk_name' not in fks:
    # Create FK
if 'fk_name' in fks:
    # Drop FK

# Unique Constraints
uqs = {uq['name'] for uq in inspector.get_unique_constraints('table_name')}
if 'uq_name' not in uqs:
    # Create unique constraint
if 'uq_name' in uqs:
    # Drop unique constraint
```

## Common Commands

### Applying Migrations
```bash
# In development (local)
cd server
alembic upgrade head

# In Docker container
docker exec -it nebula-server bash -c "cd /app && alembic upgrade head"
docker-compose exec server alembic upgrade head

# Upgrade to specific version
alembic upgrade abc123
```

### Creating New Migrations
```bash
# Auto-generate migration from model changes
cd server
alembic revision --autogenerate -m "add user_groups table"

# Create empty migration (for data migrations or custom SQL)
alembic revision -m "migrate existing data"

# Review generated migration file before applying!
# File will be in server/alembic/versions/
```

### Migration History
```bash
# Show current version
alembic current

# Show all migrations
alembic history

# Show verbose history with details
alembic history --verbose

# Show what would be upgraded
alembic upgrade head --sql
```

### Downgrading (Reverting)
```bash
# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade abc123

# Downgrade to beginning
alembic downgrade base
```

## Migration File Structure

### Auto-Generated Migration Example
```python
"""add user_groups table

Revision ID: abc123def456
Revises: previous_revision
Create Date: 2024-01-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'abc123def456'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None

def upgrade():
    """Apply migration."""
    op.create_table(
        'user_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_user_groups_name', 'user_groups', ['name'])

def downgrade():
    """Revert migration."""
    op.drop_index('ix_user_groups_name', table_name='user_groups')
    op.drop_table('user_groups')
```

## Creating Migrations

### When to Create Migrations
Create a migration when you:
- Add a new table (model)
- Add a column to existing table
- Remove a column
- Change column type or constraints
- Add or remove indexes
- Add or remove foreign keys
- Rename tables or columns

### Workflow for Model Changes
1. **Update SQLAlchemy models** in `server/app/models/models.py`
2. **Generate migration**: `alembic revision --autogenerate -m "description"`
3. **Review generated file**: Check in `server/alembic/versions/`
4. **Edit if needed**: Alembic doesn't catch everything
5. **Test migration**: Apply on development database
6. **Test downgrade**: Ensure reversibility works
7. **Commit migration file**: Include in version control

### Example: Adding a New Column
```python
# 1. Update model in app/models/models.py
class Client(Base):
    __tablename__ = "clients"
    # ... existing columns ...
    last_seen_at = Column(DateTime, nullable=True)  # New column

# 2. Generate migration
# $ alembic revision --autogenerate -m "add last_seen_at to clients"

# 3. Review generated file
def upgrade():
    op.add_column('clients', sa.Column('last_seen_at', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('clients', 'last_seen_at')

# 4. Apply migration
# $ alembic upgrade head
```

### Example: Data Migration
```python
"""migrate client groups to new format

Revision ID: abc123
Revises: previous
Create Date: 2024-01-15 10:30:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = 'abc123'
down_revision = 'previous'

def upgrade():
    # Define table structure for migration
    clients = table('clients',
        column('id', sa.Integer),
        column('groups_old', sa.String),
        column('groups_new', sa.JSON)
    )
    
    # Use connection to execute data migration
    conn = op.get_bind()
    results = conn.execute(sa.select(clients.c.id, clients.c.groups_old))
    
    for client_id, groups_old in results:
        if groups_old:
            # Convert comma-separated string to JSON array
            groups_array = groups_old.split(',')
            conn.execute(
                clients.update()
                .where(clients.c.id == client_id)
                .values(groups_new=groups_array)
            )

def downgrade():
    # Reverse the migration
    clients = table('clients',
        column('id', sa.Integer),
        column('groups_old', sa.String),
        column('groups_new', sa.JSON)
    )
    
    conn = op.get_bind()
    results = conn.execute(sa.select(clients.c.id, clients.c.groups_new))
    
    for client_id, groups_new in results:
        if groups_new:
            groups_string = ','.join(groups_new)
            conn.execute(
                clients.update()
                .where(clients.c.id == client_id)
                .values(groups_old=groups_string)
            )
```

## Best Practices

### DO's ✅
- **Always review auto-generated migrations**: Alembic doesn't catch everything
- **Test migrations on dev database first**: Never run untested migrations on production
- **Test both upgrade and downgrade**: Ensure reversibility works
- **Keep migrations small and focused**: One logical change per migration
- **Use descriptive names**: Name should explain what the migration does
- **Include data migrations when needed**: Don't just modify schema
- **Commit migration files**: Always version control migrations
- **Document complex migrations**: Add comments explaining non-obvious logic
- **Handle nullable constraints carefully**: Add column as nullable first, populate data, then make not-nullable if needed

### DON'Ts ❌
- ❌ Don't modify existing migration files after they've been applied
- ❌ Don't skip reviewing auto-generated migrations
- ❌ Don't create migrations that break existing data
- ❌ Don't forget to test downgrade path
- ❌ Don't make breaking changes without data migration
- ❌ Don't use raw SQL unless necessary (use Alembic operations)
- ❌ Don't apply migrations directly on production without testing
- ❌ Don't delete migration files that have been deployed

## Common Migration Patterns

### Adding a Non-Nullable Column
```python
def upgrade():
    # Step 1: Add column as nullable
    op.add_column('clients', sa.Column('status', sa.String(20), nullable=True))
    
    # Step 2: Set default value for existing rows
    op.execute("UPDATE clients SET status = 'active' WHERE status IS NULL")
    
    # Step 3: Make column non-nullable
    op.alter_column('clients', 'status', nullable=False)
```

### Renaming a Column
```python
def upgrade():
    # Preferred: Use batch mode for SQLite compatibility
    with op.batch_alter_table('clients') as batch_op:
        batch_op.alter_column('old_name', new_column_name='new_name')

def downgrade():
    with op.batch_alter_table('clients') as batch_op:
        batch_op.alter_column('new_name', new_column_name='old_name')
```

### Adding Foreign Key
```python
def upgrade():
    op.create_foreign_key(
        'fk_clients_owner_user',
        'clients', 'users',
        ['owner_user_id'], ['id'],
        ondelete='CASCADE'
    )

def downgrade():
    op.drop_constraint('fk_clients_owner_user', 'clients', type_='foreignkey')
```

### Adding Index
```python
def upgrade():
    op.create_index('ix_clients_name', 'clients', ['name'])
    
    # Partial index (PostgreSQL)
    op.create_index(
        'ix_clients_active',
        'clients',
        ['name'],
        postgresql_where=sa.text('is_blocked = false')
    )

def downgrade():
    op.drop_index('ix_clients_name', table_name='clients')
    op.drop_index('ix_clients_active', table_name='clients')
```

### Enum Type Changes (PostgreSQL)
```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

def upgrade():
    # Create new enum type
    status_enum = ENUM('active', 'inactive', 'suspended', name='client_status', create_type=True)
    status_enum.create(op.get_bind())
    
    # Add column with enum type
    op.add_column('clients', sa.Column('status', status_enum, nullable=True))

def downgrade():
    op.drop_column('clients', 'status')
    # Drop enum type
    ENUM(name='client_status').drop(op.get_bind())
```

## Troubleshooting

### Migration Conflicts
```bash
# Multiple branches created migrations with same parent
# Alembic will detect this and show error

# Solution: Merge migrations
alembic merge heads -m "merge branches"

# This creates a new migration that references both branches
```

### Locked Tables (SQLite)
```python
# SQLite doesn't support ALTER TABLE for some operations
# Use batch mode:

def upgrade():
    with op.batch_alter_table('clients') as batch_op:
        batch_op.add_column(sa.Column('new_field', sa.String(50)))
        batch_op.create_index('ix_new_field', ['new_field'])
```

### Migration Already Applied
```bash
# If migration file exists but not in version table
# Mark as applied without running:
alembic stamp abc123

# Or stamp to head (latest):
alembic stamp head
```

### Rollback Failed Migration
```bash
# 1. Check current version
alembic current

# 2. If migration partially applied, manually fix database
# Connect to database and fix schema

# 3. Stamp to previous version
alembic stamp previous_version

# 4. Fix migration file
# Edit the migration file to fix issues

# 5. Try again
alembic upgrade head
```

## Production Deployment

### Pre-Deployment Checklist
- [ ] Review all new migration files
- [ ] Test migrations on staging database with production data copy
- [ ] Test downgrade path
- [ ] Ensure migrations don't lock tables for extended periods
- [ ] Plan for rollback if needed
- [ ] Backup database before migration
- [ ] Schedule maintenance window if needed

### Deployment Steps
```bash
# 1. Backup database
pg_dump -h localhost -U postgres managed_nebula > backup.sql

# 2. Apply migrations
docker exec nebula-server alembic upgrade head

# 3. Verify application starts
docker logs nebula-server

# 4. If issues, rollback
docker exec nebula-server alembic downgrade -1
# Or restore from backup
psql -h localhost -U postgres managed_nebula < backup.sql
```

### Zero-Downtime Migrations
For large tables or high-traffic systems:

```python
def upgrade():
    # 1. Add new column as nullable
    op.add_column('clients', sa.Column('new_field', sa.String(50), nullable=True))
    
    # 2. Deploy application code that populates new_field
    # (Don't make migration dependent on app deployment)
    
    # In next migration after backfill complete:
    # 3. Make column non-nullable
    # 4. Remove old column
```

## Environment Configuration

### alembic.ini
```ini
[alembic]
script_location = alembic
sqlalchemy.url = driver://user:pass@localhost/dbname  # Overridden by env.py

# Template for new migrations
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(slug)s

# Logging
[loggers]
keys = root,sqlalchemy,alembic

[logger_alembic]
level = INFO
handlers =
qualname = alembic
```

### env.py
Managed Nebula's `env.py` uses runtime database URL:

```python
from app.db import get_database_url
from app.models.models import Base

config.set_main_option('sqlalchemy.url', get_database_url())
target_metadata = Base.metadata
```

## Testing Migrations

### Unit Testing Migrations
```python
import pytest
from alembic import command
from alembic.config import Config

@pytest.fixture
def alembic_config():
    config = Config('alembic.ini')
    config.set_main_option('sqlalchemy.url', 'sqlite:///:memory:')
    return config

def test_migrations_up_and_down(alembic_config):
    """Test that all migrations can upgrade and downgrade."""
    # Upgrade to head
    command.upgrade(alembic_config, 'head')
    
    # Downgrade one step
    command.downgrade(alembic_config, '-1')
    
    # Upgrade back to head
    command.upgrade(alembic_config, 'head')
```

## Resources
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://www.sqlalchemy.org/)
- [Alembic Cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html)
- [Database Migration Best Practices](https://www.sqlalchemy.org/library.html#migration)
