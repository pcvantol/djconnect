#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./deploy_ha_dev.sh [--config PATH] [--compose PATH] [--service NAME] [--container NAME] [--no-restart] [--dry-run]

Examples:
  ./deploy_ha_dev.sh
  ./deploy_ha_dev.sh --no-restart
  ./deploy_ha_dev.sh --config "$HOME/docker/homeassistant/config" --compose "$HOME/docker/homeassistant/compose.yaml"
  ./deploy_ha_dev.sh --dry-run

Syncs custom_components/djconnect into a local Home Assistant dev config,
verifies the installed manifest, restarts the Home Assistant container by
default, and prints container status.
EOF
}

CONFIG_DIR="${HOME}/docker/homeassistant/config"
COMPOSE_FILE=""
SERVICE_NAME="homeassistant"
CONTAINER_NAME="homeassistant"
RESTART=true
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      if [[ $# -lt 2 || -z "$2" ]]; then
        echo "--config requires a path." >&2
        exit 64
      fi
      CONFIG_DIR="${2%/}"
      shift 2
      ;;
    --compose)
      if [[ $# -lt 2 || -z "$2" ]]; then
        echo "--compose requires a path." >&2
        exit 64
      fi
      COMPOSE_FILE="$2"
      shift 2
      ;;
    --service)
      if [[ $# -lt 2 || -z "$2" ]]; then
        echo "--service requires a Docker Compose service name." >&2
        exit 64
      fi
      SERVICE_NAME="$2"
      shift 2
      ;;
    --container)
      if [[ $# -lt 2 || -z "$2" ]]; then
        echo "--container requires a Docker container name." >&2
        exit 64
      fi
      CONTAINER_NAME="$2"
      shift 2
      ;;
    --no-restart)
      RESTART=false
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 64
      ;;
  esac
done

if [[ ! -d ".git" || ! -f "custom_components/djconnect/manifest.json" ]]; then
  echo "Run this script from the djconnect repository root." >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required." >&2
  exit 1
fi

if [[ -z "$COMPOSE_FILE" ]]; then
  for candidate in \
    "${HOME}/docker/homeassistant/compose.yaml" \
    "${HOME}/docker/homeassistant/compose.yml" \
    "${HOME}/docker/homeassistant/docker-compose.yml" \
    "${HOME}/docker/homeassistant/docker-compose.yaml"
  do
    if [[ -f "$candidate" ]]; then
      COMPOSE_FILE="$candidate"
      break
    fi
  done
fi

DEST_DIR="${CONFIG_DIR}/custom_components/djconnect"
SOURCE_DIR="custom_components/djconnect/"

run() {
  echo "+ $*"
  if [[ "$DRY_RUN" == false ]]; then
    "$@"
  fi
}

run_shell() {
  echo "+ $*"
  if [[ "$DRY_RUN" == false ]]; then
    bash -lc "$*"
  fi
}

echo "DJConnect HA dev deploy"
echo "  source:    ${SOURCE_DIR}"
echo "  config:    ${CONFIG_DIR}"
echo "  target:    ${DEST_DIR}"
echo "  compose:   ${COMPOSE_FILE:-<not found>}"
echo "  service:   ${SERVICE_NAME}"
echo "  container: ${CONTAINER_NAME}"
echo "  restart:   ${RESTART}"
echo

if [[ ! -d "$CONFIG_DIR" ]]; then
  echo "Home Assistant config directory not found: ${CONFIG_DIR}" >&2
  exit 1
fi

if [[ "$RESTART" == true && -z "$COMPOSE_FILE" ]]; then
  echo "No Home Assistant compose file found. Pass --compose PATH or use --no-restart." >&2
  exit 1
fi

run mkdir -p "$(dirname "$DEST_DIR")"
run rsync -a --delete --delete-excluded \
  --exclude __pycache__ \
  --exclude '*.pyc' \
  "$SOURCE_DIR" \
  "${DEST_DIR}/"

run python3 -m json.tool "${DEST_DIR}/manifest.json" >/dev/null

if [[ "$DRY_RUN" == false ]]; then
  VERSION="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("custom_components/djconnect/manifest.json").read_text()).get("version", "unknown"))
PY
)"
  INSTALLED_VERSION="$(python3 - <<PY
import json
from pathlib import Path
print(json.loads(Path("${DEST_DIR}/manifest.json").read_text()).get("version", "unknown"))
PY
)"
  echo "Installed DJConnect manifest version: ${INSTALLED_VERSION} (repo: ${VERSION})"
fi

if [[ "$RESTART" == true ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker is required for restart. Re-run with --no-restart to only sync files." >&2
    exit 1
  fi
  run docker compose -f "$COMPOSE_FILE" up -d "$SERVICE_NAME"
  run docker restart "$CONTAINER_NAME"
  run docker ps --filter "name=${CONTAINER_NAME}" --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
  if [[ "$DRY_RUN" == false ]]; then
    run_shell "docker exec ${CONTAINER_NAME} python3 -c 'import custom_components.djconnect.const as c; print(\"Container DJConnect VERSION:\", c.VERSION)'"
  fi
fi

echo "HA dev deploy complete."
