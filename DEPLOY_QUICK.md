# ⚡ Deploy Rápido - Redis VPS

## 🎯 Passos Resumidos

### 1️⃣ No Windows (Local)

```bash
cd C:\Users\pf388\OneDrive\Documents\screenshare_novo\screenshare2

# Commit
git add .
git commit -m "Implementação Redis com cache e fila"
git push origin main
```

### 2️⃣ No Servidor (SSH)

```bash
# Conectar
ssh root@31.97.156.167

# Instalar Redis
sudo apt update && sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
redis-cli ping

# Atualizar código
cd /root/screenshare2
git pull

# Instalar dependência
pip install redis==5.0.1

# Configurar .env (adicionar ao final)
cat >> .env << 'EOF'

# Redis - Produção
REDIS_ENABLED=True
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_FRAME_TTL=30
REDIS_QUEUE_MAX_SIZE=100
EOF

# Testar Redis
python3 -c "from redis_manager import init_redis_manager; print('OK!' if init_redis_manager().is_available() else 'ERRO')"

# Reiniciar app no tmux
tmux attach -t novo_screenshare
# Ctrl+C depois:
python app.py
```

### 3️⃣ Validar

```bash
# Ver logs (procure: "Redis conectado")
# Abra: https://screenshare.itfolkstech.com
# Teste transmissão
# Verifique logs: "Frame servido do Redis"
```

---

## 📋 Checklist Rápido

- [ ] `git push` feito ✅
- [ ] Redis instalado: `redis-cli ping` → PONG ✅
- [ ] Código atualizado: `git pull` ✅
- [ ] Dependência: `pip install redis==5.0.1` ✅
- [ ] .env configurado: `grep REDIS .env` ✅
- [ ] App reiniciado e logs OK ✅
- [ ] Transmissão funcionando ✅

---

## 🐛 Troubleshooting Ultra-Rápido

```bash
# Redis não inicia
systemctl status redis-server

# App não conecta
redis-cli ping
cat .env | grep REDIS

# Performance não melhorou
curl -I https://screenshare.itfolkstech.com/serve_pil_image/curitiba/screen.png | grep X-Frame-Source
# Deve retornar: X-Frame-Source: redis
```

---

## 📊 Comandos Úteis

```bash
# Status Redis
systemctl status redis-server

# Monitor comandos
redis-cli monitor

# Ver fila
redis-cli llen "queue:curitiba:frames"

# Stats via API
curl https://screenshare.itfolkstech.com/admin/redis/stats

# Logs app
tail -f /root/screenshare2/app.log | grep redis
```

---

**Pronto! Deploy completo em ~5 minutos** 🚀
