#!/bin/bash
set -e

echo "🔄 Deteniendo contenedores..."
docker compose down

echo "🧱 Reconstruyendo imágenes..."
docker compose build --no-cache

echo "🚀 Levantando aplicación..."
docker compose up -d

echo "✅ Despliegue completado correctamente."
echo "💡 Nota: Las configuraciones se persisten en ./frontend/configs y ./backend/storage"

docker network connect webapps-net moeve-frontend
echo "app conectada a la red webapps-net"
