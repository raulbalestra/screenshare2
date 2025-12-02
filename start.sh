#!/bin/bash

# Script de inicialização simplificado para Render
echo "Iniciando aplicação ScreenShare2..."

# Definir variáveis de ambiente
export FLASK_APP=app.py
export FLASK_ENV=production

# Criar diretórios necessários se não existirem
mkdir -p sessions uploads logs

# Definir porta padrão do Render ou usar 5000 como fallback
export PORT=${PORT:-5000}

echo "Iniciando servidor na porta $PORT..."

# Usar gunicorn para produção (mais estável que o servidor dev do Flask)
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --preload app:app