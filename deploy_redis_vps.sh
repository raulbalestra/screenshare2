#!/bin/bash

# =============================================================================
# SCRIPT DE DEPLOY REDIS - VPS Produção
# Servidor: 31.97.156.167 (srv875853)
# Domínio: screenshare.itfolkstech.com
# Data: 11/12/2025
# =============================================================================

set -e  # Parar em caso de erro

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

print_header() {
    echo ""
    echo "============================================================="
    echo "  $1"
    echo "============================================================="
    echo ""
}

# Configurações
VPS_HOST="31.97.156.167"
VPS_USER="root"
PROJECT_DIR="/root/screenshare2"
TMUX_SESSION="novo_screenshare"

print_header "DEPLOY REDIS - SCREENSHARE VPS"

log_info "Servidor: $VPS_HOST"
log_info "Diretório: $PROJECT_DIR"
log_info "Sessão tmux: $TMUX_SESSION"
echo ""

# =============================================================================
# PASSO 1: Instalar Redis no Servidor
# =============================================================================

print_header "PASSO 1: INSTALANDO REDIS NO SERVIDOR"

log_info "Conectando ao servidor..."

ssh $VPS_USER@$VPS_HOST << 'ENDSSH'
set -e

echo "[INFO] Atualizando pacotes..."
apt update -qq

echo "[INFO] Verificando se Redis já está instalado..."
if command -v redis-server &> /dev/null; then
    echo "[✓] Redis já está instalado"
    redis-server --version
else
    echo "[INFO] Instalando Redis..."
    apt install -y redis-server
    echo "[✓] Redis instalado"
fi

echo "[INFO] Configurando Redis para iniciar no boot..."
systemctl enable redis-server

echo "[INFO] Iniciando Redis..."
systemctl start redis-server || systemctl restart redis-server

echo "[INFO] Verificando status..."
systemctl is-active redis-server && echo "[✓] Redis está rodando" || echo "[✗] Redis não está rodando"

echo "[INFO] Testando conexão..."
if redis-cli ping | grep -q "PONG"; then
    echo "[✓] Redis respondeu: PONG"
else
    echo "[✗] Redis não está respondendo"
    exit 1
fi

echo ""
echo "============================================================="
echo "  Redis instalado e funcionando!"
echo "============================================================="
echo ""

ENDSSH

log_success "Redis instalado e configurado no servidor"

# =============================================================================
# PASSO 2: Atualizar Código no Servidor
# =============================================================================

print_header "PASSO 2: ATUALIZANDO CÓDIGO NO SERVIDOR"

log_info "Fazendo pull do repositório..."

ssh $VPS_USER@$VPS_HOST << ENDSSH
set -e

cd $PROJECT_DIR

echo "[INFO] Fazendo backup do .env atual..."
if [ -f .env ]; then
    cp .env .env.backup.\$(date +%Y%m%d_%H%M%S)
    echo "[✓] Backup salvo"
fi

echo "[INFO] Fazendo git pull..."
git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || git pull

echo "[✓] Código atualizado"

ENDSSH

log_success "Código atualizado no servidor"

# =============================================================================
# PASSO 3: Instalar Dependências Python
# =============================================================================

print_header "PASSO 3: INSTALANDO DEPENDÊNCIAS PYTHON"

ssh $VPS_USER@$VPS_HOST << ENDSSH
set -e

cd $PROJECT_DIR

echo "[INFO] Instalando redis Python..."
pip install redis==5.0.1

echo "[INFO] Verificando instalação..."
python3 -c "import redis; print('[✓] Redis Python instalado:', redis.__version__)"

ENDSSH

log_success "Dependências Python instaladas"

# =============================================================================
# PASSO 4: Configurar .env de Produção
# =============================================================================

print_header "PASSO 4: CONFIGURANDO .ENV DE PRODUÇÃO"

log_info "Verificando configurações Redis no .env..."

ssh $VPS_USER@$VPS_HOST << 'ENDSSH'
set -e

cd $PROJECT_DIR

# Verificar se já tem configurações Redis no .env
if grep -q "REDIS_ENABLED" .env 2>/dev/null; then
    echo "[✓] Configurações Redis já existem no .env"
else
    echo "[INFO] Adicionando configurações Redis ao .env..."
    cat >> .env << 'EOF'

# Configurações do Redis - PRODUÇÃO
REDIS_ENABLED=True
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_FRAME_TTL=30
REDIS_QUEUE_MAX_SIZE=100
EOF
    echo "[✓] Configurações Redis adicionadas"
fi

echo ""
echo "Configurações Redis no .env:"
grep "REDIS_" .env

ENDSSH

log_success "Configuração .env atualizada"

# =============================================================================
# PASSO 5: Testar Redis
# =============================================================================

print_header "PASSO 5: TESTANDO REDIS"

log_info "Executando testes..."

ssh $VPS_USER@$VPS_HOST << ENDSSH
set -e

cd $PROJECT_DIR

echo "[INFO] Testando conexão Redis..."
python3 << 'PYEOF'
try:
    import redis
    r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=5)
    if r.ping():
        print("[✓] Conexão Redis OK - PONG recebido")
    else:
        print("[✗] Redis não respondeu")
        exit(1)
except Exception as e:
    print(f"[✗] Erro ao conectar: {e}")
    exit(1)
PYEOF

echo ""
echo "[INFO] Testando RedisFrameManager..."
python3 << 'PYEOF'
try:
    from redis_manager import init_redis_manager
    rm = init_redis_manager()
    if rm and rm.is_available():
        print("[✓] RedisFrameManager inicializado e conectado")
        stats = rm.get_stats()
        print(f"[✓] Stats: {stats}")
    else:
        print("[✗] RedisFrameManager não está disponível")
        exit(1)
except Exception as e:
    print(f"[✗] Erro: {e}")
    exit(1)
PYEOF

ENDSSH

log_success "Testes Redis passaram"

# =============================================================================
# PASSO 6: Reiniciar Aplicação
# =============================================================================

print_header "PASSO 6: REINICIANDO APLICAÇÃO"

log_warning "A aplicação será reiniciada no tmux"
log_info "Você precisará verificar os logs manualmente"

ssh $VPS_USER@$VPS_HOST << ENDSSH
set -e

cd $PROJECT_DIR

echo "[INFO] Parando aplicação no tmux..."
tmux send-keys -t $TMUX_SESSION C-c 2>/dev/null || echo "[INFO] Aplicação já estava parada"

sleep 2

echo "[INFO] Iniciando aplicação..."
tmux send-keys -t $TMUX_SESSION "cd $PROJECT_DIR && python app.py" Enter

sleep 3

echo "[✓] Comando de inicialização enviado"
echo ""
echo "Para ver os logs:"
echo "  ssh $VPS_USER@$VPS_HOST"
echo "  tmux attach -t $TMUX_SESSION"

ENDSSH

log_success "Aplicação reiniciada"

# =============================================================================
# RESUMO FINAL
# =============================================================================

print_header "DEPLOY CONCLUÍDO!"

echo -e "${GREEN}✅ Redis instalado e rodando${NC}"
echo -e "${GREEN}✅ Código atualizado${NC}"
echo -e "${GREEN}✅ Dependências instaladas${NC}"
echo -e "${GREEN}✅ Configuração aplicada${NC}"
echo -e "${GREEN}✅ Testes passaram${NC}"
echo -e "${GREEN}✅ Aplicação reiniciada${NC}"
echo ""
echo "🔗 Acesse: https://screenshare.itfolkstech.com"
echo ""
echo "📋 Próximos passos:"
echo "   1. ssh root@$VPS_HOST"
echo "   2. tmux attach -t $TMUX_SESSION"
echo "   3. Verifique logs: procure por '[INIT] ✓ Redis conectado'"
echo "   4. Teste transmissão: https://screenshare.itfolkstech.com"
echo ""
echo "📊 Comandos úteis:"
echo "   - Ver status Redis:    systemctl status redis-server"
echo "   - Ver logs app:        tail -f $PROJECT_DIR/app.log"
echo "   - Conectar Redis CLI:  redis-cli"
echo "   - Monitor Redis:       redis-cli monitor"
echo "   - Stats Redis:         curl https://screenshare.itfolkstech.com/admin/redis/stats"
echo ""

log_success "Deploy completo!"
