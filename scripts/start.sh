#!/bin/bash

# Script de inicialização ScreenShare HLS
# Execute como: ./scripts/start.sh

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Banner
echo -e "${BLUE}"
cat << 'EOF'
╔═══════════════════════════════════════╗
║         ScreenShare HLS Server        ║
║     Sistema de Transmissão por        ║
║              Estados                  ║
╚═══════════════════════════════════════╝
EOF
echo -e "${NC}"

# Verificar se está no diretório correto
if [ ! -f "app.py" ] || [ ! -f "config/mediamtx.yml" ]; then
    error "Execute este script no diretório raiz do projeto"
    exit 1
fi

# Função para verificar dependências
check_dependencies() {
    log "Verificando dependências..."
    
    # Python 3.11+
    if ! command -v python3 &> /dev/null; then
        error "Python 3 não encontrado"
        exit 1
    fi
    
    # MediaMTX
    if ! command -v mediamtx &> /dev/null; then
        warn "MediaMTX não encontrado no PATH"
        info "Baixando MediaMTX..."
        
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            MEDIAMTX_OS="linux"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            MEDIAMTX_OS="darwin"
        else
            error "Sistema operacional não suportado"
            exit 1
        fi
        
        ARCH=$(uname -m)
        if [[ "$ARCH" == "x86_64" ]]; then
            MEDIAMTX_ARCH="amd64"
        elif [[ "$ARCH" == "arm64" ]] || [[ "$ARCH" == "aarch64" ]]; then
            MEDIAMTX_ARCH="arm64v8"
        else
            error "Arquitetura não suportada: $ARCH"
            exit 1
        fi
        
        MEDIAMTX_VERSION="v1.5.1"
        MEDIAMTX_URL="https://github.com/bluenviron/mediamtx/releases/download/${MEDIAMTX_VERSION}/mediamtx_${MEDIAMTX_VERSION}_${MEDIAMTX_OS}_${MEDIAMTX_ARCH}.tar.gz"
        
        wget -q "$MEDIAMTX_URL" -O mediamtx.tar.gz
        tar -xzf mediamtx.tar.gz
        chmod +x mediamtx
        rm mediamtx.tar.gz
        
        log "MediaMTX baixado com sucesso"
    fi
}

# Função para configurar ambiente Python
setup_python_env() {
    log "Configurando ambiente Python..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log "Ambiente Python configurado"
}

# Função para iniciar MediaMTX
start_mediamtx() {
    log "Iniciando MediaMTX..."
    
    # Verificar se já está rodando
    if pgrep -f "mediamtx" > /dev/null; then
        warn "MediaMTX já está rodando"
        return
    fi
    
    # Usar MediaMTX local se disponível, senão usar do PATH
    if [ -f "./mediamtx" ]; then
        nohup ./mediamtx config/mediamtx.yml > logs/mediamtx.log 2>&1 &
    else
        nohup mediamtx config/mediamtx.yml > logs/mediamtx.log 2>&1 &
    fi
    
    MEDIAMTX_PID=$!
    echo $MEDIAMTX_PID > logs/mediamtx.pid
    
    sleep 2
    if kill -0 $MEDIAMTX_PID 2>/dev/null; then
        log "✅ MediaMTX iniciado (PID: $MEDIAMTX_PID)"
    else
        error "❌ Falha ao iniciar MediaMTX"
        cat logs/mediamtx.log
        exit 1
    fi
}

# Função para iniciar API
start_api() {
    log "Iniciando ScreenShare API..."
    
    # Verificar se já está rodando
    if pgrep -f "uvicorn.*app:app" > /dev/null; then
        warn "API já está rodando"
        return
    fi
    
    source venv/bin/activate
    
    # Modo desenvolvimento
    if [ "${1:-}" = "dev" ]; then
        nohup uvicorn app:app --host 0.0.0.0 --port 8000 --reload > logs/api.log 2>&1 &
    else
        # Modo produção
        nohup uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4 > logs/api.log 2>&1 &
    fi
    
    API_PID=$!
    echo $API_PID > logs/api.pid
    
    sleep 2
    if kill -0 $API_PID 2>/dev/null; then
        log "✅ API iniciada (PID: $API_PID)"
    else
        error "❌ Falha ao iniciar API"
        cat logs/api.log
        exit 1
    fi
}

# Função para mostrar status
show_status() {
    echo ""
    info "📊 Status dos Serviços:"
    
    # MediaMTX
    if pgrep -f "mediamtx" > /dev/null; then
        echo -e "   MediaMTX: ${GREEN}✅ Rodando${NC}"
    else
        echo -e "   MediaMTX: ${RED}❌ Parado${NC}"
    fi
    
    # API
    if pgrep -f "uvicorn.*app:app" > /dev/null; then
        echo -e "   API: ${GREEN}✅ Rodando${NC}"
    else
        echo -e "   API: ${RED}❌ Parado${NC}"
    fi
    
    echo ""
    info "🌐 Endpoints:"
    echo "   📱 Interface Web: http://localhost:8000"
    echo "   📡 API: http://localhost:8000/api"
    echo "   🎥 HLS: http://localhost:8888/hls/{estado}/{sessao}/index.m3u8"
    echo "   📺 WHIP: http://localhost:8889/whip/{estado}/{sessao}"
    
    echo ""
    info "📋 Estados Configurados:"
    echo "   SP, RJ, MG, PR, SC, RS, BA, PE, CE, GO"
    
    echo ""
    info "🔧 Comandos Úteis:"
    echo "   📜 Logs MediaMTX: tail -f logs/mediamtx.log"
    echo "   📜 Logs API: tail -f logs/api.log"
    echo "   🛑 Parar: ./scripts/stop.sh"
    echo ""
}

# Função para parar serviços
stop_services() {
    log "Parando serviços..."
    
    # Parar API
    if [ -f "logs/api.pid" ]; then
        API_PID=$(cat logs/api.pid)
        if kill -0 $API_PID 2>/dev/null; then
            kill $API_PID
            log "API parada"
        fi
        rm -f logs/api.pid
    fi
    
    # Parar MediaMTX
    if [ -f "logs/mediamtx.pid" ]; then
        MEDIAMTX_PID=$(cat logs/mediamtx.pid)
        if kill -0 $MEDIAMTX_PID 2>/dev/null; then
            kill $MEDIAMTX_PID
            log "MediaMTX parado"
        fi
        rm -f logs/mediamtx.pid
    fi
    
    # Forçar parada se necessário
    pkill -f "mediamtx" 2>/dev/null || true
    pkill -f "uvicorn.*app:app" 2>/dev/null || true
}

# Criar diretório de logs
mkdir -p logs

# Processar argumentos
case "${1:-start}" in
    "start"|"")
        check_dependencies
        setup_python_env
        start_mediamtx
        start_api
        show_status
        ;;
    "dev")
        check_dependencies
        setup_python_env
        start_mediamtx
        start_api "dev"
        show_status
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        sleep 2
        start_mediamtx
        start_api
        show_status
        ;;
    "status")
        show_status
        ;;
    "logs")
        if [ "${2:-}" = "api" ]; then
            tail -f logs/api.log
        elif [ "${2:-}" = "mediamtx" ]; then
            tail -f logs/mediamtx.log
        else
            echo "Especifique: logs api ou logs mediamtx"
        fi
        ;;
    *)
        echo "Uso: $0 {start|dev|stop|restart|status|logs}"
        echo ""
        echo "Comandos:"
        echo "  start     - Iniciar em modo produção"
        echo "  dev       - Iniciar em modo desenvolvimento"
        echo "  stop      - Parar todos os serviços"
        echo "  restart   - Reiniciar serviços"
        echo "  status    - Mostrar status"
        echo "  logs      - Ver logs (api|mediamtx)"
        exit 1
        ;;
esac