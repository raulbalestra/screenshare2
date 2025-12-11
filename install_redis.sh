#!/bin/bash

# =============================================================================
# SCRIPT DE INSTALAÇÃO REDIS - ScreenShare System
# Autor: ScreenShare Dev Team
# Data: 11/12/2025
#
# Este script instala e configura Redis para o sistema ScreenShare
# Funciona em: Ubuntu/Debian, WSL, e outros sistemas Linux
# =============================================================================

set -e  # Sair em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de log
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_header() {
    echo ""
    echo "============================================================="
    echo "  $1"
    echo "============================================================="
    echo ""
}

# Verificar se está rodando como root/sudo
check_sudo() {
    if [ "$EUID" -eq 0 ]; then
        SUDO=""
    else
        SUDO="sudo"
    fi
}

# Detectar sistema operacional
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    
    log_info "Sistema detectado: $OS $VER"
}

# Instalar Redis
install_redis() {
    print_header "INSTALAÇÃO DO REDIS"
    
    log_info "Verificando se Redis já está instalado..."
    
    if command -v redis-server &> /dev/null; then
        log_warning "Redis já está instalado"
        redis-server --version
        return 0
    fi
    
    log_info "Instalando Redis..."
    
    # Ubuntu/Debian
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        $SUDO apt update
        $SUDO apt install -y redis-server
    
    # CentOS/RHEL
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        $SUDO yum install -y redis
    
    # Fedora
    elif [[ "$OS" == *"Fedora"* ]]; then
        $SUDO dnf install -y redis
    
    else
        log_error "Sistema operacional não suportado: $OS"
        log_info "Por favor, instale Redis manualmente"
        exit 1
    fi
    
    log_success "Redis instalado com sucesso"
}

# Configurar Redis
configure_redis() {
    print_header "CONFIGURAÇÃO DO REDIS"
    
    log_info "Configurando Redis para o ScreenShare..."
    
    # Backup da configuração original
    if [ -f /etc/redis/redis.conf ]; then
        if [ ! -f /etc/redis/redis.conf.backup ]; then
            log_info "Fazendo backup da configuração original..."
            $SUDO cp /etc/redis/redis.conf /etc/redis/redis.conf.backup
            log_success "Backup salvo em /etc/redis/redis.conf.backup"
        fi
    fi
    
    log_info "Aplicando configurações recomendadas..."
    
    # Configurações básicas (opcional - descomentar se necessário)
    # $SUDO sed -i 's/^bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf
    # $SUDO sed -i 's/^# maxmemory <bytes>/maxmemory 256mb/' /etc/redis/redis.conf
    # $SUDO sed -i 's/^# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
    
    log_success "Configuração aplicada"
}

# Iniciar Redis
start_redis() {
    print_header "INICIANDO REDIS"
    
    log_info "Habilitando Redis no boot..."
    $SUDO systemctl enable redis-server 2>/dev/null || $SUDO systemctl enable redis 2>/dev/null || true
    
    log_info "Iniciando serviço Redis..."
    $SUDO systemctl start redis-server 2>/dev/null || $SUDO systemctl start redis 2>/dev/null || true
    
    sleep 2
    
    # Verificar se está rodando
    if $SUDO systemctl is-active --quiet redis-server 2>/dev/null || $SUDO systemctl is-active --quiet redis 2>/dev/null; then
        log_success "Redis está rodando"
    else
        log_error "Falha ao iniciar Redis"
        exit 1
    fi
}

# Testar conexão Redis
test_redis() {
    print_header "TESTANDO REDIS"
    
    log_info "Testando conexão com Redis..."
    
    if redis-cli ping | grep -q "PONG"; then
        log_success "Redis respondeu com PONG - Conexão OK!"
    else
        log_error "Redis não está respondendo"
        exit 1
    fi
    
    log_info "Testando operações básicas..."
    
    # Teste SET/GET
    redis-cli SET test_key "ScreenShare" > /dev/null
    VALUE=$(redis-cli GET test_key)
    
    if [ "$VALUE" = "ScreenShare" ]; then
        log_success "Operações SET/GET funcionando"
        redis-cli DEL test_key > /dev/null
    else
        log_error "Erro nas operações básicas"
        exit 1
    fi
    
    # Mostrar informações
    log_info "Informações do Redis:"
    echo "  Versão: $(redis-server --version | awk '{print $3}')"
    echo "  Porta: 6379"
    echo "  Host: localhost"
}

# Instalar dependência Python
install_python_redis() {
    print_header "INSTALANDO DEPENDÊNCIA PYTHON"
    
    log_info "Verificando se pip está instalado..."
    
    if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
        log_warning "pip não encontrado, instalando..."
        $SUDO apt install -y python3-pip 2>/dev/null || $SUDO yum install -y python3-pip 2>/dev/null || true
    fi
    
    PIP_CMD=$(command -v pip3 || command -v pip)
    
    log_info "Instalando biblioteca redis para Python..."
    $PIP_CMD install redis==5.0.1
    
    log_success "Biblioteca Python instalada"
}

# Exibir informações finais
show_summary() {
    print_header "INSTALAÇÃO CONCLUÍDA"
    
    echo -e "${GREEN}✅ Redis instalado e configurado com sucesso!${NC}"
    echo ""
    echo "📋 Informações:"
    echo "   Host: localhost"
    echo "   Port: 6379"
    echo "   Status: $(systemctl is-active redis-server 2>/dev/null || systemctl is-active redis 2>/dev/null || echo 'active')"
    echo ""
    echo "🔧 Comandos úteis:"
    echo "   Verificar status: sudo systemctl status redis-server"
    echo "   Parar Redis:      sudo systemctl stop redis-server"
    echo "   Iniciar Redis:    sudo systemctl start redis-server"
    echo "   Reiniciar Redis:  sudo systemctl restart redis-server"
    echo "   Conectar CLI:     redis-cli"
    echo ""
    echo "🧪 Próximos passos:"
    echo "   1. Execute o teste: python test_redis.py"
    echo "   2. Inicie a aplicação: python app.py"
    echo "   3. Acesse: http://localhost:5000"
    echo ""
    echo "📖 Documentação completa: REDIS_IMPLEMENTATION_GUIDE.md"
    echo ""
}

# =============================================================================
# SCRIPT PRINCIPAL
# =============================================================================

main() {
    print_header "INSTALAÇÃO REDIS - ScreenShare System"
    
    log_info "Iniciando instalação..."
    
    # Verificar sudo
    check_sudo
    
    # Detectar SO
    detect_os
    
    # Instalar Redis
    install_redis
    
    # Configurar Redis
    configure_redis
    
    # Iniciar Redis
    start_redis
    
    # Testar Redis
    test_redis
    
    # Instalar dependência Python
    install_python_redis
    
    # Mostrar resumo
    show_summary
    
    log_success "Instalação completa!"
}

# Executar
main

exit 0
