#!/usr/bin/env bash
set -euo pipefail

# Usage: ./deploy_release.sh content-20261030-01
# Requires: SERVER=user@host, REMOTE_DIR=/srv/ap-psych, COMPOSE_DIR=/srv/ap-psych/infra/compose
RELEASE_ID="${1:?release id required}"
SERVER="${SERVER:?set SERVER=user@host}"
REMOTE_DIR="${REMOTE_DIR:-/srv/ap-psych}"
COMPOSE_DIR="${COMPOSE_DIR:-$REMOTE_DIR/infra/compose}"
LOCAL_RELEASE="$(cd "$(dirname "$0")/../.." && pwd)/data/releases/$RELEASE_ID"

if [ ! -d "$LOCAL_RELEASE" ]; then
  echo "release not found: $LOCAL_RELEASE" >&2
  exit 2
fi

rsync -az --delete "$LOCAL_RELEASE/" "$SERVER:$REMOTE_DIR/releases/$RELEASE_ID/"

ssh "$SERVER" bash -s <<EOF
set -euo pipefail
ln -sfn "$REMOTE_DIR/releases/$RELEASE_ID" "$REMOTE_DIR/releases/active"
ln -sfn "$REMOTE_DIR/releases/$RELEASE_ID" "$REMOTE_DIR/releases/current"
docker compose -f "$COMPOSE_DIR/docker-compose.yml" restart api worker
sleep 2
curl -fsS http://127.0.0.1/api/v1/content/version >/dev/null
echo "activated $RELEASE_ID"
EOF
