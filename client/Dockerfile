# syntax=docker/dockerfile:1.6
FROM python:3.11-slim
LABEL org.opencontainers.image.source https://github.com/kumpeapps/managed-nebula

RUN set -eux; \
        apt-get update; \
        apt-get install -y --no-install-recommends \
            ca-certificates curl iproute2 iputils-ping \
            build-essential gcc python3-dev libffi-dev libssl-dev pkg-config \
            rustc cargo; \
        if ! apt-get install -y --no-install-recommends nebula; then \
            echo "Debian package 'nebula' not found; installing from upstream release"; \
            arch="$(dpkg --print-architecture)"; \
            case "$arch" in \
                amd64) neb_arch="amd64" ;; \
                arm64) neb_arch="arm64" ;; \
                armhf|armel|arm) neb_arch="arm" ;; \
                *) echo "Unsupported architecture: $arch"; exit 1 ;; \
            esac; \
            NEBULA_VERSION="1.9.7"; \
            curl -fsSL -o /tmp/nebula.tar.gz "https://github.com/slackhq/nebula/releases/download/v${NEBULA_VERSION}/nebula-linux-${neb_arch}.tar.gz"; \
            tar -C /usr/local/bin -xzvf /tmp/nebula.tar.gz nebula nebula-cert; \
            rm -f /tmp/nebula.tar.gz; \
        fi; \
        rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cargo/registry \
    --mount=type=cache,target=/root/.cargo/git \
    pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --prefer-binary -r /app/requirements.txt

COPY . /app
RUN chmod +x /app/entrypoint.sh

ENV CLIENT_TOKEN="" \
    SERVER_URL="http://server:8080" \
    POLL_INTERVAL_HOURS=24

VOLUME ["/etc/nebula", "/var/lib/nebula"]
COPY install-systemd-service.sh /etc/nebula/install-systemd-service.sh
# Provide systemd unit templates and installer script inside the image for host installation
RUN mkdir -p /opt/managed-nebula/systemd
COPY systemd/*.service.tpl /opt/managed-nebula/systemd/
COPY install-systemd-service.sh /opt/managed-nebula/
RUN chmod +x /opt/managed-nebula/install-systemd-service.sh

ENTRYPOINT ["/app/entrypoint.sh"]
