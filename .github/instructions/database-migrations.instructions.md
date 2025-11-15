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
- **Make migrations idempotent**: Check if changes already exist before applying (see Idempotency section below)
- **Use parameter binding for data**: Never embed raw data strings in SQL (use `:param` syntax)
- **Use constants from code**: Import defaults from models, not duplicate them
- **Avoid hardcoded values**: Especially version numbers, config values that may change

### DON'Ts ❌
- ❌ Don't modify existing migration files after they've been applied
- ❌ Don't skip reviewing auto-generated migrations
- ❌ Don't create migrations that break existing data
- ❌ Don't forget to test downgrade path
- ❌ Don't make breaking changes without data migration
- ❌ Don't use raw SQL unless necessary (use Alembic operations)
- ❌ Don't apply migrations directly on production without testing
- ❌ Don't delete migration files that have been deployed
- ❌ Don't hardcode version numbers in default data (e.g., `version: '3.8'` in docker-compose templates)
- ❌ Don't embed multi-line strings with quotes directly in SQL - use parameter binding
- ❌ Don't duplicate constants - import from models/settings files

## Common Migration Patterns

### Making Migrations Idempotent (CRITICAL)
Migrations MUST be idempotent - they should be safe to run multiple times. This is essential because:
- Container restarts run migrations automatically via `entrypoint.sh`
- Database may already have some changes applied
- Rollback scenarios may require re-running migrations

#### Idempotent Column Addition
```python
def upgrade():
    """Idempotent migration - safe to run multiple times."""
    from sqlalchemy import text, inspect
    
    # Check if column already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('clients')]
    
    if 'status' not in columns:
        op.add_column('clients', sa.Column('status', sa.String(20), nullable=True))
    
    # Update with parameter binding (safe from SQL injection)
    conn.execute(
        text("UPDATE clients SET status = :default_status WHERE status IS NULL"),
        {"default_status": "active"}
    )
```

#### Idempotent Table Creation
```python
def upgrade():
    """Idempotent table creation."""
    from sqlalchemy import inspect
    
    # Check if table already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'enrollment_codes' not in tables:
        op.create_table('enrollment_codes',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('code', sa.String(length=64), nullable=False),
            # ... other columns ...
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_enrollment_codes_code', 'enrollment_codes', ['code'])
```

#### Idempotent Index Creation
```python
def upgrade():
    """Idempotent index creation."""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    indexes = [idx['name'] for idx in inspector.get_indexes('clients')]
    
    if 'ix_clients_name' not in indexes:
        op.create_index('ix_clients_name', 'clients', ['name'])
```

### Using Parameter Binding for Default Data (CRITICAL)
NEVER embed complex strings directly in SQL - always use parameter binding:

```python
# ❌ WRONG - SQL injection risk, quote escaping issues
def upgrade():
    op.execute("""
        UPDATE settings SET template = 'version: '3.8'
        services:
          app:
            image: myapp'
    """)

# ✅ CORRECT - Use parameter binding with conn.execute()
def upgrade():
    from sqlalchemy import text
    from ..models.settings import DEFAULT_TEMPLATE  # Import from code
    
    # Get connection from op.get_bind() to use parameter binding
    conn = op.get_bind()
    conn.execute(
        text("UPDATE settings SET template = :template WHERE template IS NULL"),
        {"template": DEFAULT_TEMPLATE}
    )
```

**Note**: `op.execute()` doesn't support parameter binding. Use `conn = op.get_bind()` and then `conn.execute()` with `text()` and parameters.

### Avoiding Hardcoded Configuration Values (CRITICAL)
Don't hardcode values that may change or are environment-specific:

```python
# ❌ WRONG - Hardcoded version number
DEFAULT_TEMPLATE = """version: '3.8'
services:
  app:
    image: myapp:1.0.0"""

# ✅ CORRECT - No version (Docker Compose v2+ doesn't require it)
# Import from models to maintain single source of truth
from ..models.settings import DEFAULT_DOCKER_COMPOSE_TEMPLATE

def upgrade():
    from sqlalchemy import text
    conn = op.get_bind()
    conn.execute(
        text("UPDATE global_settings SET docker_compose_template = :template WHERE docker_compose_template IS NULL"),
        {"template": DEFAULT_DOCKER_COMPOSE_TEMPLATE}
    )
```

### Adding a Non-Nullable Column
```python
def upgrade():
    # Step 1: Add column as nullable
    op.add_column('clients', sa.Column('status', sa.String(20), nullable=True))
    
    # Step 2: Set default value for existing rows using parameter binding
    from sqlalchemy import text
    conn = op.get_bind()
    conn.execute(
        text("UPDATE clients SET status = :status WHERE status IS NULL"),
        {"status": "active"}
    )
    
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

## Critical Checklist for Every Migration

Before committing ANY migration file, verify:

- [ ] **Idempotency**: Check if table/column/index exists before creating
  ```python
  from sqlalchemy import inspect
  conn = op.get_bind()
  inspector = inspect(conn)
  tables = inspector.get_table_names()
  if 'my_table' not in tables:
      # create table
  ```

- [ ] **Parameter Binding**: Use `conn.execute()` with `text()` and parameters, NOT `op.execute()` with embedded strings
  ```python
  conn = op.get_bind()
  conn.execute(text("UPDATE table SET col = :val"), {"val": value})
  ```

- [ ] **No Hardcoded Values**: Import constants from models, don't duplicate
  ```python
  from ..models.settings import DEFAULT_TEMPLATE  # ✅ Correct
  DEFAULT_TEMPLATE = "..."  # ❌ Wrong - duplicates code
  ```

- [ ] **No Version Numbers**: Don't hardcode version numbers in config templates
  ```python
  # ❌ Wrong
  template = """version: '3.8'
  services: ..."""
  
  # ✅ Correct
  template = """services:
    ..."""  # Docker Compose v2+ doesn't need version
  ```

- [ ] **Test Locally**: Run migration twice to ensure idempotency
  ```bash
  docker compose restart server  # Should succeed without errors
  ```

## Resources
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://www.sqlalchemy.org/)
- [Alembic Cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html)
- [Database Migration Best Practices](https://www.sqlalchemy.org/library.html#migration)
