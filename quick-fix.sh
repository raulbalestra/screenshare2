#!/bin/bash
# Quick fix - cole este script direto no terminal do VPS

echo "🔧 Corrigindo configuração..."

# Parar tudo
docker compose down 2>/dev/null || true

# Descobrir rede do evo-pg
EVO_NETWORK=$(docker inspect evo-pg --format='{{range $net,$v := .NetworkSettings.Networks}}{{$net}}{{end}}' 2>/dev/null | head -n1)

if [ -z "$EVO_NETWORK" ]; then
    echo "❌ evo-pg não encontrado! Criando rede..."
    docker network create evo-network
    EVO_NETWORK="evo-network"
fi

echo "✅ Usando rede: $EVO_NETWORK"

# Conectar evo-pg se necessário
docker network connect $EVO_NETWORK evo-pg 2>/dev/null || echo "✅ evo-pg já na rede"

# Atualizar docker-compose
cat > docker-compose.yml <<'COMPOSE_EOF'
services:
  screenshare:
    build: .
    container_name: screenshare_all_in_one
    restart: unless-stopped
    environment:
      DB_HOST: evo-pg
      DB_PORT: 5432
      DB_NAME: screenshare_db
      DB_USER: screenshare_user
      DB_PASSWORD: ScreenShare2025!
      APP_HOST: 0.0.0.0
      APP_PORT: 8000
    ports:
      - "8000:8000"
      - "8888:8888"
      - "8889:8889"
      - "8890:8890"
      - "9997:9997"
    networks:
      - evo-network

networks:
  evo-network:
    external: true
COMPOSE_EOF

echo "🏗️  Rebuild..."
docker compose build

echo "▶️  Starting..."
docker compose up -d

sleep 5
echo ""
echo "📋 Status:"
docker compose ps
echo ""
docker compose logs --tail=30
