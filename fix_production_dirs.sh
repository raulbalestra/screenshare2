#!/bin/bash
#
# Script para corrigir diretórios e permissões em produção
# Execute no servidor: bash fix_production_dirs.sh
#

set -e

echo "========================================"
echo "Corrigindo Diretórios de Produção"
echo "========================================"

# Ir para diretório do projeto
cd /root/screenshare2

echo ""
echo "1. Criando diretórios necessários..."

# Criar diretórios principais
mkdir -p static/images
mkdir -p sessions
mkdir -p hls_streams
mkdir -p /opt/screenshare/uploads
mkdir -p /opt/screenshare/sessions

echo "   ✓ Diretórios principais criados"

echo ""
echo "2. Criando diretórios de localidades..."

# Criar alguns diretórios de localidades comuns
for localidade in curitiba saopaulo riodejaneiro; do
    mkdir -p "static/images/$localidade"
    echo "   ✓ static/images/$localidade"
done

echo ""
echo "3. Configurando permissões..."

# Dar permissões corretas
chmod -R 755 static/images
chmod -R 755 sessions
chmod -R 755 hls_streams
chmod -R 755 /opt/screenshare/uploads
chmod -R 755 /opt/screenshare/sessions

echo "   ✓ Permissões configuradas"

echo ""
echo "4. Verificando estrutura criada..."
echo ""
ls -la static/images/
echo ""

echo "========================================"
echo "✅ Correção concluída!"
echo "========================================"
echo ""
echo "Próximos passos:"
echo "1. Reiniciar aplicação: systemctl restart screenshare"
echo "   OU: pkill -f 'python app.py' && python app.py"
echo ""
echo "2. Testar transmissão em: https://screenshare.itfolkstech.com/curitiba/tela-compartilhada"
echo ""
