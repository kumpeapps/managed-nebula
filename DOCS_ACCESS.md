# API Documentation Access Guide

This document explains how to access the FastAPI interactive documentation through the frontend proxy.

## Available Documentation Endpoints

The Managed Nebula API documentation is now accessible through the frontend HTTPS proxy:

### Swagger UI (Interactive API Documentation)
- **URL**: `https://localhost/api/docs` (or `https://your-domain/api/docs`)
- **Description**: Interactive API documentation with "Try it out" functionality
- **Features**: 
  - Browse all API endpoints
  - View request/response schemas
  - Test API calls directly from the browser
  - View authentication requirements

### ReDoc (Alternative Documentation)
- **URL**: `https://localhost/api/redoc` (or `https://your-domain/api/redoc`)
- **Description**: Clean, responsive API documentation
- **Features**:
  - Beautiful three-panel layout
  - Search functionality
  - Code samples
  - Download OpenAPI spec

### OpenAPI JSON Schema
- **URL**: `https://localhost/api/openapi.json` (or `https://your-domain/api/openapi.json`)
- **Description**: Raw OpenAPI 3.0 specification in JSON format
- **Use Cases**:
  - Import into API testing tools (Postman, Insomnia, etc.)
  - Generate client libraries
  - Automated API validation

## Direct Server Access (Development)

For development purposes, you can still access documentation directly from the server:

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
- OpenAPI JSON: `http://localhost:8080/openapi.json`

## Deployment Modes

### Production Setup (docker-compose-server.yml)
```bash
DOMAIN=nebula.local docker compose -f docker-compose-server.yml up -d
```
Access documentation at:
- `https://nebula.local/api/docs`
- `https://nebula.local/api/redoc`
- `https://nebula.local/api/openapi.json`

### Development Setup (development-docker-compose-server.yml)
```bash
DOMAIN=localhost docker compose -f development-docker-compose-server.yml up -d
```
Access documentation at:
- `https://localhost:4200/api/docs` (frontend on port 4200)
- `http://localhost:8080/docs` (direct server access)

## Authentication

The documentation endpoints themselves do not require authentication. However:

- **Public Endpoints**: Can be tested without authentication
- **Protected Endpoints**: Require authentication to test
- **Session-based Auth**: Login through the web UI first, then use Swagger UI
- **Token-based Auth**: Use the "Authorize" button in Swagger UI

## Testing API Endpoints from Swagger UI

1. Navigate to `https://localhost/api/docs`
2. If testing authenticated endpoints:
   - First login through the web UI (`/login`)
   - Your session cookie will be automatically sent with test requests
3. Expand an endpoint to see details
4. Click "Try it out" button
5. Fill in required parameters
6. Click "Execute" to make the request
7. View the response below

## Security Considerations

### Development
- Documentation is accessible without authentication
- Suitable for local development and testing

### Production
Consider adding authentication for documentation endpoints by:
1. Using nginx `auth_basic` for simple password protection
2. Restricting access by IP address
3. Disabling documentation in production (set `docs_url=None` in FastAPI)

Example nginx configuration for basic auth:
```nginx
location = /api/docs {
    auth_basic "API Documentation";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://api_upstream/docs;
    # ... other proxy headers ...
}
```

## Troubleshooting

### Documentation Not Loading
1. Verify containers are running: `docker compose ps`
2. Check nginx logs: `docker compose logs frontend`
3. Verify server is healthy: `curl -k https://localhost/api/v1/healthz`

### "Not Found" Errors
- Ensure you're using the correct URL path: `/api/docs` (not `/docs`)
- Check that both server and frontend containers are running
- Verify nginx configuration was applied: `docker compose restart frontend`

### Interactive Features Not Working
- Check browser console for JavaScript errors
- Verify CORS settings allow your domain
- Ensure session cookies are being sent (for authenticated endpoints)

## Related Files

- `frontend/nginx.conf` - Non-SSL proxy configuration
- `frontend/nginx-ssl.conf.template` - SSL proxy configuration template
- `server/app/main.py` - FastAPI application with docs configuration
