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

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built Angular app from build stage
COPY --from=build /app/dist/managed-nebula-frontend /usr/share/nginx/html

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
