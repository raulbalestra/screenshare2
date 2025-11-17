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
    git \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# ===== SETUP PYTHON =====
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar código da aplicação
COPY . .

# ===== SETUP PostgreSQL =====
RUN mkdir -p /var/run/postgresql && \
    chown postgres:postgres /var/run/postgresql && \
    mkdir -p /app/data/postgres && \
    chown -R postgres:postgres /app/data/postgres

# Inicializar banco de dados PostgreSQL
RUN sudo -u postgres /usr/lib/postgresql/14/bin/initdb -D /app/data/postgres || true

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

# ===== SETUP Supervisor para gerenciar processos =====
RUN mkdir -p /var/log/supervisor

COPY <<EOF /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:postgresql]
command=/usr/lib/postgresql/14/bin/postgres -D /app/data/postgres
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/postgres.err.log
stdout_logfile=/var/log/supervisor/postgres.out.log
user=postgres

[program:mediamtx]
command=/usr/local/bin/mediamtx /etc/mediamtx/mediamtx.yml
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/mediamtx.err.log
stdout_logfile=/var/log/supervisor/mediamtx.out.log

[program:fastapi]
command=bash -c "sleep 3 && python migrate_db.py && uvicorn app:app --host 0.0.0.0 --port 8000"
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/fastapi.err.log
stdout_logfile=/var/log/supervisor/fastapi.out.log

[unix_http_server]
file=/var/run/supervisor.sock
chmod=0700

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface
EOF

# Criar script de inicialização
RUN mkdir -p /app/logs

COPY <<'EOF' /app/entrypoint.sh
#!/bin/bash
set -e

echo "Aguardando inicialização do PostgreSQL..."
sleep 5

# Verificar se banco foi inicializado
if [ ! -f /app/data/postgres/PG_VERSION ]; then
    echo "Inicializando PostgreSQL..."
    sudo -u postgres /usr/lib/postgresql/14/bin/initdb -D /app/data/postgres
fi

# Iniciar supervisor
echo "Iniciando todos os serviços..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
EOF

RUN chmod +x /app/entrypoint.sh

# Expor portas
EXPOSE 8000 8888 8889 9997 5432

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Criar diretórios necessários
RUN mkdir -p /app/logs && \
    mkdir -p /var/run/postgresql && \
    chown -R postgres:postgres /var/run/postgresql

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
