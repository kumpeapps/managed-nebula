# Version Checking and Security Advisory System

## Overview

The Version Checking and Security Advisory System automatically monitors client versions and checks them against the latest releases from GitHub. It identifies outdated clients and flags known security vulnerabilities, helping administrators keep their Nebula mesh network secure and up-to-date.

## Features

### 1. Automatic Version Checking
- Queries GitHub API for latest releases from:
  - `kumpeapps/managed-nebula` (client agent)
  - `slackhq/nebula` (Nebula binary)
- Compares client-reported versions against latest releases
- Categorizes version status as: current, outdated, vulnerable, or unknown

### 2. Security Advisory Detection
- Checks GitHub Security Advisory API for both repositories
- Matches advisories against specific client versions using version ranges
- Displays severity level (critical, high, medium, low)
- Provides links to full advisory details

### 3. Visual Indicators
- **Client List**: Status icons with tooltips
  - 🟢 Green: Up to date
  - 🟡 Yellow: Outdated (update available)
  - 🔴 Red: Vulnerable (security advisory applies)
  - ⚪ Gray: Unknown (version not reported)
- **Dashboard**: Version health statistics
  - Count of current clients
  - Count of outdated clients
  - Count of vulnerable clients
- **Client Detail**: Comprehensive version status section
  - Status for both client and Nebula versions
  - List of applicable security advisories
  - Severity badges and links

### 4. Intelligent Caching
- Release information cached for 1 hour
- Security advisories cached for 6 hours
- Prevents excessive API calls and rate limiting
- Graceful fallback to cached data if API is unavailable

## Client Version Reporting

### Python Client (Docker/Linux)
The Python client (`client/agent.py`) automatically reports version information in every config request:
- **Client version**: From `__version__` constant (default: "1.0.0")
- **Nebula version**: Detected by executing `nebula -version`
- **Environment overrides**: `CLIENT_VERSION_OVERRIDE` and `NEBULA_VERSION_OVERRIDE`

### macOS Native Client
The macOS client (`macos_client/`) reports version information starting from this release:
- **Client version**: From application bundle (`CFBundleShortVersionString`)
- **Nebula version**: Detected by executing `nebula -version`
- **Environment override**: `CLIENT_VERSION_OVERRIDE` (for testing)
- **Implementation**: Automatic detection in `PollingService.checkForUpdates()`

Both clients send version information as optional fields in the `/v1/client/config` POST request:
```json
{
  "token": "client_token",
  "public_key": "...",
  "client_version": "1.0.0",
  "nebula_version": "1.9.7"
}
```

**Note**: Clients not reporting version information will show "Unknown" status in the web UI. Older clients or clients with version detection failures will continue to work but won't receive version status indicators.

## API Endpoints

### GET /api/v1/version-status

Returns the latest version information and security advisories.

**Authentication**: Required

**Response**:
```json
{
  "latest_client_version": "1.2.0",
  "latest_nebula_version": "1.9.7",
  "client_advisories": [
    {
      "id": "GHSA-xxxx-yyyy-zzzz",
      "severity": "high",
      "summary": "Authentication bypass in client token validation",
      "affected_versions": "< 1.2.0",
      "patched_version": "1.2.0",
      "published_at": "2025-11-15T00:00:00Z",
      "url": "https://github.com/kumpeapps/managed-nebula/security/advisories/GHSA-xxxx",
      "cve_id": "CVE-2025-12345"
    }
  ],
  "nebula_advisories": [],
  "last_checked": "2025-11-23T21:00:00Z"
}
```

### Client Response with Version Status

The `ClientResponse` schema now includes an optional `version_status` field:

```json
{
  "id": 1,
  "name": "client1",
  "client_version": "1.0.0",
  "nebula_version": "1.9.3",
  "version_status": {
    "client_version_status": "outdated",
    "nebula_version_status": "outdated",
    "client_advisories": [],
    "nebula_advisories": [],
    "days_behind": 45
  }
}
```

## Configuration

### GitHub API Token (Optional)

To avoid rate limiting, you can configure a GitHub API token:

1. Create a personal access token at: https://github.com/settings/tokens
   - No special permissions required (public repository access only)
   
2. Store in system settings:
   ```sql
   INSERT INTO system_settings (key, value, updated_by)
   VALUES ('github_api_token', 'ghp_your_token_here', 'admin');
   ```

**Rate Limits**:
- Without token: 60 requests/hour per IP
- With token: 5,000 requests/hour

## Version Status Logic

### Status Determination

1. **Vulnerable** (Priority 1)
   - One or more security advisories apply to the current version
   - Status: `vulnerable`
   - Icon: 🔴 Red

2. **Outdated** (Priority 2)
   - Current version is behind latest release
   - No known vulnerabilities
   - Status: `outdated`
   - Icon: 🟡 Yellow

3. **Current** (Priority 3)
   - Running latest version
   - No known vulnerabilities
   - Status: `current`
   - Icon: 🟢 Green

4. **Unknown** (Fallback)
   - No version information available
   - Unable to determine status
   - Status: `unknown`
   - Icon: ⚪ Gray

### Version Comparison

Uses semantic versioning (semver) for accurate comparison:
- Handles various formats: "v1.9.7", "1.9.7", "1.9"
- Compares major.minor.patch components
- Supports pre-release versions (alpha, beta, rc)
- Normalizes versions for consistent comparison

### Advisory Matching

Checks if client version falls within affected version range:
- Supports operators: `<`, `<=`, `>`, `>=`, `=`
- Supports ranges: `>= 1.0.0, < 1.2.0`
- Matches against all published advisories
- Returns advisories sorted by severity

## Implementation Details

### Backend Services

1. **version_parser.py** (29 tests)
   - Parse semantic version strings
   - Compare versions using semver rules
   - Extract version components (major, minor, patch)
   - Detect pre-release versions
   - Normalize version strings

2. **github_api.py** (Integration tested)
   - GitHub API client with caching
   - Rate limit handling with exponential backoff
   - Support for authentication token
   - Graceful degradation on failures
   - In-memory cache with TTL

3. **advisory_checker.py** (20 tests)
   - Security advisory fetching
   - Version range parsing and matching
   - Severity level comparison
   - Advisory filtering by version

### Frontend Components

1. **Clients List** (`clients.component.ts`)
   - Version status icon in table
   - Tooltip with detailed status
   - Helper methods for icon/title generation

2. **Dashboard** (`dashboard.component.ts`)
   - Version health statistics card
   - Current/outdated/vulnerable counts
   - Visual breakdown with icons

3. **Client Detail** (`client-detail.component.ts`)
   - Version status section
   - Status indicators for both versions
   - Security advisory list with:
     - Advisory ID and CVE
     - Severity badge
     - Summary description
     - Affected version range
     - Link to full details

## Error Handling

The system handles various error conditions gracefully:

1. **GitHub API Rate Limiting**
   - Logs warning
   - Returns cached data
   - Continues operation without version status

2. **Network Failures**
   - Catches HTTP errors
   - Returns cached data if available
   - Shows "unknown" status to users

3. **Invalid Version Strings**
   - Attempts to extract numeric version
   - Falls back to "unknown" status
   - Logs parsing failures

4. **Missing Version Data**
   - Clients that haven't reported versions
   - Shows gray circle (unknown status)
   - Indicates "Version not reported"

## Performance Considerations

1. **Caching Strategy**
   - In-memory cache with TTL
   - Reduces API calls by ~99%
   - No database overhead
   - Automatic cache expiration

2. **API Call Optimization**
   - Only fetches latest release (not all releases)
   - Parallel advisory checks
   - Timeout handling (10 seconds)
   - Background polling recommended

3. **Frontend Performance**
   - Version status computed server-side
   - Minimal client-side processing
   - Icons use Unicode emoji (no images)
   - Progressive enhancement

## Future Enhancements

Potential future improvements:

1. **Settings Page Integration**
   - Toggle version checking on/off
   - Configure GitHub API token via UI
   - Manual cache refresh button
   - Last check timestamp display

2. **Notifications**
   - Alert administrators of vulnerable clients
   - Email notifications for critical advisories
   - Webhook integrations

3. **Database Cache Table**
   - Optional persistent cache
   - Advisory history tracking
   - Version change audit log

4. **Background Jobs**
   - Scheduled version checks
   - Automatic client notification
   - Report generation

5. **Custom Version Sources**
   - Support for forked Nebula builds
   - Custom release channels
   - Private repository support

## Testing

### Unit Tests

- **version_parser**: 29 tests covering all parsing scenarios
- **advisory_checker**: 20 tests for version matching and severity
- **Total**: 88 tests passing (100% pass rate)

### Integration Tests

Run the test suite:
```bash
cd server
pytest tests/ -v
```

### Manual Testing

1. Start the server:
   ```bash
   cd server
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
   ```

2. Test version-status endpoint:
   ```bash
   # Requires authentication
   curl -X GET http://localhost:8080/api/v1/version-status \
     -H "Cookie: session=YOUR_SESSION_COOKIE"
   ```

3. Check client with version status:
   - Navigate to Clients page
   - Observe version status icons
   - Click client to see detailed version status

## Troubleshooting

### No version status shown

**Cause**: Client hasn't reported version information

**Solution**: Ensure client agent is version 1.0.0+ which includes version reporting

### Rate limit errors in logs

**Cause**: Too many API calls to GitHub

**Solutions**:
1. Configure GitHub API token in system settings
2. Increase cache TTL
3. Reduce polling frequency

### "Unknown" status for all clients

**Cause**: GitHub API unavailable or blocked

**Solutions**:
1. Check network connectivity
2. Verify GitHub API is accessible
3. Check firewall rules
4. Enable API token authentication

### Advisories not showing

**Cause**: Security Advisory API requires authentication

**Solution**: Configure GitHub API token with proper permissions

## Security Considerations

1. **API Token Security**
   - Store tokens in system_settings table
   - Never log token values
   - Use read-only tokens (public repo access only)
   - Rotate tokens periodically

2. **Rate Limiting**
   - Respect GitHub API rate limits
   - Implement exponential backoff
   - Cache aggressively
   - Monitor API usage

3. **Data Privacy**
   - Version information is not sensitive
   - Advisory data is public
   - No PII transmitted to GitHub
   - All data cached locally

## References

- [GitHub REST API Documentation](https://docs.github.com/en/rest)
- [GitHub Security Advisories API](https://docs.github.com/en/rest/security-advisories)
- [Semantic Versioning](https://semver.org/)
- [Python packaging library](https://packaging.pypa.io/)
