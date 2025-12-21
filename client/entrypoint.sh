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
CURL_OPTS="-sfL"
if [[ "${ALLOW_SELF_SIGNED_CERT:-false}" == "true" ]]; then
  CURL_OPTS="-ksfL"
fi
for i in {1..60}; do
  if curl $CURL_OPTS "${SERVER_URL%/}/v1/healthz" >/dev/null; then
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

# Use enhanced monitoring mode if ENABLE_MONITORING is true (default)
ENABLE_MONITORING="${ENABLE_MONITORING:-true}"

if [[ "${ENABLE_MONITORING}" == "true" ]]; then
  echo "Starting agent in enhanced monitoring mode..."
  # Enhanced mode handles both config polling and process monitoring
  python3 /app/agent.py --monitor &
  AGENT_PID=$!
  
  # Function to handle shutdown signals
  cleanup() {
      echo "Shutting down..."
      kill $AGENT_PID 2>/dev/null || true
      
      # Stop nebula if running
      if [[ -f /var/lib/nebula/nebula.pid ]]; then
          NEBULA_PID=$(cat /var/lib/nebula/nebula.pid)
          kill $NEBULA_PID 2>/dev/null || true
          rm -f /var/lib/nebula/nebula.pid
      fi
      exit 0
  }
  
  # Set up signal handlers
  trap cleanup SIGTERM SIGINT
  
  # Agent's monitor mode will start Nebula automatically
  # Just wait for the agent process
  wait $AGENT_PID
else
  echo "Starting agent in legacy mode (no process monitoring)..."
  # Start background poller
  python3 /app/agent.py --loop &
  POLLER_PID=$!
  
  # Function to handle shutdown signals
  cleanup() {
      echo "Shutting down..."
      kill $POLLER_PID 2>/dev/null || true
      
      # Stop nebula if running
      if [[ -f /var/lib/nebula/nebula.pid ]]; then
          NEBULA_PID=$(cat /var/lib/nebula/nebula.pid)
          kill $NEBULA_PID 2>/dev/null || true
          rm -f /var/lib/nebula/nebula.pid
      fi
      exit 0
  }
  
  # Set up signal handlers
  trap cleanup SIGTERM SIGINT
  
  # Start nebula and track its PID
  nebula -config /etc/nebula/config.yml &
  NEBULA_PID=$!
  echo $NEBULA_PID > /var/lib/nebula/nebula.pid
  
  # Wait for either process to exit
  wait
fi
