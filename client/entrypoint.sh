#!/usr/bin/env bash
set -euo pipefail

mkdir -p /etc/nebula /var/lib/nebula /app/.nebula

if [[ -z "${CLIENT_TOKEN:-}" ]]; then
  echo "CLIENT_TOKEN is required" >&2
  exit 1
fi

if [[ -z "${SERVER_URL:-}" ]]; then
  echo "SERVER_URL is required" >&2
  exit 1
fi

# Wait for server to be reachable
echo "Waiting for server at ${SERVER_URL}..."
for i in {1..60}; do
  if curl -sf "${SERVER_URL%/}/api/v1/healthz" >/dev/null; then
    break
  fi
  sleep 2
done

# Fetch or refresh config before starting nebula
python3 /app/agent.py --once

if [[ ! -f /etc/nebula/config.yml ]]; then
  echo "Config generation failed" >&2
  exit 1
fi

# If not explicitly starting Nebula, exit after generating config
if [[ "${START_NEBULA:-true}" != "true" ]]; then
  echo "Config generated at /etc/nebula/config.yml; not starting nebula (START_NEBULA!=true)."
  exit 0
fi

# Start background poller
python3 /app/agent.py --loop &

# Run nebula (from PATH, installed via apt)
exec nebula -config /etc/nebula/config.yml
