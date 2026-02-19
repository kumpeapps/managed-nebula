# Multi-stage build: Node build + Nginx serve
# Use Node 20 LTS for better QEMU ARM64 emulation compatibility
FROM node:20-alpine AS build

ARG VERSION=dev-latest

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
LABEL org.opencontainers.image.source=https://github.com/kumpeapps/managed-nebula

# Install dependencies with increased timeouts for ARM64 QEMU emulation
# Node 20 LTS has better QEMU compatibility than Node 22
RUN npm config set fetch-timeout 300000 && \
    npm config set fetch-retries 3 && \
    npm ci --no-audit --no-fund

# Copy source code and build
COPY . .

# Update version in environment files
RUN sed -i "s/version: '.*'/version: '${VERSION}'/" src/environments/environment.ts && \
    sed -i "s/version: '.*'/version: '${VERSION}'/" src/environments/environment.prod.ts

# Build Angular app with increased memory for ARM64 builds
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm run build:prod


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
