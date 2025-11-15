#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 <server|client> [--activate] [--render <path>]

Generates and installs a systemd service for the running Docker Compose service
by copying a template from the container image and rendering it with metadata
from 'docker inspect' (compose working dir, compose files, project, service).

Options:
  --activate   Run 'systemctl daemon-reload' and 'enable --now' the unit
  --render     Render unit to the given path and skip installation

Examples:
  $0 server --activate
  $0 client
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" || $# -lt 1 ]]; then
  usage
  exit 0
fi

SERVICE="$1"
ACTIVATE=false
RENDER_PATH=""

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --activate)
      ACTIVATE=true
      shift
      ;;
    --render)
      RENDER_PATH="${2:-}"
      if [[ -z "$RENDER_PATH" ]]; then
        echo "Error: --render requires a path argument" >&2
        exit 1
      fi
      shift 2
      ;;
    -h|--help)
      usage; exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2; usage; exit 1
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker CLI not found on PATH" >&2
  exit 1
fi

# Find a running container for the compose service
CID=$(docker ps -q -f "label=com.docker.compose.service=${SERVICE}" | head -n1 || true)
if [[ -z "$CID" ]]; then
  # fallback: match by container name suffix
  CID=$(docker ps -q --format '{{.ID}} {{.Names}}' | awk -v s="$SERVICE" '$2 ~ ("_" s "_") { print $1; exit }')
fi

if [[ -z "$CID" ]]; then
  echo "Error: could not find a running container for service '$SERVICE'" >&2
  exit 1
fi

label() {
  local key="$1"
  docker inspect -f "{{ index .Config.Labels \"$key\" }}" "$CID" 2>/dev/null || true
}

WORKDIR="$(label com.docker.compose.project.working_dir)"
CONFIG_FILES_RAW="$(label com.docker.compose.project.config_files)"
PROJECT_NAME="$(label com.docker.compose.project)"
SERVICE_NAME="$(label com.docker.compose.service)"

if [[ -z "$WORKDIR" || -z "$CONFIG_FILES_RAW" || -z "$PROJECT_NAME" || -z "$SERVICE_NAME" ]]; then
  echo "Error: missing compose metadata labels on container; is it started via docker compose?" >&2
  exit 1
fi

# Build '-f <file>' flags for each compose file
IFS=',;:' read -r -a CF_ARR <<< "$CONFIG_FILES_RAW"
COMPOSE_FILES_FLAGS=""
for f in "${CF_ARR[@]}"; do
  # trim whitespace
  f="${f##*[[:space:]]}"
  f="${f%%*[[:space:]]}"
  [[ -z "$f" ]] && continue
  if [[ "$f" = /* ]]; then
    path="$f"
  else
    path="$WORKDIR/$f"
  fi
  COMPOSE_FILES_FLAGS+=" -f $path"
done

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
TPL_SOURCE="/opt/managed-nebula/systemd/managed-nebula-${SERVICE_NAME}.service.tpl"
LOCAL_TPL="$TMPDIR/unit.tpl"

if docker cp "$CID:$TPL_SOURCE" "$LOCAL_TPL" >/dev/null 2>&1; then
  :
elif [[ -f "$(pwd)/${SERVICE}/systemd/managed-nebula-${SERVICE}.service.tpl" ]]; then
  cp "$(pwd)/${SERVICE}/systemd/managed-nebula-${SERVICE}.service.tpl" "$LOCAL_TPL"
else
  echo "Error: could not locate a template in the container or repository" >&2
  exit 1
fi

# Render placeholders
ESC_WORKDIR="${WORKDIR//\//\\/}"
ESC_PROJECT="${PROJECT_NAME//\//\\/}"
ESC_SERVICE="${SERVICE_NAME//\//\\/}"
ESC_FLAGS="${COMPOSE_FILES_FLAGS//\//\\/}"

RENDERED="$TMPDIR/managed-nebula-${SERVICE_NAME}.service"
sed -e "s|{{COMPOSE_WORKING_DIR}}|$ESC_WORKDIR|g" \
    -e "s|{{COMPOSE_PROJECT_NAME}}|$ESC_PROJECT|g" \
    -e "s|{{COMPOSE_SERVICE_NAME}}|$ESC_SERVICE|g" \
    -e "s|{{COMPOSE_FILES_FLAGS}}|$ESC_FLAGS|g" \
    "$LOCAL_TPL" > "$RENDERED"

UNIT_NAME="managed-nebula-${SERVICE_NAME}.service"
DEST="/etc/systemd/system/$UNIT_NAME"

if [[ -n "$RENDER_PATH" ]]; then
  mkdir -p "$(dirname "$RENDER_PATH")"
  cp "$RENDERED" "$RENDER_PATH"
  echo "Rendered unit written to: $RENDER_PATH"
  echo "Done."
  exit 0
fi

echo "Installing unit to $DEST (requires sudo)"
if ! sudo install -m 0644 -D "$RENDERED" "$DEST"; then
  echo "Error: failed to install unit file to $DEST" >&2
  exit 1
fi

if command -v systemctl >/dev/null 2>&1; then
  echo "Running: sudo systemctl daemon-reload"
  sudo systemctl daemon-reload || true
  if $ACTIVATE; then
    echo "Enabling and starting $UNIT_NAME"
    sudo systemctl enable --now "$UNIT_NAME" || true
  else
    echo "Unit installed. To enable/start:"
    echo "  sudo systemctl enable --now $UNIT_NAME"
  fi
else
  echo "systemctl not found; skipped daemon-reload and enable."
fi

echo "Done."
