FROM python:3.11-slim

# Melhor prática: variáveis básicas
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y \
    wget \
    supervisor \
    curl \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ===== Instalando dependências do Python =====
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===== Instalando MediaMTX =====
RUN wget -q https://github.com/bluenviron/mediamtx/releases/download/v1.5.1/mediamtx_v1.5.1_linux_amd64.tar.gz && \
    tar -xzf mediamtx_v1.5.1_linux_amd64.tar.gz && \
    mv mediamtx /usr/local/bin/mediamtx && \
    chmod +x /usr/local/bin/mediamtx && \
    rm -f mediamtx_v1.5.1_linux_amd64.tar.gz

COPY config/mediamtx.yml /etc/mediamtx.yml

# Copia código da aplicação
COPY . .

# ===== Supervisor =====
RUN mkdir -p /var/log/supervisor

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ===== Entrypoint com Migrations =====
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000 8888 8889 9997

ENTRYPOINT ["/entrypoint.sh"]
