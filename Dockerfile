# Dockerfile all-in-one para ScreenShare
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    python3.11 python3-pip python3-venv \
    postgresql postgresql-contrib postgresql-client \
    curl wget gcc supervisor nginx git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install uvicorn

COPY . .

# Criar diretórios p/ PostgreSQL interno (se usado)
RUN mkdir -p /var/lib/postgresql/data \
    && chown -R postgres:postgres /var/lib/postgresql/data \
    && chmod 700 /var/lib/postgresql/data \
    && mkdir -p /var/run/postgresql \
    && chown postgres:postgres /var/run/postgresql

# MediaMTX
RUN cd /tmp && \
    wget -q https://github.com/bluenviron/mediamtx/releases/download/v1.5.1/mediamtx_v1.5.1_linux_amd64.tar.gz && \
    tar -xzf mediamtx_v1.5.1_linux_amd64.tar.gz && \
    mv mediamtx /usr/local/bin/ && chmod +x /usr/local/bin/mediamtx && \
    rm -rf /tmp/*
RUN mkdir -p /etc/mediamtx
COPY config/mediamtx.yml /etc/mediamtx/mediamtx.yml

# Nginx com SSL
RUN mkdir -p /etc/nginx/ssl /etc/nginx/conf.d
COPY config/nginx.conf /etc/nginx/conf.d/default.conf
COPY config/ssl_letsencrypt/fullchain.pem /etc/nginx/ssl/fullchain.pem
COPY config/ssl_letsencrypt/privkey.pem /etc/nginx/ssl/privkey.pem
RUN chmod 644 /etc/nginx/ssl/fullchain.pem && chmod 600 /etc/nginx/ssl/privkey.pem

# SUPERVISOR
RUN mkdir -p /var/log/supervisor

RUN cat > /etc/supervisor/conf.d/supervisord.conf <<'EOF'
[supervisord]
nodaemon=true

[program:postgresql]
command=/usr/lib/postgresql/14/bin/postgres -D /var/lib/postgresql/data
autostart=true
autorestart=true
user=postgres
priority=10

[program:mediamtx]
command=/usr/local/bin/mediamtx /etc/mediamtx/mediamtx.yml
autostart=true
autorestart=true
priority=20

[program:fastapi]
command=bash -c "python3 -m uvicorn app:app --host 0.0.0.0 --port 8000"
directory=/app
autostart=true
autorestart=true
startsecs=5
priority=30

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
priority=40
EOF

# ENTRYPOINT
COPY <<'EOF' /app/entrypoint.sh
#!/bin/bash
set -e

echo "========================================="
echo "Iniciando ScreenShare All-in-One"
echo "========================================="

# Aguardar 2 segundos
sleep 2

# Variáveis de ambiente (corretas, vindas do docker-compose)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-screenshare}"
DB_PASSWORD="${DB_PASSWORD:-screenshare_secure_pass_123}"
DB_NAME="${DB_NAME:-screenshare}"

echo "[INFO] Usando DATABASE:"
echo "DB_HOST=$DB_HOST"
echo "DB_PORT=$DB_PORT"
echo "DB_USER=$DB_USER"
echo "DB_NAME=$DB_NAME"

# Se banco interno → inicializar
if [ "$DB_HOST" = "localhost" ]; then
    echo "[INFO] Banco interno detectado"
    if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
        echo "[INIT] Inicializando PostgreSQL interno..."
        su - postgres -c "/usr/lib/postgresql/14/bin/initdb -D /var/lib/postgresql/data"
    else
        echo "[OK] PostgreSQL interno já inicializado"
    fi
else
    echo "[INFO] Usando banco externo: $DB_HOST"
fi

# Iniciar supervisor
echo "[OK] Iniciando supervisor..."
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf &
SUPERVISOR_PID=$!

# Aguardar banco estar pronto
echo "[WAIT] Aguardando banco $DB_HOST:$DB_PORT..."
for i in {1..60}; do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; then
        echo "[OK] Banco está pronto!"
        break
    fi
    echo "[WAIT] Tentativa $i/60..."
    sleep 1
done

# Criar banco se não existir
echo "[INIT] Checando database..."
psql "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/postgres" -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || {
    echo "[INIT] Criando database e usuário..."
    psql "postgresql://postgres:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/postgres" <<SQL
CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}' LOGIN;
CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL
}

# MIGRATION
echo "[INIT] Executando migrações..."
python3 migrate_db.py
echo "[OK] Migrações concluídas"

wait $SUPERVISOR_PID
EOF

RUN chmod +x /app/entrypoint.sh

EXPOSE 80 443 8000 8888 8889 9997 5432

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
