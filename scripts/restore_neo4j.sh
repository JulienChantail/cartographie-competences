#!/usr/bin/env bash
set -euo pipefail

BACKUP_SOURCE=${1:-}
if [ -z "$BACKUP_SOURCE" ]; then
  echo "Usage: $0 <chemin_backup>"
  exit 1
fi

CONTAINER_NAME="cartographie-neo4j"

docker cp "$BACKUP_SOURCE" "$CONTAINER_NAME:/var/lib/neo4j/backups/"

docker exec "$CONTAINER_NAME" sh -c 'neo4j-admin database load --from=/var/lib/neo4j/backups/neo4j_backup --overwrite=true'

echo "Restauration lancée depuis $BACKUP_SOURCE"
