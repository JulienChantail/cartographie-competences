#!/usr/bin/env bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$(pwd)/backups"
BACKUP_PATH="$BACKUP_DIR/neo4j_backup_${TIMESTAMP}"
mkdir -p "$BACKUP_PATH"

CONTAINER_NAME="cartographie-neo4j"
TMP_CONTAINER="neo4j-backup-tmp-$$"

# neo4j-admin ne peut pas sauvegarder une base montée dans un serveur Neo4j en
# cours d'exécution (STOP DATABASE / sauvegarde en ligne : fonctionnalités
# Neo4j Enterprise, absentes de l'édition Community utilisée par ce projet).
# On arrête donc brièvement le conteneur le temps du dump (quelques secondes
# en pratique), via un conteneur temporaire basé sur la même image et le
# même volume de données.
DATA_VOLUME=$(docker inspect "$CONTAINER_NAME" --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}')
IMAGE=$(docker inspect "$CONTAINER_NAME" --format '{{.Config.Image}}')

if [ -z "$DATA_VOLUME" ]; then
  echo "Impossible de déterminer le volume de données de $CONTAINER_NAME (le conteneur est-il démarré ?)" >&2
  exit 1
fi

echo "Arrêt de $CONTAINER_NAME pour la sauvegarde (hors ligne, requis en édition Community)..."
docker stop "$CONTAINER_NAME" >/dev/null

cleanup() {
  echo "Redémarrage de $CONTAINER_NAME..."
  docker start "$CONTAINER_NAME" >/dev/null
}
trap cleanup EXIT

docker rm -f "$TMP_CONTAINER" >/dev/null 2>&1 || true
docker create --name "$TMP_CONTAINER" -v "$DATA_VOLUME":/data "$IMAGE" \
  sh -c 'mkdir -p /tmp/dumps && neo4j-admin database dump "*" --to-path=/tmp/dumps --overwrite-destination=true'

docker start -a "$TMP_CONTAINER"
docker cp "$TMP_CONTAINER:/tmp/dumps/." "$BACKUP_PATH/"
docker rm "$TMP_CONTAINER" >/dev/null

echo "Sauvegarde créée dans $BACKUP_PATH"
ls -la "$BACKUP_PATH"
