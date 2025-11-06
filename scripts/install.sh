#!/bin/bash

# Script de instalação ScreenShare HLS para Ubuntu VPS
# Execute como: curl -sSL https://raw.githubusercontent.com/seu-repo/screenshare2/main/scripts/install.sh | bash

set -e

echo "🚀 Iniciando instalação ScreenShare HLS..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Verificar se é Ubuntu
if ! lsb_release -d | grep -q "Ubuntu"; then
    error "Este script é apenas para Ubuntu"
    exit 1
fi

# Atualizar sistema
log "Atualizando sistema..."
sudo apt update
sudo apt upgrade -y

# Instalar dependências básicas
log "Instalando dependências básicas..."
sudo apt install -y \
    curl \
    wget \
    git \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    build-essential \
    nginx \
    supervisor

# Instalar Python 3.11
log "Instalando Python 3.11..."
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-pip python3.11-venv python3.11-dev

# Criar usuário screenshare
log "Criando usuário screenshare..."
if ! id "screenshare" &>/dev/null; then
    sudo useradd -m -s /bin/bash screenshare
    sudo usermod -aG www-data screenshare
fi

# Criar diretórios
log "Criando estrutura de diretórios..."
sudo mkdir -p /opt/screenshare
sudo mkdir -p /var/log/screenshare
sudo mkdir -p /etc/screenshare
sudo chown -R screenshare:screenshare /opt/screenshare
sudo chown -R screenshare:screenshare /var/log/screenshare

# Baixar MediaMTX
log "Instalando MediaMTX..."
MEDIAMTX_VERSION="v1.5.1"
wget https://github.com/bluenviron/mediamtx/releases/download/${MEDIAMTX_VERSION}/mediamtx_${MEDIAMTX_VERSION}_linux_amd64.tar.gz
tar -xzf mediamtx_${MEDIAMTX_VERSION}_linux_amd64.tar.gz
sudo mv mediamtx /usr/local/bin/
sudo chmod +x /usr/local/bin/mediamtx
rm mediamtx_${MEDIAMTX_VERSION}_linux_amd64.tar.gz

# Clonar repositório (substitua pela URL real)
log "Clonando repositório da aplicação..."
cd /opt/screenshare
if [ -d "screenshare2" ]; then
    sudo rm -rf screenshare2
fi

# Se o repositório existir no GitHub, use:
# sudo -u screenshare git clone https://github.com/seu-usuario/screenshare2.git .

# Caso contrário, baixe os arquivos manualmente ou copie-os

# Criar virtual environment
log "Criando ambiente virtual Python..."
sudo -u screenshare python3.11 -m venv /opt/screenshare/venv
sudo -u screenshare /opt/screenshare/venv/bin/pip install --upgrade pip

# Instalar dependências Python
log "Instalando dependências Python..."
sudo -u screenshare /opt/screenshare/venv/bin/pip install -r requirements.txt

# Configurar MediaMTX
log "Configurando MediaMTX..."
sudo cp config/mediamtx.yml /etc/screenshare/
sudo chown screenshare:screenshare /etc/screenshare/mediamtx.yml

# Criar serviços systemd
log "Criando serviços systemd..."

# Serviço MediaMTX
cat << 'EOF' | sudo tee /etc/systemd/system/mediamtx.service
[Unit]
Description=MediaMTX Server
After=network.target

[Service]
Type=simple
User=screenshare
Group=screenshare
WorkingDirectory=/opt/screenshare
ExecStart=/usr/local/bin/mediamtx /etc/screenshare/mediamtx.yml
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Serviço ScreenShare API
cat << 'EOF' | sudo tee /etc/systemd/system/screenshare-api.service
[Unit]
Description=ScreenShare HLS API
After=network.target

[Service]
Type=simple
User=screenshare
Group=screenshare
WorkingDirectory=/opt/screenshare
Environment=PATH=/opt/screenshare/venv/bin
ExecStart=/opt/screenshare/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Configurar Nginx
log "Configurando Nginx..."
cat << 'EOF' | sudo tee /etc/nginx/sites-available/screenshare
server {
    listen 80;
    server_name _;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=hls:10m rate=30r/s;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    # API FastAPI
    location / {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # HLS streams
    location /hls/ {
        limit_req zone=hls burst=50 nodelay;
        proxy_pass http://127.0.0.1:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # CORS para HLS
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods 'GET, POST, OPTIONS';
        add_header Access-Control-Allow-Headers 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range';
        add_header Access-Control-Expose-Headers 'Content-Length,Content-Range';
        
        # Cache para segments
        location ~* \.(m3u8)$ {
            expires 1s;
            add_header Cache-Control "no-cache, no-store, must-revalidate";
        }
        
        location ~* \.(ts|mp4)$ {
            expires 1m;
            add_header Cache-Control "public, immutable";
        }
    }

    # WHIP endpoint
    location /whip/ {
        proxy_pass http://127.0.0.1:8889;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebRTC specific
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Static files
    location /static/ {
        alias /opt/screenshare/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Logs
    access_log /var/log/nginx/screenshare_access.log;
    error_log /var/log/nginx/screenshare_error.log;
}
EOF

# Habilitar site
sudo ln -sf /etc/nginx/sites-available/screenshare /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Configurar firewall
log "Configurando firewall..."
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8888/tcp  # HLS
sudo ufw allow 8889/tcp  # WHIP
sudo ufw --force enable

# Configurar variáveis de ambiente
log "Configurando variáveis de ambiente..."
cat << 'EOF' | sudo tee /etc/screenshare/.env
# Aplicação
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False

# JWT
JWT_SECRET_KEY=sua_chave_jwt_super_secreta_mude_em_producao_$(openssl rand -hex 32)

# MediaMTX
MEDIAMTX_HOST=localhost
MEDIAMTX_WHIP_PORT=8889
MEDIAMTX_HLS_PORT=8888

# Estados permitidos
ALLOWED_STATES=SP,RJ,MG,PR,SC,RS,BA,PE,CE,GO

# Banco de dados
DATABASE_PATH=/opt/screenshare/sessions.db
EOF

sudo chown screenshare:screenshare /etc/screenshare/.env
sudo chmod 600 /etc/screenshare/.env

# Criar link simbólico para .env
sudo -u screenshare ln -sf /etc/screenshare/.env /opt/screenshare/.env

# Recarregar systemd e iniciar serviços
log "Iniciando serviços..."
sudo systemctl daemon-reload
sudo systemctl enable mediamtx
sudo systemctl enable screenshare-api
sudo systemctl enable nginx

sudo systemctl start mediamtx
sudo systemctl start screenshare-api
sudo systemctl restart nginx

# Verificar status dos serviços
log "Verificando status dos serviços..."
sleep 5

if sudo systemctl is-active --quiet mediamtx; then
    log "✅ MediaMTX está rodando"
else
    error "❌ MediaMTX falhou ao iniciar"
fi

if sudo systemctl is-active --quiet screenshare-api; then
    log "✅ ScreenShare API está rodando"
else
    error "❌ ScreenShare API falhou ao iniciar"
fi

if sudo systemctl is-active --quiet nginx; then
    log "✅ Nginx está rodando"
else
    error "❌ Nginx falhou ao iniciar"
fi

# Mostrar informações finais
log "🎉 Instalação concluída!"
echo ""
echo "📋 Informações do sistema:"
echo "   - API: http://$(curl -s ifconfig.me):80"
echo "   - HLS Endpoint: http://$(curl -s ifconfig.me):80/hls/"
echo "   - WHIP Endpoint: http://$(curl -s ifconfig.me):80/whip/"
echo ""
echo "🔧 Comandos úteis:"
echo "   - Status: sudo systemctl status mediamtx screenshare-api nginx"
echo "   - Logs: sudo journalctl -u mediamtx -f"
echo "   - Logs API: sudo journalctl -u screenshare-api -f"
echo "   - Logs Nginx: sudo tail -f /var/log/nginx/screenshare_error.log"
echo ""
echo "⚠️  IMPORTANTE:"
echo "   - Configure SSL/HTTPS para produção"
echo "   - Altere a JWT_SECRET_KEY em /etc/screenshare/.env"
echo "   - Configure domínio próprio no Nginx"
echo "   - Configure backup do banco de dados"

log "Instalação finalizada com sucesso!"