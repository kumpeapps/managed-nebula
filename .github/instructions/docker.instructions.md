---
applies_to:
  - "**/Dockerfile"
  - "**/docker-compose.yml"
  - "**/.dockerignore"
  - "**/entrypoint.sh"
---

# Docker and Containerization Instructions

## Overview
Managed Nebula uses Docker containers for all components (server, frontend, client). This document covers Docker-related patterns, best practices, and troubleshooting.

## Docker Architecture

### Images
- **Server**: FastAPI backend with Python 3.11, nebula-cert, and database drivers
- **Frontend**: Nginx serving Angular static build
- **Client**: Lightweight Python agent with nebula binary

### Container Registry
Pre-built images are available at:
- `ghcr.io/kumpeapps/managed-nebula/server:latest`
- `ghcr.io/kumpeapps/managed-nebula/frontend:latest`
- `ghcr.io/kumpeapps/managed-nebula/client:latest`

## Building Images

### Server Image
```bash
cd server
docker build -t managed-nebula-server:latest .

# With specific tag
docker build -t managed-nebula-server:v1.0.0 .

# Build and push to registry
docker build -t ghcr.io/kumpeapps/managed-nebula/server:latest .
docker push ghcr.io/kumpeapps/managed-nebula/server:latest
```

### Frontend Image
```bash
cd frontend
docker build -t managed-nebula-frontend:latest .

# Multi-stage build is used (build + serve stages)
```

### Client Image
```bash
cd client
docker build -t managed-nebula-client:latest .
```

## Dockerfile Best Practices

### Multi-Stage Builds
Use multi-stage builds to minimize final image size:

```dockerfile
# Build stage
FROM node:18 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build:prod

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
```

### Layer Caching
Order Dockerfile commands for optimal caching:

```dockerfile
# Good: Dependencies change less frequently than code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Bad: Code changes invalidate dependency cache
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
```

### Security
- Use specific base image versions (not `latest`)
- Run as non-root user when possible
- Use `.dockerignore` to exclude sensitive files
- Don't include secrets in images
- Scan images for vulnerabilities

```dockerfile
# Add non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Use specific version
FROM python:3.11-slim-bookworm
```

## Docker Compose

### Development Setup
```yaml
version: '3.8'

services:
  server:
    build: ./server
    ports:
      - "8080:8080"
    environment:
      - DB_URL=sqlite+aiosqlite:///./data/app.db
      - SECRET_KEY=dev-secret-key
      - ADMIN_EMAIL=admin@example.com
      - ADMIN_PASSWORD=admin
    volumes:
      - ./server/data:/app/data
      - ./server/app:/app/app  # Live reload
    depends_on:
      - postgres  # If using external DB
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "4200:80"
    depends_on:
      - server
    restart: unless-stopped
```

### Production Setup
```yaml
version: '3.8'

services:
  server:
    image: ghcr.io/kumpeapps/managed-nebula/server:latest
    ports:
      - "8080:8080"
    environment:
      - DB_URL=${DB_URL}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - server-data:/app/data
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: ghcr.io/kumpeapps/managed-nebula/frontend:latest
    ports:
      - "80:80"
    depends_on:
      - server
    restart: always

volumes:
  server-data:
```

## Running Containers

### Server
```bash
# Development (with volume mount for live reload)
docker run -d \
  --name nebula-server \
  -p 8080:8080 \
  -e DB_URL=sqlite+aiosqlite:///./app.db \
  -e SECRET_KEY=change-me \
  -e ADMIN_EMAIL=admin@example.com \
  -e ADMIN_PASSWORD=admin \
  -v $(pwd)/server/data:/app/data \
  managed-nebula-server:latest

# Production (with external PostgreSQL)
docker run -d \
  --name nebula-server \
  -p 8080:8080 \
  -e DB_URL=postgresql+asyncpg://user:pass@postgres:5432/db \
  -e SECRET_KEY=${SECRET_KEY} \
  managed-nebula-server:latest
```

### Frontend
```bash
docker run -d \
  --name nebula-frontend \
  -p 4200:80 \
  managed-nebula-frontend:latest
```

### Client
```bash
# Client requires special capabilities and devices
docker run -d \
  --name nebula-client \
  --cap-add=NET_ADMIN \
  --device /dev/net/tun \
  -e CLIENT_TOKEN=${CLIENT_TOKEN} \
  -e SERVER_URL=http://your-server:8080 \
  -e POLL_INTERVAL_HOURS=24 \
  -e START_NEBULA=true \
  managed-nebula-client:latest

# With persistent keypair
docker run -d \
  --name nebula-client \
  --cap-add=NET_ADMIN \
  --device /dev/net/tun \
  -e CLIENT_TOKEN=${CLIENT_TOKEN} \
  -e SERVER_URL=http://your-server:8080 \
  -v $(pwd)/nebula-keys:/var/lib/nebula \
  managed-nebula-client:latest
```

## Container Management

### Common Commands
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f server
docker logs -f nebula-server

# Execute command in container
docker exec -it nebula-server bash
docker-compose exec server bash

# Restart a service
docker-compose restart server

# Rebuild and restart
docker-compose up -d --build server
```

### Database Migrations
```bash
# Run migrations in container
docker exec -it nebula-server bash -c "cd /app && alembic upgrade head"
docker-compose exec server alembic upgrade head

# Create new migration
docker exec -it nebula-server bash -c "cd /app && alembic revision --autogenerate -m 'description'"
```

### Creating Admin User
```bash
# Interactive
docker exec -it nebula-server python manage.py create-admin admin@example.com

# Non-interactive
docker exec nebula-server python manage.py create-admin admin@example.com SecurePassword123
```

## Environment Variables

### Server Environment Variables
Required:
- `SECRET_KEY`: Session encryption key (⚠️ must be strong in production)

Optional:
- `DB_URL`: Database connection string (default: SQLite)
- `ADMIN_EMAIL`: Initial admin email (first startup only)
- `ADMIN_PASSWORD`: Initial admin password (first startup only)
- `CA_DEFAULT_VALIDITY_DAYS`: CA certificate validity (default: 540)
- `CA_ROTATE_AT_DAYS`: CA rotation threshold (default: 365)
- `CLIENT_CERT_VALIDITY_DAYS`: Client cert validity (default: 180)
- `LIGHTHOUSE_DEFAULT_PORT`: Default Nebula port (default: 4242)
- `ENABLE_SCHEMA_AUTOSYNC`: Auto-add columns (default: false)

### Client Environment Variables
Required:
- `CLIENT_TOKEN`: Authentication token from server
- `SERVER_URL`: Server API endpoint

Optional:
- `POLL_INTERVAL_HOURS`: Update check interval (default: 24)
- `START_NEBULA`: Auto-start Nebula daemon (default: true)

## Volumes and Persistence

### Server Data
```yaml
volumes:
  # SQLite database
  - ./server/data:/app/data
  
  # Certificate files (if storing on disk)
  - ./server/certs:/app/certs
  
  # Logs (if not using stdout)
  - ./server/logs:/app/logs
```

### Client Data
```yaml
volumes:
  # Persist keypair across container restarts
  - ./client/nebula-keys:/var/lib/nebula
  
  # Nebula config (if you want to inspect it)
  - ./client/nebula-config:/etc/nebula
```

## Networking

### Container Networking
```yaml
services:
  server:
    networks:
      - backend
  
  postgres:
    networks:
      - backend
  
  frontend:
    networks:
      - frontend
      - backend

networks:
  frontend:
  backend:
```

### Port Mapping
- Server: `8080:8080` (FastAPI)
- Frontend: `4200:80` (Nginx) or `80:80` (production)
- Client: No ports (outbound only)

## Health Checks

### Server Health Check
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Database Health Check
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 10s
  timeout: 5s
  retries: 5
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs nebula-server
docker-compose logs server

# Check if port is already in use
netstat -tuln | grep 8080
lsof -i :8080

# Inspect container
docker inspect nebula-server

# Check if image exists
docker images | grep nebula-server
```

### Database Connection Issues
```bash
# Test database connectivity
docker exec -it nebula-server python -c "from app.db import engine; print('DB OK')"

# Check database URL
docker exec nebula-server printenv DB_URL

# Test PostgreSQL connection
docker exec -it postgres-container psql -U username -d database
```

### Client Network Issues
```bash
# Check if TUN device exists
docker exec nebula-client ls -l /dev/net/tun

# Check capabilities
docker exec nebula-client capsh --print | grep net_admin

# Test Nebula config
docker exec nebula-client nebula -test -config /etc/nebula/config.yml

# Check Nebula process
docker exec nebula-client ps aux | grep nebula
```

### Performance Issues
```bash
# Check resource usage
docker stats

# Limit resources
docker run -d \
  --memory=512m \
  --cpus=1.0 \
  managed-nebula-server

# In docker-compose:
services:
  server:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
```

## Best Practices

### DO's ✅
- **Use docker-compose for orchestration**: Easier than managing individual containers
- **Use named volumes**: Better than bind mounts for production
- **Set restart policies**: Ensure services recover from failures
- **Use health checks**: Monitor service health
- **Tag images properly**: Use semantic versioning
- **Use .dockerignore**: Exclude unnecessary files from build context
- **Run as non-root**: Improve security when possible
- **Use multi-stage builds**: Reduce final image size
- **Set resource limits**: Prevent resource exhaustion
- **Use secrets management**: Never hardcode secrets

### DON'Ts ❌
- ❌ Don't use `latest` tag in production
- ❌ Don't hardcode secrets in Dockerfiles or compose files
- ❌ Don't run as root unless necessary
- ❌ Don't include build artifacts in final image
- ❌ Don't use `--privileged` unless absolutely necessary
- ❌ Don't forget to clean up unused images/containers
- ❌ Don't expose unnecessary ports
- ❌ Don't skip health checks in production
- ❌ Don't use development images in production

## Security Considerations

### Image Security
```bash
# Scan for vulnerabilities
docker scan managed-nebula-server:latest

# Use minimal base images
FROM python:3.11-slim-bookworm  # Not python:3.11

# Keep images updated
docker pull python:3.11-slim-bookworm
docker-compose build --pull
```

### Runtime Security
```yaml
# Read-only root filesystem
services:
  server:
    read_only: true
    tmpfs:
      - /tmp
      - /app/temp

# Drop capabilities
services:
  server:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if needed
```

### Secrets Management
```bash
# Use Docker secrets (Swarm mode)
echo "my-secret" | docker secret create db_password -

# Use environment file (not committed to git)
docker-compose --env-file .env.production up -d

# Use external secret management (Vault, AWS Secrets Manager)
```

## CI/CD Integration

### Building and Pushing Images
```yaml
name: Build and Push

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push server
        uses: docker/build-push-action@v4
        with:
          context: ./server
          push: true
          tags: |
            ghcr.io/kumpeapps/managed-nebula/server:latest
            ghcr.io/kumpeapps/managed-nebula/server:${{ github.ref_name }}
```

## Docker Compose Profiles

Use profiles to run different configurations:

```yaml
services:
  server:
    # Always runs
    
  postgres:
    profiles: ["production"]
    # Only with: docker-compose --profile production up
  
  dev-tools:
    profiles: ["dev"]
    # Only with: docker-compose --profile dev up
```

## Cleanup

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything unused
docker system prune -a --volumes

# Stop and remove compose project
docker-compose down -v  # Include volumes
```
