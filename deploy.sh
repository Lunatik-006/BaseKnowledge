#!/usr/bin/env bash
set -euo pipefail

# Deployment script for BaseKnowledge
# - Logs into GHCR using credentials from environment or ./.env
# - Pulls the latest images per docker-compose.yml
# - Restarts services with zero-downtime style (up -d)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load variables from .env for compose substitution and GHCR auth
if [ -f ./.env ]; then
  set -o allexport
  # shellcheck disable=SC1091
  source ./.env
  set +o allexport
fi

# Required for GHCR auth
: "${GHCR_USERNAME:=}"
: "${GHCR_TOKEN:=}"

if [ -z "${GHCR_USERNAME}" ] || [ -z "${GHCR_TOKEN}" ]; then
  echo "[deploy] GHCR_USERNAME and/or GHCR_TOKEN are not set." >&2
  echo "Add them to /root/BaseKnowledge/.env or export before running." >&2
  exit 1
fi

echo "[deploy] Docker login to ghcr.io as ${GHCR_USERNAME}"
echo "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USERNAME}" --password-stdin >/dev/null

echo "[deploy] Pulling images per docker-compose.yml"
docker compose pull

echo "[deploy] Starting/Updating services"
docker compose up -d --remove-orphans

echo "[deploy] Pruning unused images"
docker image prune -f >/dev/null || true

echo "[deploy] Done."

