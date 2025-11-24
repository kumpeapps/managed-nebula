#!/bin/sh
set -euo pipefail

CERT_NAME="${SSL_CERT_NAME:-tls.crt}"
KEY_NAME="${SSL_KEY_NAME:-tls.key}"
DOMAIN_NAME="${DOMAIN:-localhost}"
CERT_DIR="/etc/nginx/certs"

mkdir -p "$CERT_DIR"

if [ ! -f "$CERT_DIR/$CERT_NAME" ] || [ ! -f "$CERT_DIR/$KEY_NAME" ]; then
  echo "[entrypoint] Generating self-signed certificate for $DOMAIN_NAME"
  if ! command -v openssl >/dev/null 2>&1; then
    apk add --no-cache openssl >/dev/null
  fi
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$CERT_DIR/$KEY_NAME" \
    -out "$CERT_DIR/$CERT_NAME" \
    -subj "/CN=$DOMAIN_NAME"
  chmod 600 "$CERT_DIR/$KEY_NAME" || true
fi

# Inject API_TEST_DELAY into environment.js if it exists
API_TEST_DELAY="${API_TEST_DELAY:-0}"
if [ -f "/usr/share/nginx/html/assets/environment.js" ]; then
  echo "[entrypoint] Setting API_TEST_DELAY to ${API_TEST_DELAY}ms"
  sed -i "s/apiTestDelay = [0-9]*/apiTestDelay = ${API_TEST_DELAY}/" \
    /usr/share/nginx/html/assets/environment.js
fi

# Render nginx.conf from template
sed "s#__CERT_NAME__#${CERT_NAME}#g; s#__KEY_NAME__#${KEY_NAME}#g" \
  /etc/nginx/nginx-ssl.conf.template > /etc/nginx/nginx.conf

# Test and start nginx
nginx -t
exec nginx -g "daemon off;"
