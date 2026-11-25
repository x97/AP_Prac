#!/usr/bin/env bash
set -euo pipefail

# Sync tracked source code to the server without pulling large assets.
#
# Usage:
#   SERVER=user@host ./infra/deploy/sync_code.sh
#
# Requires a commit (run this after `git commit`). The archive respects
# .gitattributes export-ignore, so source PDFs and _archive/ are not
# transferred; assets images/audio are included. Server-only files (.env,
# releases/, backups/, certs/, infra/deploy/nginx.conf) are protected from
# rsync --delete.

SERVER="${SERVER:?set SERVER=user@host}"
REMOTE_DIR="${REMOTE_DIR:-/srv/ap-psych}"
REF="${REF:-HEAD}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

git archive --format=tar "$REF" | tar -x -C "$TMP_DIR"

# Protect server-only files. Anchor /releases/ to the transfer root so source
# directories named "releases" (e.g. admin app routes) are still synced.
rsync -az --delete \
  --exclude='.env' \
  --exclude='/releases/' \
  --exclude='backups/' \
  --exclude='certs/' \
  --exclude='infra/deploy/nginx.conf' \
  "$TMP_DIR/" "$SERVER:$REMOTE_DIR/"

echo "code synced to $SERVER:$REMOTE_DIR (source PDFs and _archive excluded)"
