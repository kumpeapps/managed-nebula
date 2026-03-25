# Using the Managed Nebula OpenAPI Specification

The `openapi-spec.yaml` file provides a complete API specification that can be imported into various API clients and tools.

## ⚡ Quick Start for RapidAPI/Paw Users

**If you're using RapidAPI Desktop (formerly Paw), follow these steps:**

1. **Get your API key** from the web UI: http://localhost:8080 → Profile → API Keys → Create
2. **Import the spec**: File → Import → Select `openapi-spec.yaml`
3. **Create environment**: Preferences → Environments → **+** → Add variable
   - Name: `apiKey`
   - Value: `mnapi_your_actual_key_here`
4. **Add auth to requests**: For each request → Headers → Add:
   - `Authorization`: `Bearer {{apiKey}}`
5. **Save and test!**

**Why manual setup?** RapidAPI/Paw doesn't automatically apply OpenAPI security schemes to imported requests. You need to add the `Authorization` header manually to each request or use environment defaults.

---

## Full Setup Guide

## Quick Start

### 1. Get Your API Key

1. Login to the Managed Nebula web UI
2. Navigate to **Profile → API Keys tab**
3. Click **"Create API Key"**
4. Copy the key (format: `mnapi_<64-hex-characters>`)
5. Save it securely - it's only shown once!

### 2. Import the OpenAPI Spec

#### Postman

1. Open Postman
2. Click **Import** → **File** → Select `openapi-spec.yaml`
3. The collection will be imported with all endpoints

#### Paw (macOS) / RapidAPI

1. Open Paw/RapidAPI
2. **File → Import** → Select `openapi-spec.yaml`
3. All endpoints will be imported as requests

**Important for RapidAPI/Paw:** The import will not automatically set up authentication. You must configure it manually:

1. **Create Environment**:
   - **RapidAPI Desktop**: **Preferences → Environments** → Click **+** to add new environment
   - **Paw**: **Environments** → **Manage Environments**
   
2. **Add the `apiKey` variable**:
   - **Name/Key**: `apiKey`
   - **Value**: `mnapi_your_actual_key_here` (your full API key from the web UI)
   
3. **Apply to all requests**:
   - Select a request from the imported collection
   - In the right panel, find **Authorization** or **Headers**
   - Add or edit the `Authorization` header:
     - **Header**: `Authorization`
     - **Value**: `Bearer {{apiKey}}` (use the environment variable)
   
4. **Apply to all requests in collection**:
   - You may need to manually add the `Authorization: Bearer {{apiKey}}` header to each request
   - Or use RapidAPI's "Request Variables" feature to inherit authentication

**Alternative: Set Authorization for each request:**
- In each request → **Auth** tab → Select **Bearer Token**
- Token value: `{{apiKey}}` (reference your environment variable)

#### Insomnia

1. Open Insomnia
2. Click **Create** → **Import From** → **File**
3. Select `openapi-spec.yaml`

### 3. Configure the `apiKey` Variable

#### Postman

1. Click on the collection → **Variables** tab
2. Add a new variable:
   - **Variable**: `apiKey`
   - **Initial Value**: `mnapi_your_actual_key_here`
   - **Type**: `default`
3. Save the collection

Or create an environment:
1. **Environments** → **Create Environment**
2. Add variable: `apiKey` = `mnapi_your_key_here`
3. Select this environment when making requests

#### Paw / RapidAPI

**RapidAPI Desktop (formerly Paw):**

1. **Preferences** (Cmd+,) → **Environments**
2. Click **+** to create new environment (e.g., "Managed Nebula Local")
3. Add variable:
   - **Variable Name**: `apiKey`
   - **Value**: `mnapi_your_actual_key_here`
4. Click **Save**
5. Select this environment from the environments dropdown

**Then for EACH imported request:**
- Click on the request
- In the right panel → **Headers** section
- Add header:
  - **Header**: `Authorization`
  - **Value**: Click the **{}** button and select `Bearer {{apiKey}}`
  - Or manually type: `Bearer {{apiKey}}`

**Note**: RapidAPI/Paw does not automatically apply collection-level authentication from OpenAPI imports. You must add the Authorization header to each request manually, or set it as a default header in your environment.

#### Insomnia

1. **Manage Environments** (Ctrl+E / Cmd+E)
2. Add to base environment:
```json
{
  "apiKey": "mnapi_your_key_here",
  "baseUrl": "http://localhost:8080"
}
```

### 4. Update the Base URL (Optional)

By default, the spec uses `http://localhost:8080`. To use a different server:

#### Postman
- Collection Variables → Update `baseUrl`

#### Paw / RapidAPI
- Environment Variables → Update server URL

#### Insomnia
- Environment → Update `baseUrl` variable

## Authentication

All authenticated endpoints use Bearer token authentication:

```
Authorization: Bearer mnapi_your_api_key_here
```

The OpenAPI spec is preconfigured to use the `apiKey` variable, so once you set it, all requests will automatically include the correct Authorization header.

## Example Requests

### Using cURL

```bash
# List all clients
curl -X GET "http://localhost:8080/clients" \
     -H "Authorization: Bearer mnapi_your_key_here" \
     -H "Content-Type: application/json"

# Create a new client
curl -X POST "http://localhost:8080/clients" \
     -H "Authorization: Bearer mnapi_your_key_here" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "web-server-01",
       "pool_id": 1,
       "group_ids": [1]
     }'
```

### Using Python

```python
import requests

API_KEY = "mnapi_your_key_here"
BASE_URL = "http://localhost:8080"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# List all clients
response = requests.get(f"{BASE_URL}/clients", headers=headers)
clients = response.json()
print(clients)

# Create a new client
new_client = {
    "name": "web-server-01",
    "pool_id": 1,
    "group_ids": [1]
}
response = requests.post(f"{BASE_URL}/clients", headers=headers, json=new_client)
print(response.json())
```

### Using JavaScript/Node.js

```javascript
const axios = require('axios');

const API_KEY = 'mnapi_your_key_here';
const BASE_URL = 'http://localhost:8080';

const client = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
  }
});

// List all clients
client.get('/clients')
  .then(response => console.log(response.data))
  .catch(error => console.error(error));

// Create a new client
client.post('/clients', {
  name: 'web-server-01',
  pool_id: 1,
  group_ids: [1]
})
  .then(response => console.log(response.data))
  .catch(error => console.error(error));
```

## API Key Scopes

API keys can have restricted scopes:

- **Group Restrictions**: Limit access to specific client groups
- **IP Pool Restrictions**: Limit access to specific IP pools
- **Created Clients Only**: Only access clients created by this API key

Configure scopes when creating the API key in the web UI.

## Available Endpoints

The OpenAPI spec includes all API endpoints organized by tags:

- **auth** - Authentication and user profile
- **clients** - Client (node) management
- **groups** - Client group management
- **firewall-rulesets** - Firewall configuration
- **ip-pools** - IP address pools
- **ip-groups** - IP group management for certificates
- **ca** - Certificate Authority management
- **users** - User account management (admin)
- **user-groups** - User group permissions
- **api-keys** - API key management
- **permissions** - Permission management
- **settings** - System configuration
- **version** - Version and update information
- **github** - GitHub integrations
- **health** - Health check endpoints

## Troubleshooting

### "Unauthorized" or 401 errors
- Verify your API key is correct (should start with `mnapi_`)
- Check that the `apiKey` variable is set in your environment
- Ensure the Authorization header format is: `Bearer mnapi_...`

### "Forbidden" or 403 errors
- Check API key scopes - you may not have access to this resource
- Some endpoints require admin privileges

### Connection errors
- Verify the server URL is correct
- Check that the Managed Nebula server is running
- Ensure there are no firewall rules blocking the connection

## More Information

- [Main README](README.md) - Project overview and setup
- [API Key Guide](API_KEY_GUIDE.md) - Detailed API key documentation
- [API Documentation](https://github.com/kumpeapps/managed-nebula) - Full API documentation
