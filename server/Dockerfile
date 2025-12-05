# syntax=docker/dockerfile:1.6
FROM python:3.12-slim

ARG VERSION=dev-latest

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_VERSION=${VERSION}
LABEL org.opencontainers.image.source https://github.com/kumpeapps/managed-nebula
RUN set -eux; \
        apt-get update; \
        apt-get install -y --no-install-recommends \
            ca-certificates curl \
            build-essential gcc python3-dev libffi-dev libssl-dev pkg-config \
            libpq5 libpq-dev \
            default-libmysqlclient-dev \
            nano \
            rustc cargo; \
        echo "Installing Nebula v1.10.0 from upstream release (Debian package is outdated)";
        arch="$(dpkg --print-architecture)";
        case "$arch" in \
            amd64) neb_arch="amd64" ;; \
            arm64) neb_arch="arm64" ;; \
            armhf|armel|arm) neb_arch="arm" ;; \
            *) echo "Unsupported architecture: $arch"; exit 1 ;; \
        esac; \
        NEBULA_VERSION="1.10.0"; \
        curl -fsSL -o /tmp/nebula.tar.gz "https://github.com/slackhq/nebula/releases/download/v${NEBULA_VERSION}/nebula-linux-${neb_arch}.tar.gz"; \
        tar -C /usr/local/bin -xzvf /tmp/nebula.tar.gz nebula nebula-cert; \
        rm -f /tmp/nebula.tar.gz; \
        rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
# Reduce parallelism during builds to avoid OOM/segfault on constrained builders (especially ARM/QEMU)
ENV MAKEFLAGS="-j1"

# Install build dependencies for greenlet and other C extensions
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cargo/registry \
    --mount=type=cache,target=/root/.cargo/git \
    pip install --upgrade pip setuptools wheel && \
    # Install greenlet separately first with verbose output for debugging
    pip install --verbose greenlet==3.0.0 && \
    # Then install remaining requirements
    pip install --prefer-binary -r /app/requirements.txt

COPY . /app

# Provide systemd unit templates and installer script inside the image for host installation
RUN mkdir -p /opt/managed-nebula/systemd
COPY systemd/*.service.tpl /opt/managed-nebula/systemd/
COPY install-systemd-service.sh /opt/managed-nebula/
RUN chmod +x /opt/managed-nebula/install-systemd-service.sh

ENV APP_ENV=production \
    DB_URL=sqlite+aiosqlite:///./app.db \
    SECRET_KEY=change-me \
    ACCESS_TOKEN_EXPIRE_MINUTES=60 \
    CA_DEFAULT_VALIDITY_DAYS=540 \
    CA_ROTATE_AT_DAYS=365 \
    CA_OVERLAP_DAYS=90 \
    CLIENT_CERT_VALIDITY_DAYS=180 \
    CLIENT_ROTATE_BEFORE_DAYS=90

EXPOSE 8080

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
