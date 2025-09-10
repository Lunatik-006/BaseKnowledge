#!/usr/bin/env bash
set -euo pipefail

# Deployment script for BaseKnowledge
# - Logs into GHCR using credentials from environment or ./.env
# - Pulls the latest images per docker-compose.yml
# - Restarts services with zero-downtime style (up -d)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure repo is up-to-date (requires the server clone to have origin configured)
if git rev-parse --git-dir >/dev/null 2>&1; then
  echo "[deploy] Updating repo from origin/main"
  git fetch --all --prune
  # Use main by default; adjust BRANCH env to override
  BRANCH_NAME=${BRANCH:-main}
  git checkout "$BRANCH_NAME" || true
  git reset --hard "origin/$BRANCH_NAME"
else
  echo "[deploy] Warning: not a git repo. Skipping git update." >&2
fi

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
