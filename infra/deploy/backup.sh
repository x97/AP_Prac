#!/usr/bin/env bash
set -euo pipefail

# Run on the server (or adapt to your backup host).
COMPOSE_DIR="${COMPOSE_DIR:-/srv/ap-psych/infra/compose}"
BACKUP_DIR="${BACKUP_DIR:-/srv/ap-psych/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"
docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T postgres \
  pg_dump -U ap_psych -d ap_psych \
  | gzip > "$BACKUP_DIR/ap_psych-$STAMP.sql.gz"

find "$BACKUP_DIR" -name 'ap_psych-*.sql.gz' -type f -mtime +"$KEEP_DAYS" -delete
echo "backup written: $BACKUP_DIR/ap_psych-$STAMP.sql.gz"
