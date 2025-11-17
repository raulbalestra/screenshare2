#!/bin/bash
set -e

echo "====================================="
echo " Iniciando ScreenShare API + MediaMTX"
echo "====================================="

# Info do banco
echo "[INFO] Usando banco:"
echo "HOST=${DB_HOST} PORT=${DB_PORT} USER=${DB_USER} DB=${DB_NAME}"

# Aguardar banco estar disponível
echo "[WAIT] Aguardando o banco subir..."
for i in {1..30}; do
    if pg_isready -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} 2>/dev/null; then
        echo "[OK] Banco conectado!"
        break
    fi
    echo "[WAIT] Tentativa $i/30..."
    sleep 2
done

# Criar tabelas
echo "[INIT] Criando tabelas..."
python3 -c "from src.database.models import DatabaseManager; DatabaseManager.create_tables()" || echo "[WARN] Erro ao criar tabelas"

# Migrations
echo "[MIGRATIONS] Rodando migrações..."
python3 migrate_db.py || echo "[WARN] Falha nas migrations (continuando)..."

# Criar admin
echo "[INIT] Criando usuário admin..."
python3 create_admin.py || echo "[INFO] Admin já existe"

# Iniciar supervisor
echo "[START] Iniciando supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
