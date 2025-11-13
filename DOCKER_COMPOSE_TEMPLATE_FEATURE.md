# Docker Compose Template Customization Feature

## Overview
This feature allows administrators to customize the docker-compose template used when generating client deployment files. Templates support dynamic placeholders that are replaced with actual values when a client downloads their configuration.

## Architecture

### Backend Implementation

#### Database Model (server/app/models/settings.py)
- Added `docker_compose_template` field to `GlobalSettings` model (TEXT column)
- Stores the customizable YAML template with placeholders
- Default template provided that matches existing behavior

#### Database Migration (server/alembic/versions/202511132147_add_docker_compose_template.py)
- Adds the new column to `global_settings` table
- Sets default value for existing rows
- Reversible migration with proper downgrade

#### API Endpoints (server/app/routers/api.py)

**Settings Endpoints (Extended):**
- `GET /api/v1/settings` - Now includes `docker_compose_template` field
- `PUT /api/v1/settings` - Now accepts `docker_compose_template` with YAML validation

**New Template-Specific Endpoints:**
- `GET /api/v1/settings/docker-compose-template` - Retrieve current template (admin-only)
- `PUT /api/v1/settings/docker-compose-template` - Update template with YAML validation (admin-only)
- `GET /api/v1/settings/placeholders` - List available placeholders with descriptions (admin-only)

**Enhanced Client Download:**
- `GET /api/v1/clients/{id}/docker-compose` - Now uses template with placeholder replacement

#### Placeholder System
Available placeholders that get replaced with actual values:
- `{{CLIENT_NAME}}` - Client hostname/identifier
- `{{CLIENT_TOKEN}}` - Authentication token for API access
- `{{SERVER_URL}}` - Full API endpoint URL
- `{{CLIENT_DOCKER_IMAGE}}` - Docker image reference
- `{{POLL_INTERVAL_HOURS}}` - Config polling frequency

### Frontend Implementation

#### Models (frontend/src/app/models/index.ts)
Extended Settings interface with:
- `docker_compose_template: string` field
- New interfaces: `DockerComposeTemplate`, `Placeholder`, `PlaceholdersResponse`

#### Services (frontend/src/app/services/api.service.ts)
New API methods:
- `getDockerComposeTemplate()` - Fetch current template
- `updateDockerComposeTemplate(template: string)` - Update template
- `getPlaceholders()` - Fetch available placeholders

#### Settings Component (frontend/src/app/components/settings.component.ts)
Enhanced with three new sections:
1. **Template Editor** - YAML textarea for editing the template
2. **Available Placeholders** - Reference table showing all placeholders
3. **Preview** - Live preview with sample data

New features:
- "Reset to Default" button to restore original template
- "Save Changes" button with validation
- Real-time preview updates as you type
- YAML validation with error feedback

## Usage Examples

### Default Template
```yaml
version: '3.8'

services:
  nebula-client:
    image: {{CLIENT_DOCKER_IMAGE}}
    container_name: nebula-{{CLIENT_NAME}}
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    environment:
      SERVER_URL: {{SERVER_URL}}
      CLIENT_TOKEN: {{CLIENT_TOKEN}}
      POLL_INTERVAL_HOURS: {{POLL_INTERVAL_HOURS}}
    volumes:
      - ./nebula-config:/etc/nebula
      - ./nebula-data:/var/lib/nebula
    network_mode: host
```

### Custom Template Example
An administrator could customize this to:
- Add custom labels for monitoring
- Include additional environment variables
- Change volume mount paths
- Add custom networks
- Include logging configuration

Example customization:
```yaml
version: '3.8'

services:
  nebula-client:
    image: {{CLIENT_DOCKER_IMAGE}}
    container_name: nebula-{{CLIENT_NAME}}
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    environment:
      SERVER_URL: {{SERVER_URL}}
      CLIENT_TOKEN: {{CLIENT_TOKEN}}
      POLL_INTERVAL_HOURS: {{POLL_INTERVAL_HOURS}}
      LOG_LEVEL: info
    volumes:
      - /opt/nebula/config:/etc/nebula
      - /opt/nebula/data:/var/lib/nebula
    labels:
      - "com.example.app=nebula"
      - "com.example.client={{CLIENT_NAME}}"
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    networks:
      - nebula-net

networks:
  nebula-net:
    driver: bridge
```

## API Usage Examples

### Get Placeholders
```bash
curl -X GET https://your-server.com/api/v1/settings/placeholders \
  -H "Cookie: session=your-session-cookie"
```

Response:
```json
{
  "placeholders": [
    {
      "name": "{{CLIENT_NAME}}",
      "description": "Client hostname/identifier",
      "example": "my-client"
    },
    {
      "name": "{{CLIENT_TOKEN}}",
      "description": "Authentication token for API access",
      "example": "abc123..."
    },
    ...
  ]
}
```

### Get Current Template
```bash
curl -X GET https://your-server.com/api/v1/settings/docker-compose-template \
  -H "Cookie: session=your-session-cookie"
```

Response:
```json
{
  "template": "version: '3.8'\n\nservices:\n  nebula-client:\n    ..."
}
```

### Update Template
```bash
curl -X PUT https://your-server.com/api/v1/settings/docker-compose-template \
  -H "Cookie: session=your-session-cookie" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "version: '\''3.8'\''\n\nservices:\n  nebula-client:\n    ..."
  }'
```

### Download Client Docker Compose
```bash
curl -X GET https://your-server.com/api/v1/clients/1/docker-compose \
  -H "Cookie: session=your-session-cookie" \
  -o client-docker-compose.yml
```

The downloaded file will have all placeholders replaced with actual values.

## Testing

### Backend Tests (server/tests/test_docker_compose_template.py)
Comprehensive test coverage including:
- Placeholder retrieval
- Template CRUD operations
- YAML validation
- Placeholder replacement logic
- Default template validity

Run tests:
```bash
cd server
pytest tests/test_docker_compose_template.py -v
```

### Manual Testing

1. **Login as admin** to the web UI
2. **Navigate to Settings** page
3. **Scroll to "Docker Compose Template" section**
4. **Edit the template** in the textarea
5. **View the preview** with sample data
6. **Click "Save Changes"** to persist
7. **Download a client's docker-compose** to verify placeholders are replaced

## Security Considerations

- All template endpoints require admin authentication
- YAML validation prevents malformed templates
- Placeholders are safely replaced with string substitution
- No code execution in templates (pure YAML)
- Original default template can always be restored

## Benefits

1. **Infrastructure Flexibility** - Match your organization's Docker standards
2. **Centralized Management** - Update template once, affects all new downloads
3. **Custom Configuration** - Add monitoring, logging, networking as needed
4. **Version Control Friendly** - Templates stored in database, can be exported
5. **Safe Defaults** - Comes with working default template

## Future Enhancements

Potential improvements for future versions:
- Multiple templates (per-client or per-group)
- Template versioning/history
- Template validation beyond YAML (lint docker-compose syntax)
- Additional placeholders (client groups, IP address, etc.)
- Template import/export functionality
- Template preview with actual client data (not just samples)
