#!/bin/bash

# 🚀 Script de Deploy Automatizado - ScreenShare
# Servidor: 31.97.156.167
# Domínio: screenshare.itfolkstech.com

set -e  # Parar em caso de erro

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   ScreenShare - Deploy Automatizado${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Variáveis
APP_DIR="/opt/screenshare"
BACKUP_DIR="/opt/backups/screenshare"
LOG_DIR="/var/log/screenshare"
VENV_DIR="$APP_DIR/venv"

# Função para log
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se é root
if [ "$EUID" -ne 0 ]; then 
    log_error "Por favor, execute como root (sudo)"
    exit 1
fi

# Passo 1: Criar backup
log_info "Criando backup da instalação atual..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

if [ -d "$APP_DIR" ]; then
    tar -czf $BACKUP_DIR/app_backup_$TIMESTAMP.tar.gz -C /opt screenshare
    log_info "Backup criado: $BACKUP_DIR/app_backup_$TIMESTAMP.tar.gz"
fi

# Passo 2: Criar estrutura de diretórios
log_info "Criando estrutura de diretórios..."
mkdir -p $APP_DIR
mkdir -p $LOG_DIR
mkdir -p $APP_DIR/uploads
mkdir -p $APP_DIR/templates
mkdir -p $APP_DIR/static

# Passo 3: Instalar dependências do sistema
log_info "Instalando dependências do sistema..."
apt update
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib \
    nginx certbot python3-certbot-nginx ffmpeg gunicorn htop curl

# Passo 4: Configurar ambiente virtual Python
log_info "Configurando ambiente virtual Python..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
    log_info "Ambiente virtual criado"
fi

source $VENV_DIR/bin/activate

# Passo 5: Instalar dependências Python
log_info "Instalando dependências Python..."
if [ -f "$APP_DIR/requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r $APP_DIR/requirements.txt
    log_info "Dependências instaladas"
else
    log_warn "Arquivo requirements.txt não encontrado. Pulando instalação de pacotes."
fi

# Passo 6: Configurar PostgreSQL (se ainda não configurado)
log_info "Verificando configuração do PostgreSQL..."
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw screenshare; then
    log_info "Banco de dados 'screenshare' já existe"
else
    log_info "Criando banco de dados..."
    sudo -u postgres psql <<EOF
CREATE DATABASE screenshare;
CREATE USER screenshare_user WITH PASSWORD 'ChangeThisPassword123!';
GRANT ALL PRIVILEGES ON DATABASE screenshare TO screenshare_user;
EOF
    log_info "Banco de dados criado"
fi

# Passo 7: Criar arquivo .env se não existir
if [ ! -f "$APP_DIR/.env" ]; then
    log_info "Criando arquivo .env..."
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
    cat > $APP_DIR/.env <<EOF
# Configurações do Banco de Dados PostgreSQL
DB_HOST=localhost
DB_NAME=screenshare
DB_USER=screenshare_user
DB_PASSWORD=ChangeThisPassword123!

# Configurações da Aplicação
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production

# Configuração de Domínio
BASE_URL=https://screenshare.itfolkstech.com
ALLOWED_ORIGINS=https://screenshare.itfolkstech.com

# Configurações de Segurança
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SECURE=True

# Configurações de Upload
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=$APP_DIR/uploads

# Configurações de Taxa de Limite
RATE_LIMIT_ENABLED=True
MAX_REQUESTS_PER_MINUTE=60
EOF
    chmod 600 $APP_DIR/.env
    log_warn "Arquivo .env criado. ALTERE AS SENHAS em $APP_DIR/.env"
else
    log_info "Arquivo .env já existe"
fi

# Passo 8: Criar serviço systemd
log_info "Configurando serviço systemd..."
cat > /etc/systemd/system/screenshare.service <<EOF
[Unit]
Description=ScreenShare Application
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/gunicorn --workers 4 --bind 127.0.0.1:5000 --timeout 120 --access-logfile $LOG_DIR/access.log --error-logfile $LOG_DIR/error.log app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable screenshare
log_info "Serviço systemd configurado"

# Passo 9: Configurar firewall
log_info "Configurando firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
log_info "Firewall configurado"

# Passo 10: Criar script de backup
log_info "Criando script de backup..."
cat > $APP_DIR/backup.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/screenshare"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup do banco de dados
PGPASSWORD="ChangeThisPassword123!" pg_dump -U screenshare_user -h localhost screenshare > $BACKUP_DIR/db_$DATE.sql

# Backup dos uploads
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /opt/screenshare/uploads

# Manter apenas os 7 backups mais recentes
find $BACKUP_DIR -name "db_*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "uploads_*.tar.gz" -mtime +7 -delete

echo "Backup concluído: $DATE"
EOF

chmod +x $APP_DIR/backup.sh

# Adicionar ao crontab se ainda não existir
if ! crontab -l | grep -q "$APP_DIR/backup.sh"; then
    (crontab -l 2>/dev/null; echo "0 2 * * * $APP_DIR/backup.sh >> /var/log/screenshare_backup.log 2>&1") | crontab -
    log_info "Backup automático configurado (diário às 2h)"
fi

# Passo 11: Ajustar permissões
log_info "Ajustando permissões..."
chmod 755 $APP_DIR
chmod 755 $APP_DIR/uploads
chmod 600 $APP_DIR/.env
chown -R root:root $APP_DIR

# Passo 12: Verificar se app.py existe
if [ ! -f "$APP_DIR/app.py" ]; then
    log_error "Arquivo app.py não encontrado em $APP_DIR"
    log_error "Por favor, transfira os arquivos da aplicação para $APP_DIR"
    exit 1
fi

# Passo 13: Reiniciar serviços
log_info "Reiniciando serviços..."
systemctl restart screenshare
systemctl restart nginx

# Passo 14: Verificar status
sleep 3
log_info "Verificando status dos serviços..."

if systemctl is-active --quiet screenshare; then
    log_info "✓ Serviço screenshare está RODANDO"
else
    log_error "✗ Serviço screenshare NÃO está rodando"
    log_error "Verifique os logs: journalctl -u screenshare -n 50"
fi

if systemctl is-active --quiet nginx; then
    log_info "✓ Nginx está RODANDO"
else
    log_error "✗ Nginx NÃO está rodando"
fi

if systemctl is-active --quiet postgresql; then
    log_info "✓ PostgreSQL está RODANDO"
else
    log_error "✗ PostgreSQL NÃO está rodando"
fi

# Resumo final
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   Deploy Concluído!${NC}"
echo -e "${GREEN}========================================${NC}\n"
echo -e "URL: ${YELLOW}https://screenshare.itfolkstech.com${NC}"
echo -e "Logs: ${YELLOW}$LOG_DIR${NC}"
echo -e "App Dir: ${YELLOW}$APP_DIR${NC}"
echo -e "Backups: ${YELLOW}$BACKUP_DIR${NC}"
echo -e "\n${YELLOW}IMPORTANTE:${NC}"
echo -e "1. Altere as senhas em ${YELLOW}$APP_DIR/.env${NC}"
echo -e "2. Altere a senha do banco de dados PostgreSQL"
echo -e "3. Altere a senha do usuário admin na aplicação"
echo -e "4. Verifique os logs: ${YELLOW}tail -f $LOG_DIR/error.log${NC}"
echo -e "\n${GREEN}========================================${NC}\n"
