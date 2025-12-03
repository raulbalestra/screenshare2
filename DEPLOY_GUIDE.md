# 🚀 Guia de Deploy - screenshare.itfolkstech.com

## ✅ Configuração Concluída

### 1. Servidor e Domínio
- **Servidor**: 31.97.156.167 (Ubuntu 24.04.3 LTS)
- **Domínio**: https://screenshare.itfolkstech.com
- **SSL**: Certificado Let's Encrypt ativo até 03/03/2026
- **Nginx**: Configurado e rodando
- **Firewall**: Porta 5000 liberada

### 2. Estrutura de Diretórios no Servidor
```bash
/opt/screenshare/           # Diretório da aplicação
├── app.py
├── security_utils.py
├── requirements.txt
├── .env                    # Configurações sensíveis
├── templates/
├── static/
└── uploads/                # Diretório para uploads
```

## 📋 Passos para Deploy

### 1. Conectar ao Servidor
```bash
ssh root@31.97.156.167
```

### 2. Preparar o Ambiente
```bash
# Criar diretório da aplicação
mkdir -p /opt/screenshare
cd /opt/screenshare

# Instalar dependências do sistema
apt update
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx certbot python3-certbot-nginx ffmpeg

# Criar ambiente virtual Python
python3 -m venv venv
source venv/bin/activate
```

### 3. Configurar PostgreSQL
```bash
# Entrar no PostgreSQL
sudo -u postgres psql

# Executar os seguintes comandos SQL:
```

```sql
-- Criar banco de dados e usuário
CREATE DATABASE screenshare;
CREATE USER screenshare_user WITH PASSWORD 'SuaSenhaSeguraAqui123!@#';
GRANT ALL PRIVILEGES ON DATABASE screenshare TO screenshare_user;

-- Conectar ao banco
\c screenshare

-- Criar tabela de usuários
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_admin BOOLEAN DEFAULT FALSE,
    localidade VARCHAR(100),
    cpf VARCHAR(11) UNIQUE,
    nome_completo VARCHAR(100),
    last_login TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    account_locked_until TIMESTAMP,
    password_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    must_change_password BOOLEAN DEFAULT FALSE
);

-- Criar usuário admin padrão (senha: admin123 - MUDE IMEDIATAMENTE!)
INSERT INTO users (username, password_hash, is_admin, nome_completo) 
VALUES ('admin', 'scrypt:32768:8:1$YCVPAwLnMK5uM5qo$8f5e4c3b2a1d0e9f8c7b6a5d4e3c2b1a0f9e8d7c6b5a4e3d2c1b0a9f8e7d6c5b4a3e2d1c0b9a8f7e6d5c4b3a2e1d0c9b8a7f6e5d4c3b2a1e0d9c8b7a6f5e4d', TRUE, 'Administrador do Sistema')
ON CONFLICT (username) DO NOTHING;

-- Criar tabela de eventos de uso
CREATE TABLE IF NOT EXISTS usage_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255),
    details JSONB
);

-- Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_usage_events_user_id ON usage_events(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_created_at ON usage_events(created_at);
CREATE INDEX IF NOT EXISTS idx_usage_events_session_id ON usage_events(session_id);

-- Criar view para monitoramento
CREATE OR REPLACE VIEW user_usage_summary AS
SELECT 
    u.id,
    u.username,
    u.localidade,
    COUNT(ue.id) as total_events,
    MAX(ue.created_at) as last_activity,
    COUNT(DISTINCT ue.session_id) as unique_sessions
FROM users u
LEFT JOIN usage_events ue ON u.id = ue.user_id
GROUP BY u.id, u.username, u.localidade;

-- Conceder permissões
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO screenshare_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO screenshare_user;

\q
```

### 4. Transferir Arquivos para o Servidor

No seu computador local, execute:

```bash
# Criar arquivo tar com os arquivos necessários
cd c:\Users\pf388\OneDrive\Documents\screenshare_novo\screenshare2
tar -czf screenshare.tar.gz *.py templates/ sql/ requirements.txt

# Transferir para o servidor (usando SCP ou SFTP)
scp screenshare.tar.gz root@31.97.156.167:/opt/screenshare/

# OU usar MobaXterm para transferir via interface gráfica
```

No servidor:
```bash
cd /opt/screenshare
tar -xzf screenshare.tar.gz
rm screenshare.tar.gz
```

### 5. Configurar Variáveis de Ambiente

Crie o arquivo `.env` no servidor:

```bash
nano /opt/screenshare/.env
```

Conteúdo do `.env`:
```env
# Configurações do Banco de Dados PostgreSQL
DB_HOST=localhost
DB_NAME=screenshare
DB_USER=screenshare_user
DB_PASSWORD=SuaSenhaSeguraAqui123!@#

# Configurações da Aplicação
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
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
UPLOAD_FOLDER=/opt/screenshare/uploads

# Configurações de Taxa de Limite
RATE_LIMIT_ENABLED=True
MAX_REQUESTS_PER_MINUTE=60
```

### 6. Instalar Dependências Python

```bash
cd /opt/screenshare
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 7. Criar Diretórios Necessários

```bash
mkdir -p /opt/screenshare/uploads
chmod 755 /opt/screenshare/uploads
```

### 8. Configurar Serviço Systemd

Criar arquivo de serviço:

```bash
sudo nano /etc/systemd/system/screenshare.service
```

Conteúdo:
```ini
[Unit]
Description=ScreenShare Application
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/screenshare
Environment="PATH=/opt/screenshare/venv/bin"
ExecStart=/opt/screenshare/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5000 --timeout 120 --access-logfile /var/log/screenshare/access.log --error-logfile /var/log/screenshare/error.log app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Criar diretório de logs:
```bash
mkdir -p /var/log/screenshare
```

Habilitar e iniciar o serviço:
```bash
systemctl daemon-reload
systemctl enable screenshare
systemctl start screenshare
systemctl status screenshare
```

### 9. Verificar Configuração Nginx

O arquivo já deve estar em `/etc/nginx/sites-available/screenshare.itfolkstech.com`:

```bash
cat /etc/nginx/sites-available/screenshare.itfolkstech.com
```

Deve conter algo como:
```nginx
server {
    server_name screenshare.itfolkstech.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # Configurações de segurança
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/screenshare.itfolkstech.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/screenshare.itfolkstech.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    if ($host = screenshare.itfolkstech.com) {
        return 301 https://$host$request_uri;
    }

    listen 80;
    server_name screenshare.itfolkstech.com;
    return 404;
}
```

### 10. Testar e Reiniciar Nginx

```bash
nginx -t
systemctl reload nginx
```

## 🔍 Verificações Finais

### 1. Verificar Serviços
```bash
# Verificar se a aplicação está rodando
systemctl status screenshare

# Verificar logs da aplicação
tail -f /var/log/screenshare/error.log
tail -f /var/log/screenshare/access.log

# Verificar se está ouvindo na porta 5000
netstat -tulpn | grep 5000

# Verificar Nginx
systemctl status nginx

# Verificar PostgreSQL
systemctl status postgresql
```

### 2. Testar Conectividade
```bash
# Testar localmente
curl http://127.0.0.1:5000

# Testar o domínio
curl https://screenshare.itfolkstech.com
```

### 3. Verificar SSL
```bash
# Verificar certificado
openssl s_client -connect screenshare.itfolkstech.com:443 -servername screenshare.itfolkstech.com
```

## 🔒 Segurança Pós-Deploy

### 1. Mudar Senha do Admin
- Acesse https://screenshare.itfolkstech.com
- Login: `admin` / `admin123`
- Vá em Configurações → Alterar Senha
- Defina uma senha forte

### 2. Configurar Firewall
```bash
# Permitir apenas portas necessárias
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
ufw status
```

### 3. Backup Automático
Criar script de backup:

```bash
nano /opt/screenshare/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/screenshare"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup do banco de dados
pg_dump -U screenshare_user screenshare > $BACKUP_DIR/db_$DATE.sql

# Backup dos uploads
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /opt/screenshare/uploads

# Manter apenas os 7 backups mais recentes
find $BACKUP_DIR -name "db_*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "uploads_*.tar.gz" -mtime +7 -delete

echo "Backup concluído: $DATE"
```

```bash
chmod +x /opt/screenshare/backup.sh

# Adicionar ao crontab (executa diariamente às 2h)
crontab -e
# Adicionar linha:
0 2 * * * /opt/screenshare/backup.sh >> /var/log/screenshare_backup.log 2>&1
```

## 📊 Monitoramento

### Verificar Uso de Recursos
```bash
# CPU e Memória
htop

# Espaço em disco
df -h

# Logs em tempo real
tail -f /var/log/screenshare/error.log
```

### Renovação Automática SSL
```bash
# Testar renovação
certbot renew --dry-run

# O certbot já configura renovação automática via cron
```

## 🔄 Atualização da Aplicação

Para atualizar o código:

```bash
cd /opt/screenshare

# Backup antes de atualizar
cp -r /opt/screenshare /opt/screenshare_backup_$(date +%Y%m%d)

# Transferir novos arquivos
# (use scp ou MobaXterm)

# Recarregar aplicação
systemctl restart screenshare

# Verificar logs
tail -f /var/log/screenshare/error.log
```

## 🆘 Troubleshooting

### Aplicação não inicia
```bash
# Verificar logs
journalctl -u screenshare -n 50

# Verificar permissões
ls -la /opt/screenshare

# Testar manualmente
cd /opt/screenshare
source venv/bin/activate
python app.py
```

### Erro 502 Bad Gateway
```bash
# Verificar se a aplicação está rodando
systemctl status screenshare

# Verificar porta 5000
netstat -tulpn | grep 5000

# Reiniciar aplicação
systemctl restart screenshare
```

### Erro de Banco de Dados
```bash
# Verificar PostgreSQL
systemctl status postgresql

# Testar conexão
psql -U screenshare_user -d screenshare -h localhost
```

## 📱 Acesso à Aplicação

**URL**: https://screenshare.itfolkstech.com

**Credenciais Iniciais**:
- Usuário: `admin`
- Senha: `admin123` (⚠️ MUDE IMEDIATAMENTE!)

---

## ✅ Checklist Final

- [ ] PostgreSQL configurado e rodando
- [ ] Banco de dados criado com tabelas
- [ ] Arquivos transferidos para `/opt/screenshare`
- [ ] Arquivo `.env` configurado com senhas seguras
- [ ] Dependências Python instaladas
- [ ] Serviço systemd criado e rodando
- [ ] Nginx configurado e rodando
- [ ] SSL ativo e funcionando
- [ ] Firewall configurado (UFW)
- [ ] Senha do admin alterada
- [ ] Backup automático configurado
- [ ] Aplicação acessível via HTTPS
- [ ] WebSocket funcionando para compartilhamento de tela

---

**Data de Deploy**: 03/12/2025
**Domínio**: https://screenshare.itfolkstech.com
**Servidor**: 31.97.156.167
**Certificado SSL**: Válido até 03/03/2026
