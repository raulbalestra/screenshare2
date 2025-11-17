#!/bin/bash
# Script para corrigir deploy no VPS

echo "🔧 Corrigindo configuração do ScreenShare..."

# Parar containers
echo "⏹️  Parando containers..."
docker compose down 2>/dev/null || true

# Descobrir a rede do evo-pg
echo "🔍 Procurando rede do evo-pg..."
EVO_NETWORK=$(docker inspect evo-pg --format='{{range $net,$v := .NetworkSettings.Networks}}{{$net}}{{end}}' 2>/dev/null)

if [ -z "$EVO_NETWORK" ]; then
    echo "❌ Container evo-pg não encontrado!"
    echo "Criando rede padrão..."
    docker network create evo-network 2>/dev/null || true
    EVO_NETWORK="evo-network"
fi

echo "✅ Rede encontrada: $EVO_NETWORK"

# Atualizar docker-compose.yml
echo "📝 Atualizando docker-compose.yml..."
cat > docker-compose.yml <<EOF
version: "3.9"

services:
  screenshare:
    build:
      context: .
      dockerfile: Dockerfile
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
      - ${EVO_NETWORK}

networks:
  ${EVO_NETWORK}:
    external: true
EOF

# Rebuild
echo "🏗️  Reconstruindo container..."
docker compose build --no-cache

# Conectar evo-pg à rede se necessário
echo "🔗 Conectando evo-pg à rede..."
docker network connect $EVO_NETWORK evo-pg 2>/dev/null || echo "Já conectado"

# Start
echo "▶️  Iniciando container..."
docker compose up -d

# Aguardar um pouco
sleep 5

# Mostrar logs
echo ""
echo "📋 Logs:"
docker compose logs --tail=50

echo ""
echo "✅ Deploy concluído!"
echo ""
echo "🧪 Testar:"
echo "  curl http://localhost:8000/api/health"
