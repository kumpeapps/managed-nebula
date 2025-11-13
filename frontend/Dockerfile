# Multi-stage build: Node build + Nginx serve
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
LABEL org.opencontainers.image.source https://github.com/kumpeapps/managed-nebula
RUN npm install

# Copy source code and build
COPY . .
RUN npm run build:prod

# Production stage - nginx
FROM nginx:alpine

# Copy SSL-aware nginx template and entrypoint
COPY nginx-ssl.conf.template /etc/nginx/nginx-ssl.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy built Angular app from build stage
COPY --from=build /app/dist/managed-nebula-frontend /usr/share/nginx/html

# Expose ports 80 and 443
EXPOSE 80 443

CMD ["/docker-entrypoint.sh"]
