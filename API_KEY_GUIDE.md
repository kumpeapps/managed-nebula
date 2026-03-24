# API Key Authentication Guide

## Overview

Managed Nebula supports API key authentication for programmatic access to the REST API. This allows you to automate tasks, integrate with CI/CD pipelines, and build custom tools without requiring interactive login sessions.

## Features

- **Secure Key Generation**: Cryptographically secure API keys with bcrypt_sha256 hashing
- **Configurable Expiration**: Set expiration dates up to 10 years (or no expiration)
- **Usage Tracking**: Monitor when and how often your keys are used
- **Rate Limiting**: Maximum of 10 active keys per user
- **Easy Revocation**: Instantly revoke compromised keys
- **Scope-based Permissions** (planned): Fine-grained control over API access

## Generating an API Key

### Via Web UI

1. Log in to the Managed Nebula web interface
2. Navigate to **Profile** → **API Keys** tab
3. Click **"+ Generate API Key"**
4. Fill in the details:
   - **Name**: A descriptive name to identify the key (e.g., "CI/CD Pipeline", "Automation Script")
   - **Expires In (days)**: Optional expiration period (leave empty for no expiration)
5. Click **"Generate Key"**
6. **IMPORTANT**: Copy the generated API key immediately. You won't be able to see it again!

### Key Format

API keys follow this format:
```
mnapi_<64-character-hex-string>
```

Example:
```
mnapi_0000000000000000000000000000000000000000000000000000000000000000
```

> **Note**: The above is a placeholder example. Real API keys use cryptographically random hex characters.

## Using API Keys

### Authentication Header

Include your API key in the `Authorization` header with the `Bearer` scheme:

```bash
curl -H "Authorization: Bearer mnapi_YOUR_API_KEY_HERE" \
     https://your-nebula-server.com/api/v1/clients
```

### Example: List All Clients

```bash
curl -X GET \
  -H "Authorization: Bearer mnapi_YOUR_ACTUAL_API_KEY_HERE" \
  https://your-nebula-server.com/api/v1/clients
```

### Example: Create a New Client

```bash
curl -X POST \
  -H "Authorization: Bearer mnapi_YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new-client",
    "is_lighthouse": false,
    "group_ids": [1, 2]
  }' \
  https://your-nebula-server.com/api/v1/clients
```

### Python Example

```python
import requests

API_KEY = "mnapi_YOUR_API_KEY_HERE"
BASE_URL = "https://your-nebula-server.com/api/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# List all clients
response = requests.get(f"{BASE_URL}/clients", headers=headers)
clients = response.json()
print(f"Found {len(clients)} clients")

# Create a new client
new_client = {
    "name": "automated-client",
    "is_lighthouse": False,
    "group_ids": [1]
}
response = requests.post(f"{BASE_URL}/clients", headers=headers, json=new_client)
if response.status_code == 200:
    print(f"Created client: {response.json()['name']}")
```

### JavaScript/Node.js Example

```javascript
const API_KEY = 'mnapi_YOUR_API_KEY_HERE';
const BASE_URL = 'https://your-nebula-server.com/api/v1';

const headers = {
  'Authorization': `Bearer ${API_KEY}`,
  'Content-Type': 'application/json'
};

// List all clients
fetch(`${BASE_URL}/clients`, { headers })
  .then(res => res.json())
  .then(clients => console.log(`Found ${clients.length} clients`))
  .catch(err => console.error('Error:', err));

// Create a new client
const newClient = {
  name: 'automated-client',
  is_lighthouse: false,
  group_ids: [1]
};

fetch(`${BASE_URL}/clients`, {
  method: 'POST',
  headers,
  body: JSON.stringify(newClient)
})
  .then(res => res.json())
  .then(client => console.log(`Created client: ${client.name}`))
  .catch(err => console.error('Error:', err));
```

## Managing API Keys

### Viewing Your Keys

1. Navigate to **Profile** → **API Keys** tab
2. View all your active and revoked keys with:
   - Key name
   - Key prefix (first 12 characters for identification)
   - Status (Active/Revoked)
   - Creation date
   - Expiration date
   - Last used timestamp
   - Total usage count

### Revoking a Key

If a key is compromised or no longer needed:

1. Navigate to **Profile** → **API Keys** tab
2. Find the key in the list
3. Click **"Revoke"**
4. Confirm the action

**Note**: Revoked keys cannot be reactivated. You must generate a new key.

## API Endpoints

All API key endpoints are prefixed with `/api/v1/api-keys`.

### List API Keys

```http
GET /api/v1/api-keys?include_inactive=false
```

**Response:**
```json
{
  "keys": [
    {
      "id": 1,
      "user_id": 1,
      "name": "CI/CD Pipeline",
      "key_prefix": "mnapi_a1b2c3",
      "scopes": null,
      "is_active": true,
      "created_at": "2026-03-24T01:00:00",
      "expires_at": "2027-03-24T01:00:00",
      "last_used_at": "2026-03-24T12:00:00",
      "usage_count": 42
    }
  ],
  "total": 1
}
```

### Create API Key

```http
POST /api/v1/api-keys
Content-Type: application/json

{
  "name": "My Automation Script",
  "expires_in_days": 365
}
```

**Response:**
```json
{
  "id": 2,
  "user_id": 1,
  "name": "My Automation Script",
  "key": "mnapi_0000000000000000000000000000000000000000000000000000000000000000",
  "key_prefix": "mnapi_000000",
  "scopes": null,
  "is_active": true,
  "created_at": "2026-03-24T01:30:00",
  "expires_at": "2027-03-24T01:30:00"
}
```

> **Note**: The `key` field contains your actual API key only during creation. Store it securely!
```

### Get Single API Key

```http
GET /api/v1/api-keys/{key_id}
```

### Update API Key

```http
PUT /api/v1/api-keys/{key_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "is_active": true
}
```

### Revoke API Key

```http
DELETE /api/v1/api-keys/{key_id}
```

## Security Best Practices

### Storage

- **Never commit API keys to version control** (add to `.gitignore`)
- Store keys in environment variables or secure secret management systems
- Use different keys for different environments (development, staging, production)

### Rotation

- Regularly rotate API keys (recommended: every 90-180 days)
- Set expiration dates when generating keys
- Immediately revoke keys that may have been compromised

### Permissions

- Use descriptive names to track key purposes
- Generate separate keys for different applications/services
- Follow the principle of least privilege (when scope-based permissions are implemented)

### Monitoring

- Regularly review the "Last Used" timestamp for each key
- Investigate unexpected usage patterns
- Revoke unused keys to minimize attack surface

## Troubleshooting

### "Invalid API key" Error

- Verify the key is copied correctly (including the `mnapi_` prefix)
- Check that the key hasn't been revoked
- Ensure the key hasn't expired
- Confirm you're using the `Bearer` authentication scheme

### "Maximum number of API keys reached" Error

- Review your existing keys in the Profile → API Keys tab
- Revoke unused or expired keys
- Default limit: 10 active keys per user

### Key Not Working After Creation

- Ensure you're including the full key, not just the prefix
- Verify the `Authorization` header format: `Bearer mnapi_...`
- Check server logs for authentication errors

## Rate Limiting

- Maximum 10 active API keys per user
- No per-key request rate limits (uses same limits as session authentication)

## Migration from Session-based Auth

API keys work alongside existing session-based authentication:

- **Web UI**: Uses session cookies (no changes needed)
- **Programmatic access**: Use API keys with `Authorization` header
- Both methods access the same endpoints with identical permissions

## Future Enhancements

Planned features for API key authentication:

- **Scope-based permissions**: Fine-grained control over which API endpoints each key can access
- **IP whitelisting**: Restrict keys to specific IP addresses
- **Webhooks**: Get notified when keys are used or reach usage thresholds
- **Audit logs**: Detailed tracking of all API key operations

## Support

For issues or feature requests related to API keys, please:

1. Check the [GitHub Issues](https://github.com/kumpeapps/managed-nebula/issues)
2. Create a new issue with the label `api-keys`
3. Include relevant error messages and steps to reproduce
