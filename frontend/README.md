# Managed Nebula Frontend

Modern Angular-based web interface for Managed Nebula VPN control plane.

## Features

- **Modern SPA Architecture**: Single-page application built with Angular 17
- **Full-Featured UI**: Manage clients, groups, firewall rules, and more
- **Session-Based Auth**: Secure cookie-based authentication with the backend
- **Responsive Design**: Works on desktop and mobile devices
- **Pre-Built Components**: All components, services, and guards included
- **Docker Ready**: Multi-stage build with nginx serving

## Quick Start

### Using Docker Compose (Recommended)

The frontend is automatically built and served when you start the stack:

```bash
docker-compose up -d
```

Access the frontend at: `http://localhost:4200`
Backend API available at: `http://localhost:8080`

### Local Development

For local development with live reload:

```bash
cd frontend
npm install
npm start
```

Then access at: `http://localhost:4200`

**Note**: The backend server must be running at `http://localhost:8080` for API calls to work.

## Architecture

### Components

- **LoginComponent**: Session-based login form
- **DashboardComponent**: Overview with statistics and recent clients
- **ClientsComponent**: CRUD operations for VPN clients
- **GroupsComponent**: Manage client groups

### Services

- **AuthService**: Handles authentication, login/logout, user state
- **ApiService**: REST API client for all backend endpoints

### Guards & Interceptors

- **AuthGuard**: Protects routes requiring authentication
- **AuthInterceptor**: Adds credentials to all requests, handles 401 errors

### Models

TypeScript interfaces for all API models (Client, Group, User, etc.)

## Configuration

### Backend URL

The nginx configuration proxies `/api/*` requests to the backend server. No CORS configuration needed!

### Environment Variables

None required for Docker deployment. For local development, ensure the backend is running on port 8080.

## Build Process

The Docker multi-stage build:

1. **Build Stage**: Installs npm dependencies, runs `ng build --configuration production`
2. **Serve Stage**: Copies built files to nginx, serves on port 80

## API Integration

The frontend communicates with the backend via:

- **Session Auth**: Login creates a session cookie
- **REST API**: All CRUD operations use `/api/v1/*` endpoints
- **Proxy**: Nginx proxies API calls to avoid CORS issues

## Customization

All components use inline templates and styles for simplicity. To customize:

1. Edit component files in `src/app/components/`
2. Rebuild: `docker-compose build frontend`
3. Restart: `docker-compose up -d frontend`

## Coexistence with Jinja2 UI

The Angular frontend **does not replace** the existing Jinja2 UI. Both are available:

- **Jinja2 UI**: `http://localhost:8080` (built into server container)
- **Angular UI**: `http://localhost:4200` (separate frontend container)

Choose whichever interface you prefer!

## Troubleshooting

### Frontend not loading

```bash
# Check frontend container logs
docker-compose logs frontend

# Rebuild if needed
docker-compose build frontend
docker-compose up -d frontend
```

### API calls failing

- Verify backend is running: `curl http://localhost:8080/api/v1/healthz`
- Check nginx proxy configuration in `nginx.conf`
- Review browser console for errors

### Login issues

- Ensure you've completed initial setup at `http://localhost:8080/setup`
- Check backend logs: `docker-compose logs server`
- Verify credentials are correct

## Development Workflow

1. **Make changes** to TypeScript files
2. **Test locally** with `npm start` (requires backend running)
3. **Build Docker** image: `docker build -t managed-nebula-frontend:latest .`
4. **Deploy** with docker-compose

## Tech Stack

- **Angular**: 17.0.0
- **TypeScript**: 5.2.2
- **RxJS**: 7.8.0
- **Nginx**: Alpine-based for serving
- **Node**: 20-alpine for building
