#!/bin/bash
# ============================================================
# Script de deploy: screenshare2
# Domínio: teste.paineldefilas-raizen.com.br
# ============================================================
set -e

APP_DIR="/home/kaminsk/screenshare2"
DOMAIN="teste.paineldefilas-raizen.com.br"
SERVICE_NAME="screenshare2"
USER="kaminsk"

echo "===> [1/6] Atualizando o repositório..."
cd "$APP_DIR"
git pull origin main

echo "===> [2/6] Criando virtualenv e instalando dependências..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q
echo "      Dependências instaladas com sucesso."

echo "===> [3/6] Criando arquivo .env (pule se já existir com dados corretos)..."
if [ ! -f "$APP_DIR/.env" ]; then
    cat > "$APP_DIR/.env" <<'EOF'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nome_do_banco
DB_USER=usuario
DB_PASSWORD=senha
EOF
    echo "      .env criado — edite com suas credenciais reais: nano $APP_DIR/.env"
else
    echo "      .env já existe, mantendo o atual."
fi

echo "===> [4/6] Criando serviço systemd..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Screenshare2 Flask App
After=network.target

[Service]
User=${USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/gunicorn \\
    --workers 3 \\
    --bind 127.0.0.1:5000 \\
    --timeout 120 \\
    app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}
echo "      Serviço ${SERVICE_NAME} ativo."
sudo systemctl status ${SERVICE_NAME} --no-pager -l

echo "===> [5/6] Configurando Nginx..."
sudo apt-get install -y nginx -q

sudo tee /etc/nginx/sites-available/${SERVICE_NAME} > /dev/null <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120;
    }
}
EOF

# Ativar site e remover default se existir
sudo ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/${SERVICE_NAME}
sudo rm -f /etc/nginx/sites-enabled/default

sudo nginx -t
sudo systemctl restart nginx
echo "      Nginx configurado e rodando."

echo "===> [6/6] Instalando SSL (HTTPS) com Certbot..."
sudo apt-get install -y certbot python3-certbot-nginx -q
sudo certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos -m admin@paineldefilas-raizen.com.br --redirect
echo "      SSL instalado com sucesso."

echo ""
echo "============================================="
echo " DEPLOY CONCLUÍDO!"
echo " Acesse: https://${DOMAIN}"
echo "============================================="
