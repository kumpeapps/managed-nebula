---
applies_to:
  - "**/test_*.py"
  - "**/tests/**"
  - "**/*.spec.ts"
  - "**/conftest.py"
---

# Testing Instructions

## Overview
This document outlines testing practices and patterns for the Managed Nebula project across all components (server, frontend, client).

## Testing Philosophy
- **Test meaningful behavior**: Focus on testing what users care about, not implementation details
- **Integration over unit**: Prefer integration tests that test multiple components together
- **No excessive mocking**: Use real databases and services when possible
- **Fast feedback**: Tests should run quickly to enable rapid iteration
- **Clear failures**: Test failures should clearly indicate what went wrong

## Server Testing (Python/pytest)

### Running Tests
```bash
cd server
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Skip tests requiring nebula-cert
pytest tests/ -m "not nebula_cert"

# Run specific test file
pytest tests/test_health.py -v

# Run specific test function
pytest tests/test_health.py::test_health_endpoint -v
```

### Test Structure
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.db import get_db

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

@pytest.fixture
async def db_session():
    """Async database session for testing."""
    # Setup test database
    async with get_test_db() as session:
        yield session
    # Cleanup happens automatically

def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

### Testing Patterns

#### Testing API Endpoints
```python
def test_create_client(client, admin_token):
    """Test creating a new client."""
    payload = {
        "name": "test-client",
        "is_lighthouse": False
    }
    
    response = client.post(
        "/api/v1/clients",
        json=payload,
        cookies={"session": admin_token}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-client"
    assert "id" in data
```

#### Testing Authentication
```python
def test_requires_authentication(client):
    """Test endpoint requires authentication."""
    response = client.get("/api/v1/clients")
    assert response.status_code == 401
    
def test_requires_admin(client, user_token):
    """Test endpoint requires admin role."""
    response = client.delete(
        "/api/v1/clients/1",
        cookies={"session": user_token}
    )
    assert response.status_code == 403
```

#### Testing Database Operations
```python
@pytest.mark.asyncio
async def test_create_and_fetch_client(db_session):
    """Test creating and fetching a client from database."""
    from app.models.models import Client
    from sqlalchemy import select
    
    # Create
    client = Client(name="test-client", is_lighthouse=False)
    db_session.add(client)
    await db_session.commit()
    await db_session.refresh(client)
    
    # Fetch
    result = await db_session.execute(
        select(Client).where(Client.name == "test-client")
    )
    fetched = result.scalar_one()
    
    assert fetched.id == client.id
    assert fetched.name == "test-client"
```

#### Skipping Tests Based on Dependencies
```python
import pytest
import shutil

@pytest.mark.skipif(
    shutil.which("nebula-cert") is None,
    reason="nebula-cert binary not found in PATH"
)
def test_certificate_generation():
    """Test certificate generation with nebula-cert."""
    # Test code that requires nebula-cert
    pass
```

#### Testing Error Cases
```python
def test_create_client_validation_error(client, admin_token):
    """Test validation error when creating client with invalid data."""
    payload = {
        "name": "",  # Invalid: empty name
        "is_lighthouse": False
    }
    
    response = client.post(
        "/api/v1/clients",
        json=payload,
        cookies={"session": admin_token}
    )
    
    assert response.status_code == 400
    assert "name" in response.json()["detail"]

def test_delete_nonexistent_client(client, admin_token):
    """Test deleting a client that doesn't exist."""
    response = client.delete(
        "/api/v1/clients/99999",
        cookies={"session": admin_token}
    )
    
    assert response.status_code == 404
```

### Common Test Fixtures
```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.main import app
from app.models.models import Base

@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

@pytest.fixture
async def admin_user(db_session):
    """Create admin user for testing."""
    from app.models.models import User, Role
    from app.core.auth import hash_password
    
    role = Role(name="admin")
    db_session.add(role)
    await db_session.commit()
    
    user = User(
        email="admin@test.com",
        password_hash=hash_password("password123"),
        role=role
    )
    db_session.add(user)
    await db_session.commit()
    
    return user
```

## Frontend Testing (Angular/Jasmine)

### Running Tests
```bash
cd frontend
npm test                  # Run tests in watch mode
npm run test:coverage     # Generate coverage report
npm run test:ci          # Single run (for CI)
```

### Test Structure
```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ClientListComponent } from './client-list.component';
import { ClientService } from '../../services/client.service';
import { of } from 'rxjs';

describe('ClientListComponent', () => {
  let component: ClientListComponent;
  let fixture: ComponentFixture<ClientListComponent>;
  let clientService: jasmine.SpyObj<ClientService>;

  beforeEach(async () => {
    const clientServiceSpy = jasmine.createSpyObj('ClientService', ['getClients']);

    await TestBed.configureTestingModule({
      imports: [ClientListComponent],
      providers: [
        { provide: ClientService, useValue: clientServiceSpy }
      ]
    }).compileComponents();

    clientService = TestBed.inject(ClientService) as jasmine.SpyObj<ClientService>;
    fixture = TestBed.createComponent(ClientListComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load clients on init', () => {
    const mockClients = [
      { id: 1, name: 'client1', is_lighthouse: false },
      { id: 2, name: 'client2', is_lighthouse: true }
    ];
    clientService.getClients.and.returnValue(of(mockClients));

    component.ngOnInit();

    expect(clientService.getClients).toHaveBeenCalled();
    expect(component.clients).toEqual(mockClients);
  });
});
```

### Testing Patterns

#### Testing Services
```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ClientService } from './client.service';

describe('ClientService', () => {
  let service: ClientService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ClientService]
    });
    service = TestBed.inject(ClientService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should fetch clients', () => {
    const mockClients = [{ id: 1, name: 'test' }];

    service.getClients().subscribe(clients => {
      expect(clients).toEqual(mockClients);
    });

    const req = httpMock.expectOne('/api/v1/clients');
    expect(req.request.method).toBe('GET');
    req.flush(mockClients);
  });
});
```

#### Testing Forms
```typescript
it('should validate client form', () => {
  const form = component.clientForm;
  
  // Initially invalid (empty)
  expect(form.valid).toBeFalsy();
  
  // Set valid values
  form.patchValue({
    name: 'test-client',
    is_lighthouse: false
  });
  
  expect(form.valid).toBeTruthy();
});

it('should show validation errors', () => {
  const nameControl = component.clientForm.get('name');
  
  // Empty name
  nameControl?.setValue('');
  expect(nameControl?.hasError('required')).toBeTruthy();
  
  // Name too short
  nameControl?.setValue('ab');
  expect(nameControl?.hasError('minlength')).toBeTruthy();
});
```

## Integration Testing

### End-to-End Workflow Tests
```python
def test_complete_client_lifecycle(client):
    """Test creating client, fetching config, updating, and deleting."""
    # 1. Create admin user
    admin_token = create_admin_and_login(client)
    
    # 2. Create CA
    ca_response = client.post(
        "/api/v1/ca",
        json={"name": "test-ca", "duration_days": 540},
        cookies={"session": admin_token}
    )
    assert ca_response.status_code == 200
    
    # 3. Create IP pool
    pool_response = client.post(
        "/api/v1/ip-pools",
        json={"name": "main-pool", "cidr": "10.100.0.0/16"},
        cookies={"session": admin_token}
    )
    assert pool_response.status_code == 200
    
    # 4. Create client
    client_response = client.post(
        "/api/v1/clients",
        json={"name": "test-client", "is_lighthouse": False},
        cookies={"session": admin_token}
    )
    assert client_response.status_code == 200
    client_id = client_response.json()["id"]
    
    # 5. Generate token
    token_response = client.post(
        f"/api/v1/clients/{client_id}/tokens",
        cookies={"session": admin_token}
    )
    assert token_response.status_code == 200
    token = token_response.json()["token"]
    
    # 6. Fetch config as client
    config_response = client.post(
        "/api/v1/client/config",
        json={"token": token, "public_key": "test-public-key"}
    )
    assert config_response.status_code == 200
    assert "config" in config_response.json()
    
    # 7. Update client
    update_response = client.put(
        f"/api/v1/clients/{client_id}",
        json={"name": "updated-client"},
        cookies={"session": admin_token}
    )
    assert update_response.status_code == 200
    
    # 8. Delete client
    delete_response = client.delete(
        f"/api/v1/clients/{client_id}",
        cookies={"session": admin_token}
    )
    assert delete_response.status_code == 200
```

## Test Data Management

### Using Factories
```python
from datetime import datetime

def create_test_user(db_session, email="test@example.com", is_admin=False):
    """Factory for creating test users."""
    from app.models.models import User, Role
    from app.core.auth import hash_password
    
    role_name = "admin" if is_admin else "user"
    role = Role(name=role_name)
    db_session.add(role)
    
    user = User(
        email=email,
        password_hash=hash_password("password123"),
        role=role,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    return user

def create_test_client(db_session, name="test-client", **kwargs):
    """Factory for creating test clients."""
    from app.models.models import Client
    
    client = Client(name=name, is_lighthouse=False, **kwargs)
    db_session.add(client)
    return client
```

## Best Practices

### DO's ✅
- **Test behavior, not implementation**: Focus on what the code does, not how
- **Use descriptive test names**: Name should describe what is being tested
- **Arrange-Act-Assert**: Structure tests clearly with setup, action, and verification
- **Test edge cases**: Test boundary conditions, empty inputs, large inputs
- **Test error paths**: Verify error handling works correctly
- **Keep tests independent**: Each test should be runnable in isolation
- **Use fixtures for common setup**: Avoid duplication with fixtures
- **Test async code properly**: Use `@pytest.mark.asyncio` for async tests

### DON'Ts ❌
- **Don't test framework code**: Don't test FastAPI or Angular internals
- **Don't mock excessively**: Prefer real implementations when possible
- **Don't test private methods**: Test public interfaces only
- **Don't make tests dependent**: Tests should not rely on execution order
- **Don't use hard-coded waits**: Use proper async patterns, not `time.sleep()`
- **Don't skip cleanup**: Always clean up test data and resources
- **Don't ignore flaky tests**: Fix or remove tests that fail randomly

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Test

on: [push, pull_request]

jobs:
  test-server:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd server
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd server
          pytest tests/ -v --cov=app

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm install
      - name: Run tests
        run: |
          cd frontend
          npm run test:ci
```

## Performance Testing
- Use pytest-benchmark for performance tests
- Test with realistic data volumes
- Monitor memory usage in long-running tests
- Profile slow tests and optimize

## Security Testing
- Test authentication and authorization
- Test input validation and sanitization
- Test for SQL injection (though ORM protects)
- Test for XSS in frontend (Angular protects by default)
- Verify sensitive data is not logged

## Debugging Tests

### pytest Debugging
```bash
# Run with verbose output
pytest tests/ -v

# Stop on first failure
pytest tests/ -x

# Show print statements
pytest tests/ -s

# Run specific test
pytest tests/test_file.py::test_function -v

# Use pdb debugger on failure
pytest tests/ --pdb
```

### Angular Debugging
```bash
# Run tests in watch mode
npm test

# Debug in Chrome
npm test -- --browsers=Chrome

# Generate coverage report
npm run test:coverage
```
