# ⚡ Quick Start - Redis Implementation

## 🚀 Instalação e Teste Rápido (5 minutos)

### Windows (WSL)

```bash
# 1. Instalar WSL se ainda não tiver
wsl --install

# 2. No WSL, executar script de instalação
cd /mnt/c/Users/pf388/OneDrive/Documents/screenshare_novo/screenshare2
chmod +x install_redis.sh
./install_redis.sh

# 3. Testar Redis
python test_redis.py

# 4. Iniciar aplicação
python app.py
```

### Linux (VPS Produção)

```bash
# 1. SSH no servidor
ssh root@31.97.156.167

# 2. Ir para diretório
cd /root/screenshare2

# 3. Executar instalação
chmod +x install_redis.sh
./install_redis.sh

# 4. Testar
python test_redis.py

# 5. Deploy
git pull
pip install redis==5.0.1
tmux attach -t novo_screenshare
# Ctrl+C e depois:
python app.py
```

---

## 📋 Comandos Essenciais

### Gerenciar Redis

```bash
# Iniciar
sudo systemctl start redis-server

# Parar
sudo systemctl stop redis-server

# Status
sudo systemctl status redis-server

# Reiniciar
sudo systemctl restart redis-server

# Logs
sudo journalctl -u redis-server -f
```

### Testar Redis

```bash
# Ping
redis-cli ping

# Info
redis-cli info

# Monitor em tempo real
redis-cli monitor

# Estatísticas
redis-cli info stats

# Chaves ativas
redis-cli keys "frame:*"

# Ver fila
redis-cli llen "queue:curitiba:frames"
```

### Aplicação

```bash
# Testar Redis
python test_redis.py

# Iniciar app
python app.py

# Ver logs (buscar Redis)
tail -f app.log | grep -i redis

# Estatísticas via API
curl http://localhost:5000/admin/redis/stats

# Info da fila
curl http://localhost:5000/admin/redis/queue/curitiba
```

---

## 🧪 Teste Rápido Manual

### 1. Testar Conexão

```bash
redis-cli ping
# Esperado: PONG
```

### 2. Testar SET/GET

```bash
redis-cli SET test "hello"
redis-cli GET test
# Esperado: "hello"
```

### 3. Testar Python

```python
python3 << EOF
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
print("Ping:", r.ping())
r.set('test', 'python_works')
print("Get:", r.get('test'))
EOF
```

### 4. Testar Aplicação

```bash
# Terminal 1: Iniciar app
python app.py

# Terminal 2: Fazer upload simulado
curl -X POST http://localhost:5000/upload_frame/curitiba \
  -H "Content-Type: multipart/form-data" \
  -F "frame=@test_image.png" \
  -F "csrf_token=TOKEN"

# Terminal 3: Ver no Redis
redis-cli GET "frame:curitiba:current"
```

---

## 🔍 Debug Rápido

### Redis não conecta

```bash
# Verificar se está rodando
ps aux | grep redis

# Verificar porta
netstat -tulpn | grep 6379

# Tentar iniciar manualmente
redis-server /etc/redis/redis.conf
```

### Aplicação não usa Redis

```bash
# Verificar .env
cat .env | grep REDIS_ENABLED
# Deve ser: REDIS_ENABLED=True

# Verificar logs da inicialização
python app.py 2>&1 | head -n 20
# Procure por: "[INIT] ✓ Redis conectado"
```

### Performance não melhorou

```bash
# Verificar header da resposta
curl -I http://localhost:5000/serve_pil_image/curitiba/screen.png | grep X-Frame-Source
# Esperado: X-Frame-Source: redis

# Se retornar "disk", verificar:
redis-cli keys "frame:*"  # Deve ter frames
redis-cli GET "frame:curitiba:current"  # Deve ter dados
```

---

## 📊 Monitoramento

### Dashboard Redis (opcional)

```bash
# Instalar RedisInsight
# https://redis.com/redis-enterprise/redis-insight/

# Ou usar redis-cli
watch -n 1 'redis-cli info stats | grep instantaneous'
```

### Estatísticas da Aplicação

```bash
# Via browser (como admin)
http://localhost:5000/admin/redis/stats

# Via curl
watch -n 5 'curl -s http://localhost:5000/admin/redis/stats | jq'
```

### Monitorar Operações

```bash
# Terminal 1: Monitor Redis
redis-cli monitor

# Terminal 2: Usar aplicação
# Observe comandos SET/GET aparecendo no monitor
```

---

## 🎯 Validação Final

Execute este checklist antes de considerar pronto:

```bash
# 1. Redis responde
redis-cli ping
# ✅ PONG

# 2. Teste automatizado passa
python test_redis.py
# ✅ 6/6 testes passaram

# 3. App conecta ao Redis
python app.py 2>&1 | grep "Redis conectado"
# ✅ [INIT] ✓ Redis conectado e pronto para uso

# 4. Upload salva no Redis
curl -X POST [...] && redis-cli keys "frame:*"
# ✅ frame:curitiba:current

# 5. Download busca do Redis
curl -I [...] | grep X-Frame-Source
# ✅ X-Frame-Source: redis

# 6. Estatísticas funcionam
curl http://localhost:5000/admin/redis/stats
# ✅ {"status": "ok", "stats": {...}}
```

---

## 📖 Documentação Completa

- **REDIS_IMPLEMENTATION_GUIDE.md** - Guia detalhado de implementação
- **REDIS_SUMMARY.md** - Resumo executivo e arquitetura
- **test_redis.py** - Suite de testes automatizados
- **redis_manager.py** - Código-fonte do gerenciador

---

## 🆘 Suporte

Se algo não funcionar:

1. Verifique Redis: `redis-cli ping`
2. Verifique logs: `tail -f app.log`
3. Execute testes: `python test_redis.py`
4. Revise .env: `REDIS_ENABLED=True`
5. Sistema funciona em fallback (disco) se Redis falhar

**Lembre-se:** A implementação é híbrida - sempre salva no disco como backup!
