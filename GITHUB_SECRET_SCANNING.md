# GitHub Secret Scanning Integration

This document explains how to set up and use the GitHub Secret Scanning Partner Program integration with Managed Nebula.

## Overview

Managed Nebula supports the GitHub Secret Scanning Partner Program, which allows GitHub to automatically detect and alert you when Nebula client tokens are accidentally committed to public repositories.

## Features

- **Automatic Detection**: GitHub scans public repositories for Managed Nebula client tokens
- **Token Verification**: Verify if detected tokens are valid and active
- **Automatic Revocation**: Automatically deactivate tokens found in public repositories
- **Audit Trail**: All detection and revocation events are logged

## Token Format

New client tokens follow this standardized format:

```
<prefix><32-random-alphanumeric-characters>
```

**Default format**: `mnebula_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

The prefix is configurable (default: `mnebula_`) and must be 3-20 characters (alphanumeric and underscores only).

### Backward Compatibility

Legacy tokens without the prefix continue to work. The system supports both formats:
- **New format**: `mnebula_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`
- **Legacy format**: Various alphanumeric formats (32+ characters)

## Setup Instructions

### 1. Configure Token Prefix (Optional)

By default, tokens use the `mnebula_` prefix. To customize:

1. Log in as an admin
2. Navigate to **Settings > Security**
3. Update the **Token Prefix** field
4. Click **Save**

**Note**: Changing the prefix only affects new tokens. Existing tokens remain valid.

### 2. Configure GitHub Webhook Secret

To enable GitHub Secret Scanning integration:

1. Generate a strong webhook secret (minimum 16 characters):
   ```bash
   openssl rand -hex 32
   ```

2. Log in to Managed Nebula as an admin
3. Navigate to **Settings > Security**
4. Enter the webhook secret in the **GitHub Webhook Secret** field
5. Click **Save**

### 3. Register with GitHub Secret Scanning Partner Program

1. Visit: https://docs.github.com/en/code-security/secret-scanning/secret-scanning-partner-program

2. Provide GitHub with these endpoint URLs:
   - **Pattern Metadata**: `https://your-domain/.well-known/secret-scanning.json`
   - **Verification Endpoint**: `https://your-domain/api/v1/github/secret-scanning/verify`
   - **Revocation Endpoint**: `https://your-domain/api/v1/github/secret-scanning/revoke`

3. Share your webhook secret with GitHub (the one you configured in step 2)

### 4. Test the Integration

1. Create a test repository on GitHub
2. Generate a test token in Managed Nebula
3. Commit the token to your test repository
4. GitHub should detect and alert you within minutes

## API Endpoints

### Public Endpoints (No Authentication)

#### Pattern Metadata
```
GET /.well-known/secret-scanning.json
```

Returns the secret pattern that GitHub uses to detect tokens.

**Example Response**:
```json
[
  {
    "type": "managed_nebula_client_token",
    "pattern": "mnebula_[a-z0-9]{32}",
    "description": "Managed Nebula Client Token"
  }
]
```

### GitHub-Authenticated Endpoints (Webhook Signature Required)

#### Token Verification
```
POST /api/v1/github/secret-scanning/verify
```

Verifies if a detected token is valid and returns details.

**Request** (from GitHub):
```json
[
  {
    "type": "managed_nebula_client_token",
    "token": "mnebula_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "url": "https://github.com/org/repo/blob/main/file.py"
  }
]
```

**Response**:
```json
[
  {
    "token": "mnebula_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "type": "managed_nebula_client_token",
    "label": "client-hostname",
    "url": "https://your-nebula.com/clients/123",
    "is_active": true
  }
]
```

#### Token Revocation
```
POST /api/v1/github/secret-scanning/revoke
```

Automatically deactivates tokens found in public repositories.

**Request** (from GitHub):
```json
[
  {
    "type": "managed_nebula_client_token",
    "token": "mnebula_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "url": "https://github.com/org/repo/blob/main/file.py"
  }
]
```

**Response**:
```json
{
  "message": "Tokens processed",
  "revoked_count": 1
}
```

### Admin Endpoints (Authentication Required)

#### Get Token Prefix
```
GET /api/v1/settings/token-prefix
```

Returns the current token prefix setting.

#### Update Token Prefix
```
PUT /api/v1/settings/token-prefix
```

**Request**:
```json
{
  "prefix": "custom_"
}
```

**Validation Rules**:
- 3-20 characters
- Alphanumeric and underscores only
- Must end with underscore (recommended)

#### Re-issue Client Token
```
POST /api/v1/clients/{client_id}/tokens/{token_id}/reissue
```

Deactivates the old token and generates a new one.

**Response**:
```json
{
  "id": 123,
  "token": "mnebula_newtoken123...",
  "client_id": 456,
  "created_at": "2024-01-15T10:30:00Z",
  "old_token_id": 122
}
```

**⚠️ Important**: The full token is only shown once in the response. Save it securely!

## Security Considerations

### Webhook Signature Verification

All requests from GitHub to the verification and revocation endpoints are authenticated using HMAC SHA-256 signatures. The signature is sent in the `X-Hub-Signature-256` header.

**Signature Format**:
```
sha256=<hex_digest>
```

If the signature doesn't match, the request is rejected with a 401 error.

### Audit Trail

All GitHub Secret Scanning events are logged in the `github_secret_scanning_logs` table:

- **Action**: `verify` or `revoke`
- **Token Preview**: First 12 characters (for security)
- **GitHub URL**: Where the token was found
- **Token Status**: Active/inactive at time of event
- **Client ID**: Associated client (if found)
- **Timestamp**: When the event occurred

View logs with:
```sql
SELECT * FROM github_secret_scanning_logs ORDER BY created_at DESC;
```

### Rate Limiting

Consider implementing rate limiting on the public GitHub endpoints to prevent abuse:

```nginx
# Nginx example
limit_req_zone $binary_remote_addr zone=github_scan:10m rate=10r/s;

location /api/v1/github/secret-scanning/ {
    limit_req zone=github_scan burst=20;
    proxy_pass http://backend;
}
```

## Token Rotation Best Practices

1. **Regular Rotation**: Rotate client tokens every 3-6 months
2. **Immediate Rotation**: Re-issue tokens immediately if:
   - Token found in public repository
   - Suspicious activity detected
   - Employee leaves organization
3. **Monitoring**: Check audit logs regularly for GitHub scanning events
4. **Testing**: Test token revocation process periodically

## Troubleshooting

### GitHub Not Detecting Tokens

1. **Check token format**: Ensure tokens match the pattern `<prefix>[a-z0-9]{32}`
2. **Verify public endpoint**: Test `/.well-known/secret-scanning.json` is accessible
3. **Check GitHub registration**: Ensure you've completed Partner Program registration
4. **Pattern mismatch**: If you changed the prefix, update it with GitHub

### Webhook Signature Verification Failing

1. **Check webhook secret**: Ensure it matches the one configured in Managed Nebula
2. **Verify header**: GitHub sends `X-Hub-Signature-256` header
3. **Check payload**: Signature is computed over the raw request body
4. **Test signature**:
   ```python
   import hmac
   import hashlib
   
   payload = b'{"token": "test"}'
   secret = "your-webhook-secret"
   signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
   print(f"sha256={signature}")
   ```

### Tokens Not Being Revoked

1. **Check audit logs**: Verify revocation requests are being received
2. **Verify token format**: Ensure token matches the expected format
3. **Check database**: Verify `is_active` flag is being set to `False`
4. **Client still connecting**: Clients cache configs; may take up to 24 hours (or next poll interval)

## Example: Testing Locally

```bash
# 1. Generate a test token
curl -X POST http://localhost:8080/api/v1/clients/1/tokens \
  -H "Authorization: Bearer admin-token" \
  -H "Content-Type: application/json"

# 2. Test verification endpoint
echo '[{"type":"managed_nebula_client_token","token":"mnebula_test123","url":"https://github.com/test/repo"}]' | \
  curl -X POST http://localhost:8080/api/v1/github/secret-scanning/verify \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$(echo -n '[{"type":"managed_nebula_client_token","token":"mnebula_test123","url":"https://github.com/test/repo"}]' | openssl dgst -sha256 -hmac 'your-secret' | cut -d' ' -f2)" \
  -d @-

# 3. Check audit logs
docker exec nebula-server sqlite3 /app/app.db "SELECT * FROM github_secret_scanning_logs;"
```

## Resources

- [GitHub Secret Scanning Partner Program](https://docs.github.com/en/code-security/secret-scanning/secret-scanning-partner-program)
- [HMAC SHA-256 Signature Verification](https://docs.github.com/en/developers/webhooks-and-events/webhooks/securing-your-webhooks)
- [Managed Nebula API Documentation](http://localhost:8080/docs)

## Support

For issues or questions:
1. Check the audit logs for GitHub scanning events
2. Review server logs for error messages
3. Open an issue on GitHub: https://github.com/kumpeapps/managed-nebula/issues
