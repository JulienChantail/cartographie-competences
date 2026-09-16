#!/usr/bin/env bash
set -euo pipefail

BACKUP_SOURCE=${1:-}
if [ -z "$BACKUP_SOURCE" ]; then
  echo "Usage: $0 <chemin_vers_un_dossier_contenant_neo4j.dump_et/ou_system.dump>"
  echo "  (ex: ./scripts/restore_neo4j.sh backups/neo4j_backup_20260916_140957)"
  exit 1
fi
if [ ! -d "$BACKUP_SOURCE" ]; then
  echo "Le chemin '$BACKUP_SOURCE' n'existe pas ou n'est pas un dossier." >&2
  exit 1
fi

CONTAINER_NAME="cartographie-neo4j"
TMP_CONTAINER="neo4j-restore-tmp-$$"

# Comme pour la sauvegarde, neo4j-admin ne peut pas charger une base dans un
# serveur Neo4j en cours d'exécution (édition Community). Le conteneur est
# donc arrêté le temps de la restauration puis redémarré.
DATA_VOLUME=$(docker inspect "$CONTAINER_NAME" --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}')
IMAGE=$(docker inspect "$CONTAINER_NAME" --format '{{.Config.Image}}')

if [ -z "$DATA_VOLUME" ]; then
  echo "Impossible de déterminer le volume de données de $CONTAINER_NAME (le conteneur est-il démarré ?)" >&2
  exit 1
fi

echo "⚠️  Cette opération remplace entièrement le contenu actuel de la base Neo4j."
echo "Arrêt de $CONTAINER_NAME pour la restauration (hors ligne, requis en édition Community)..."
docker stop "$CONTAINER_NAME" >/dev/null

cleanup() {
  echo "Redémarrage de $CONTAINER_NAME..."
  docker start "$CONTAINER_NAME" >/dev/null
}
trap cleanup EXIT

docker rm -f "$TMP_CONTAINER" >/dev/null 2>&1 || true
docker create --name "$TMP_CONTAINER" -v "$DATA_VOLUME":/data "$IMAGE" \
  sh -c 'neo4j-admin database load "*" --from-path=/tmp --overwrite-destination=true'

for f in "$BACKUP_SOURCE"/*.dump; do
  [ -e "$f" ] || continue
  docker cp "$f" "$TMP_CONTAINER:/tmp/$(basename "$f")"
done

docker start -a "$TMP_CONTAINER"
docker rm "$TMP_CONTAINER" >/dev/null

echo "Restauration terminée depuis $BACKUP_SOURCE"
