#!/bin/bash

# Script de inicialização para Render
# Este script prepara e inicia a aplicação ScreenShare2

echo "Iniciando aplicação ScreenShare2..."

# Definir variáveis de ambiente
export FLASK_APP=app.py
export FLASK_ENV=production

# Criar diretórios necessários se não existirem
mkdir -p sessions
mkdir -p uploads
mkdir -p logs

# Definir porta padrão do Render ou usar 5000 como fallback
export PORT=${PORT:-5000}

echo "Configurando permissões..."
# Dar permissões de execução se necessário
chmod +x app.py

echo "Verificando dependências..."
# Verificar se todas as dependências estão instaladas
python -c "import flask, psycopg2, dotenv" || {
    echo "Erro: Dependências não encontradas. Instalando..."
    pip install -r requirements.txt
}

echo "Iniciando servidor na porta $PORT..."
# Usar gunicorn para produção (mais estável que o servidor dev do Flask)
if command -v gunicorn &> /dev/null; then
    echo "Usando Gunicorn para produção..."
    exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
else
    echo "Gunicorn não encontrado, usando Flask dev server..."
    exec python app.py
fi