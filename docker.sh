#!/bin/bash
# Script unificado para rodar ScreenShare em um único container

set -e

echo "╔════════════════════════════════════════════╗"
echo "║      ScreenShare Docker All-In-One         ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Verificar se Docker está rodando
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker não está rodando!"
    exit 1
fi

MODE=${1:-start}

if [ "$MODE" = "start" ]; then
    echo "🚀 Iniciando ScreenShare..."
    docker compose up -d
    echo "✅ Container iniciado!"
    
elif [ "$MODE" = "stop" ]; then
    echo "⏹️  Parando ScreenShare..."
    docker compose down
    echo "✅ Container parado!"
    
elif [ "$MODE" = "build" ]; then
    echo "🔨 Fazendo build da imagem..."
    docker compose build --no-cache
    echo "✅ Build concluído!"
    
elif [ "$MODE" = "logs" ]; then
    echo "📋 Mostrando logs..."
    docker compose logs -f
    
elif [ "$MODE" = "shell" ]; then
    echo "🔧 Abrindo shell do container..."
    docker compose exec screenshare bash
    
elif [ "$MODE" = "restart" ]; then
    echo "🔄 Reiniciando..."
    docker compose restart
    echo "✅ Container reiniciado!"
    
else
    echo "Uso: $0 {start|stop|build|logs|shell|restart}"
    echo ""
    echo "Comandos:"
    echo "  start               - Iniciar o container"
    echo "  stop                - Parar o container"
    echo "  build               - Fazer build da imagem"
    echo "  logs                - Ver logs em tempo real"
    echo "  shell               - Abrir bash no container"
    echo "  restart             - Reiniciar o container"
    exit 1
fi

echo ""
echo "🌐 Endpoints:"
echo "   API:          http://localhost:8000"
echo "   HLS:          http://localhost:8888"
echo "   WHIP:         http://localhost:8889"
echo "   MediaMTX API: http://localhost:9997"
echo "   PostgreSQL:   localhost:5432"
echo ""
