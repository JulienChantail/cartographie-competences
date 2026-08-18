#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose up --build -d

echo "Stack démarrée."
echo "Frontend: http://localhost"
echo "Backend: http://localhost:8000/docs"
echo "Neo4j Browser: http://localhost:7474"
