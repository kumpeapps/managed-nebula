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

# Try to wait for server, but don't block forever if we have existing config
SERVER_REACHABLE=false
CURL_OPTS="-sfL"
if [[ "${ALLOW_SELF_SIGNED_CERT:-false}" == "true" ]]; then
  CURL_OPTS="-ksfL"
fi

if [[ -f /etc/nebula/config.yml ]]; then
  echo "Existing config found, will attempt quick server check..."
  for i in {1..5}; do
    if curl $CURL_OPTS "${SERVER_URL%/}/v1/healthz" >/dev/null 2>&1; then
      SERVER_REACHABLE=true
      echo "Server is reachable"
      break
    fi
    sleep 2
  done

  if [[ "$SERVER_REACHABLE" == "false" ]]; then
    echo "Server unreachable, will use existing config and retry during polling"
  fi
else
  echo "No existing config found, waiting for server at ${SERVER_URL}..."
  for i in {1..60}; do
    if curl $CURL_OPTS "${SERVER_URL%/}/v1/healthz" >/dev/null 2>&1; then
      SERVER_REACHABLE=true
      echo "Server is reachable"
      break
    fi
    sleep 2
  done

  if [[ "$SERVER_REACHABLE" == "false" ]]; then
    echo "ERROR: Server unreachable and no existing config available" >&2
    exit 1
  fi
fi

# Fetch or refresh config when possible; fall back to existing config when offline
if [[ "$SERVER_REACHABLE" == "true" ]] || [[ ! -f /etc/nebula/config.yml ]]; then
  echo "Fetching initial config from server..."
  python3 /app/agent.py --once || {
    if [[ -f /etc/nebula/config.yml ]]; then
      echo "Config fetch failed but existing config available, continuing with existing config"
    else
      echo "Config generation failed and no existing config available" >&2
      exit 1
    fi
  }
else
  echo "Using existing config, will fetch updates during polling loop"
fi

if [[ ! -f /etc/nebula/config.yml ]]; then
  echo "ERROR: Config file does not exist and could not be generated" >&2
  exit 1
fi

# If not explicitly starting Nebula, exit after generating config
if [[ "${START_NEBULA:-true}" != "true" ]]; then
  echo "Config generated at /etc/nebula/config.yml; not starting nebula (START_NEBULA!=true)."
  exit 0
fi

# Shared cleanup function for both enhanced and legacy modes
cleanup() {
    echo "Shutting down..."
    
    # Best-effort stop of whichever background processes are in use
    if [[ -n "${AGENT_PID:-}" ]]; then
        kill "${AGENT_PID}" 2>/dev/null || true
    fi
    if [[ -n "${POLLER_PID:-}" ]]; then
        kill "${POLLER_PID}" 2>/dev/null || true
    fi

    # Stop nebula if running
    if [[ -f /var/lib/nebula/nebula.pid ]]; then
        NEBULA_PID="$(cat /var/lib/nebula/nebula.pid)"
        kill "${NEBULA_PID}" 2>/dev/null || true
        rm -f /var/lib/nebula/nebula.pid
    fi

    exit 0
}

# Set up signal handlers for both modes
trap cleanup SIGINT SIGTERM

# Use enhanced monitoring mode if ENABLE_MONITORING is true (default)
ENABLE_MONITORING="${ENABLE_MONITORING:-true}"

if [[ "${ENABLE_MONITORING}" == "true" ]]; then
  echo "Starting agent in enhanced monitoring mode..."
  # Enhanced mode handles both config polling and process monitoring
  python3 /app/agent.py --monitor &
  AGENT_PID=$!
  
  # Agent's monitor mode will start Nebula automatically
  # Just wait for the agent process
  wait $AGENT_PID
else
  echo "Starting agent in legacy mode (no process monitoring)..."
  # Start background poller
  python3 /app/agent.py --loop &
  POLLER_PID=$!
  
  # Start nebula and track its PID
  nebula -config /etc/nebula/config.yml &
  NEBULA_PID=$!
  echo $NEBULA_PID > /var/lib/nebula/nebula.pid
  
  # Wait for either process to exit
  wait
fi
