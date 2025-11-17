#!/bin/bash
# Script para iniciar MediaMTX no Windows via WSL/Git Bash

cd "$(dirname "$0")" || exit

echo "Iniciando MediaMTX..."
echo "Aguarde alguns segundos..."
echo ""

# Executar mediamtx.exe diretamente
./mediamtx.exe config/mediamtx.yml 2>&1 &

# Capturar PID
PID=$!
echo "MediaMTX iniciado com PID: $PID"
echo "Portas: HLS=8888, WHIP=8889, API=9997"
echo ""
echo "Pressione Ctrl+C para parar"

# Manter o script rodando
wait $PID
