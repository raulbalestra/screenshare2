# Dockerfile all-in-one para ScreenShare
# Rodas API FastAPI + MediaMTX + PostgreSQL em um único container

FROM ubuntu:22.04

# Definir variáveis
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    curl \
    wget \
    gcc \
    postgresql-client \
    supervisor \
    nginx \
    git \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# ===== SETUP PYTHON =====
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install uvicorn

# Copiar código da aplicação
COPY . .

# ===== SETUP PostgreSQL =====
RUN mkdir -p /var/lib/postgresql/data && \
    chown -R postgres:postgres /var/lib/postgresql/data && \
    chmod 700 /var/lib/postgresql/data && \
    mkdir -p /var/run/postgresql && \
    chown postgres:postgres /var/run/postgresql

# Inicializar banco de dados PostgreSQL
RUN su - postgres -c "/usr/lib/postgresql/14/bin/initdb -D /var/lib/postgresql/data" || true

# ===== SETUP MediaMTX =====
RUN cd /tmp && \
    wget -q https://github.com/bluenviron/mediamtx/releases/download/v1.5.1/mediamtx_v1.5.1_linux_amd64.tar.gz && \
    tar -xzf mediamtx_v1.5.1_linux_amd64.tar.gz && \
    mv mediamtx /usr/local/bin/ && \
    chmod +x /usr/local/bin/mediamtx && \
    rm -rf /tmp/*

# Copiar configuração do MediaMTX
RUN mkdir -p /etc/mediamtx
COPY config/mediamtx.yml /etc/mediamtx/mediamtx.yml

# ===== SETUP Nginx com SSL =====
RUN mkdir -p /etc/nginx/ssl /etc/nginx/conf.d
COPY config/nginx.conf /etc/nginx/conf.d/default.conf
COPY config/ssl_letsencrypt/fullchain.pem /etc/nginx/ssl/fullchain.pem
COPY config/ssl_letsencrypt/privkey.pem /etc/nginx/ssl/privkey.pem
RUN chmod 644 /etc/nginx/ssl/fullchain.pem && \
    chmod 600 /etc/nginx/ssl/privkey.pem

# ===== SETUP Supervisor para gerenciar processos =====
RUN mkdir -p /var/log/supervisor

RUN cat > /etc/supervisor/conf.d/supervisord.conf <<'SUPERVISOR_EOF'
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid
user=root

[program:postgresql]
command=/usr/lib/postgresql/14/bin/postgres -D /var/lib/postgresql/data
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/postgres.err.log
stdout_logfile=/var/log/supervisor/postgres.out.log
user=postgres
priority=999

[program:mediamtx]
command=/usr/local/bin/mediamtx /etc/mediamtx/mediamtx.yml
autostart=true
autorestart=true
startsecs=10
stderr_logfile=/var/log/supervisor/mediamtx.err.log
stdout_logfile=/var/log/supervisor/mediamtx.out.log
priority=998

[program:fastapi]
command=bash -c "sleep 5 && python3 migrate_db.py && python3 -m uvicorn app:app --host 0.0.0.0 --port 8000"
directory=/app
autostart=true
autorestart=true
startsecs=15
stderr_logfile=/var/log/supervisor/fastapi.err.log
stdout_logfile=/var/log/supervisor/fastapi.out.log
priority=997

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/nginx.err.log
stdout_logfile=/var/log/supervisor/nginx.out.log
priority=996

[unix_http_server]
file=/var/run/supervisor.sock
chmod=0700

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface
SUPERVISOR_EOF

# Criar script de inicialização
RUN mkdir -p /app/logs

COPY <<'EOF' /app/entrypoint.sh
#!/bin/bash
set -e

echo "=========================================="
echo "Iniciando ScreenShare All-in-One"
echo "=========================================="

# Aguardar um pouco
sleep 2

# Garantir permissões corretas no diretório PostgreSQL
mkdir -p /var/lib/postgresql/data
chown -R postgres:postgres /var/lib/postgresql/data
chmod 700 /var/lib/postgresql/data
mkdir -p /var/run/postgresql
chown postgres:postgres /var/run/postgresql
chmod 775 /var/run/postgresql

# Verificar e inicializar PostgreSQL se necessário
if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
    echo "[INIT] Inicializando PostgreSQL..."
    su - postgres -c "/usr/lib/postgresql/14/bin/initdb -D /var/lib/postgresql/data" || true
else
    echo "[OK] PostgreSQL já inicializado"
fi

# Iniciar supervisor
echo "[OK] Iniciando supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
EOF

RUN chmod +x /app/entrypoint.sh

# Expor portas
EXPOSE 80 443 8000 8888 8889 9997 5432

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Criar diretórios necessários
RUN mkdir -p /app/logs && \
    mkdir -p /var/run/postgresql && \
    mkdir -p /var/lib/postgresql/data && \
    chown -R postgres:postgres /var/lib/postgresql/data && \
    chmod 700 /var/lib/postgresql/data && \
    chown -R postgres:postgres /var/run/postgresql && \
    chmod 775 /var/run/postgresql

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
