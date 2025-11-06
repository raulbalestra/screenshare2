#!/bin/bash

# Script para parar ScreenShare HLS
# Execute como: ./scripts/stop.sh

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log "Parando ScreenShare HLS..."

# Parar API
log "Parando API..."
if [ -f "logs/api.pid" ]; then
    API_PID=$(cat logs/api.pid)
    if kill -0 $API_PID 2>/dev/null; then
        kill $API_PID
        log "✅ API parada (PID: $API_PID)"
    else
        warn "API já estava parada"
    fi
    rm -f logs/api.pid
fi

# Parar MediaMTX
log "Parando MediaMTX..."
if [ -f "logs/mediamtx.pid" ]; then
    MEDIAMTX_PID=$(cat logs/mediamtx.pid)
    if kill -0 $MEDIAMTX_PID 2>/dev/null; then
        kill $MEDIAMTX_PID
        log "✅ MediaMTX parado (PID: $MEDIAMTX_PID)"
    else
        warn "MediaMTX já estava parado"
    fi
    rm -f logs/mediamtx.pid
fi

# Forçar parada de processos remanescentes
pkill -f "mediamtx" 2>/dev/null && log "Processos MediaMTX remanescentes finalizados" || true
pkill -f "uvicorn.*app:app" 2>/dev/null && log "Processos API remanescentes finalizados" || true

log "🛑 Todos os serviços foram parados"