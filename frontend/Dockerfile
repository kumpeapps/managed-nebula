# Multi-stage build: Node build + Nginx serve
# Use Node LTS for better stability and ARM64 performance
FROM node:22-alpine AS build

ARG VERSION=dev-latest

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
LABEL org.opencontainers.image.source=https://github.com/kumpeapps/managed-nebula

# Install dependencies with retry logic for network reliability
# Increase timeouts and retry on failure (common in CI/CD for ARM64 builds)
RUN npm config set fetch-timeout 300000 && \
    npm config set fetch-retries 5 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000 && \
    npm ci --no-audit --no-fund || \
    (echo "First attempt failed, retrying..." && sleep 10 && npm ci --no-audit --no-fund) || \
    (echo "Second attempt failed, retrying..." && sleep 20 && npm ci --no-audit --no-fund)

# Copy source code and build
COPY . .

# Update version in environment files
RUN sed -i "s/version: '.*'/version: '${VERSION}'/" src/environments/environment.ts && \
    sed -i "s/version: '.*'/version: '${VERSION}'/" src/environments/environment.prod.ts

# Build with optimizations for ARM64 (slower architecture in CI/CD)
# Increase Node.js memory limit and reduce parallelization to prevent hangs
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Add build progress monitoring to detect actual hangs vs slow builds
RUN echo "Starting Angular build (this may take 10-20 minutes on ARM64)..." && \
    echo "Build started at: $(date)" && \
    (timeout 1800 npm run build:prod -- --progress=true || \
     (echo "Build timed out or failed after 30 minutes, retrying with reduced optimization..." && \
      timeout 1800 npm run build:prod -- --progress=true --optimization=false)) && \
    echo "Build completed at: $(date)"


# Production stage - nginx
FROM nginx:alpine

# Copy SSL-aware nginx template and entrypoint
COPY nginx-ssl.conf.template /etc/nginx/nginx-ssl.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Provide systemd unit template and installer script inside the image for host installation
RUN mkdir -p /opt/managed-nebula/systemd
COPY systemd/*.service.tpl /opt/managed-nebula/systemd/
COPY install-systemd-service.sh /opt/managed-nebula/
RUN chmod +x /opt/managed-nebula/install-systemd-service.sh

# Copy built Angular app from build stage
COPY --from=build /app/dist/managed-nebula-frontend /usr/share/nginx/html

# Create environment.js for runtime configuration
RUN mkdir -p /usr/share/nginx/html/assets && \
    echo "window.__env = window.__env || {}; window.__env.apiTestDelay = 0;" > /usr/share/nginx/html/assets/environment.js

# Expose ports 80 and 443
EXPOSE 80 443

CMD ["/docker-entrypoint.sh"]
