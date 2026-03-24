# Managed Nebula Integration Quick Reference

**Copy this file to your project for quick API reference**

## Authentication

### API Key (Recommended for Automation)
```bash
# Generate: Profile → API Keys in Web UI
export NEBULA_API_KEY="mnapi_abc123..."

curl -H "Authorization: Bearer $NEBULA_API_KEY" \
     https://nebula.example.com/api/v1/clients
```

### Session (Web UI)
```bash
curl -X POST https://nebula.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"pass"}'
```

## Essential Endpoints

### Clients

```python
# Create client
POST /api/v1/clients
{
  "name": "my-client",
  "is_lighthouse": false,
  "group_ids": [1],
  "pool_id": 1
}

# List clients
GET /api/v1/clients

# Get client config
GET /api/v1/clients/{id}/config

# Update client
PUT /api/v1/clients/{id}
{
  "group_ids": [1, 2],
  "is_blocked": false
}

# Delete client
DELETE /api/v1/clients/{id}
```

### API Keys

```python
# Generate key (shown once!)
POST /api/v1/api-keys
{
  "name": "CI/CD Pipeline",
  "expires_in_days": 365
}

# List keys
GET /api/v1/api-keys

# Revoke key
DELETE /api/v1/api-keys/{id}
```

### Groups

```python
# Create group
POST /api/v1/groups
{"name": "production"}

# List groups
GET /api/v1/groups
```

### IP Pools

```python
# Create pool
POST /api/v1/ip-pools
{
  "cidr": "10.100.0.0/16",
  "description": "Production pool"
}

# List pools
GET /api/v1/ip-pools

# Check available IPs
GET /api/v1/ip-pools/{id}/available
```

### Firewall

```python
# Create ruleset
POST /api/v1/firewall-rulesets
{
  "name": "web-servers",
  "description": "Allow HTTP/HTTPS"
}

# Create rule
POST /api/v1/firewall-rules
{
  "direction": "inbound",
  "port": "443",
  "proto": "tcp",
  "cidr": "0.0.0.0/0"
}
```

## Python Quick Start

```python
import os
import requests

# Setup
API_URL = os.getenv("NEBULA_API_URL", "https://nebula.example.com/api/v1")
API_KEY = os.getenv("NEBULA_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Create client
response = requests.post(
    f"{API_URL}/clients",
    headers=headers,
    json={
        "name": "automated-client",
        "group_ids": [1],
        "pool_id": 1
    }
)
client = response.json()
print(f"Created: {client['name']} with IP {client['ip_address']}")

# List all clients
clients = requests.get(f"{API_URL}/clients", headers=headers).json()
print(f"Total clients: {len(clients)}")

# Download config for client
config_response = requests.get(
    f"{API_URL}/clients/{client['id']}/config",
    headers=headers
)
config_data = config_response.json()
# Returns: {config: "...", client_cert_pem: "...", ca_chain_pems: [...]}
```

## Common Patterns

### Bulk Client Creation

```python
def create_clients_for_team(team_name, member_count):
    # Create group
    group_resp = requests.post(
        f"{API_URL}/groups",
        headers=headers,
        json={"name": team_name}
    )
    group_id = group_resp.json()['id']
    
    # Create clients
    clients = []
    for i in range(member_count):
        client_resp = requests.post(
            f"{API_URL}/clients",
            headers=headers,
            json={
                "name": f"{team_name}-member-{i+1}",
                "group_ids": [group_id]
            }
        )
        clients.append(client_resp.json())
    
    return clients
```

### Health Monitoring

```python
def check_client_health():
    clients = requests.get(f"{API_URL}/clients", headers=headers).json()
    
    never_connected = [
        c for c in clients 
        if not c['last_config_download_at']
    ]
    
    blocked = [c for c in clients if c['is_blocked']]
    
    return {
        'total': len(clients),
        'never_connected': len(never_connected),
        'blocked': len(blocked),
        'active': len(clients) - len(never_connected) - len(blocked)
    }
```

### Error Handling

```python
from requests.exceptions import HTTPError

try:
    response = requests.post(
        f"{API_URL}/clients",
        headers=headers,
        json=client_data,
        timeout=30
    )
    response.raise_for_status()
    return response.json()
    
except HTTPError as e:
    if e.response.status_code == 401:
        print("Invalid API key")
    elif e.response.status_code == 409:
        print("Conflict - duplicate name or IP")
    elif e.response.status_code == 400:
        print(f"Validation error: {e.response.json()['detail']}")
    else:
        print(f"Error: {e}")
```

## Status Codes

- `200` - Success
- `400` - Bad Request (validation error)
- `401` - Unauthorized (invalid/missing API key)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `409` - Conflict (duplicate, resource in use)
- `503` - Service Unavailable (no active CA)

## Environment Variables

```bash
# Required
export NEBULA_API_URL="https://nebula.example.com"
export NEBULA_API_KEY="mnapi_your_key_here"

# Optional
export NEBULA_VERIFY_SSL="true"
export NEBULA_TIMEOUT="30"
```

## Docker Compose Integration

```yaml
version: '3.8'
services:
  nebula-provisioner:
    image: my-provisioner:latest
    environment:
      - NEBULA_API_URL=${NEBULA_API_URL}
      - NEBULA_API_KEY=${NEBULA_API_KEY}
```

## Testing

```python
import pytest

@pytest.fixture
def nebula_client():
    return {
        'url': os.getenv('TEST_NEBULA_URL'),
        'headers': {'Authorization': f'Bearer {os.getenv("TEST_API_KEY")}'}
    }

def test_create_client(nebula_client):
    resp = requests.post(
        f"{nebula_client['url']}/clients",
        headers=nebula_client['headers'],
        json={'name': 'test-client'}
    )
    assert resp.status_code == 200
    assert resp.json()['name'] == 'test-client'
```

## Troubleshooting

### "Invalid API key"
- Check key includes `mnapi_` prefix
- Verify key hasn't been revoked
- Check expiration date

### "Maximum number of API keys reached"
- Max 10 active keys per user
- Revoke unused keys: Profile → API Keys

### "No IP address assigned"
- Ensure IP pool exists and has available IPs
- Check: `GET /api/v1/ip-pools`

### "Certificate expired"
- Automatic rotation every 6 months (client certs)
- Force reissue: `POST /api/v1/clients/{id}/certificates/reissue`

## Links

- GitHub: https://github.com/kumpeapps/managed-nebula
- Docker Images: `ghcr.io/kumpeapps/managed-nebula/{server,frontend,client}:latest`
- Full Documentation: See `API_KEY_GUIDE.md` in repository

## Need Help?

Use the Copilot agent in your repository:

```
@managed-nebula How do I [your question]?
```

---
**Last Updated**: March 2026 | **Version**: 1.0.0
