#!/usr/bin/env bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$(pwd)/backups"
mkdir -p "$BACKUP_DIR"

CONTAINER_NAME="cartographie-neo4j"
BACKUP_PATH="$BACKUP_DIR/neo4j_backup_${TIMESTAMP}"

mkdir -p "$BACKUP_PATH"

docker exec "$CONTAINER_NAME" sh -c 'mkdir -p /var/lib/neo4j/backups && /bin/neo4j-admin database dump --to=/var/lib/neo4j/backups/neo4j_backup' 

docker cp "$CONTAINER_NAME:/var/lib/neo4j/backups/neo4j_backup" "$BACKUP_PATH"

echo "Sauvegarde créée dans $BACKUP_PATH"
