# 🐳 Teste Local com Docker - Redis ScreenShare

**Data:** 11 de dezembro de 2025  
**Objetivo:** Testar Redis localmente no Windows usando Docker antes de subir para produção

---

## 📋 Pré-requisitos

### 1. Instalar Docker Desktop no Windows

Se ainda não tiver Docker instalado:

1. Baixe Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Instale e reinicie o computador se necessário
3. Abra Docker Desktop e aguarde inicializar
4. Verifique a instalação:

```bash
docker --version
docker-compose --version
```

**Esperado:**
```
Docker version 24.x.x
Docker Compose version v2.x.x
```

---

## 🚀 Passo 1: Iniciar Redis com Docker

### Opção A: Usar docker-compose (RECOMENDADO)

```bash
# No diretório do projeto
cd c:\Users\pf388\OneDrive\Documents\screenshare_novo\screenshare2

# Iniciar Redis
docker-compose up -d

# Verificar se está rodando
docker-compose ps
```

**Esperado:**
```
NAME                 STATUS              PORTS
screenshare_redis    Up (healthy)        0.0.0.0:6379->6379/tcp
```

### Opção B: Comando direto Docker

```bash
docker run -d \
  --name screenshare_redis \
  -p 6379:6379 \
  redis:7-alpine
```

---

## 🧪 Passo 2: Testar Conexão Redis

### Testar com redis-cli (dentro do container)

```bash
# Conectar ao container
docker exec -it screenshare_redis redis-cli

# Dentro do redis-cli, testar:
127.0.0.1:6379> ping
# Esperado: PONG

127.0.0.1:6379> set test "hello"
# Esperado: OK

127.0.0.1:6379> get test
# Esperado: "hello"

127.0.0.1:6379> exit
```

### Testar direto (sem entrar no container)

```bash
docker exec screenshare_redis redis-cli ping
# Esperado: PONG
```

---

## 📦 Passo 3: Instalar Dependências Python

```bash
cd c:\Users\pf388\OneDrive\Documents\screenshare_novo\screenshare2

# Instalar biblioteca redis
pip install redis==5.0.1

# Ou instalar todas as dependências
pip install -r requirements.txt
```

---

## ✅ Passo 4: Verificar Configuração

Seu arquivo `.env` já está configurado corretamente:

```env
REDIS_ENABLED=True
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_FRAME_TTL=30
REDIS_QUEUE_MAX_SIZE=100
```

✅ **Nenhuma alteração necessária!**

---

## 🧪 Passo 5: Executar Testes Automatizados

```bash
# Teste completo do Redis
python test_redis.py
```

**Saída esperada:**
```
==========================================================
  REDIS IMPLEMENTATION - TEST SUITE
==========================================================

✅ TESTE 1: Conexão com Redis - PASSOU
✅ TESTE 2: Salvar e Recuperar Frame - PASSOU
✅ TESTE 3: Sistema de Fila FIFO - PASSOU
✅ TESTE 4: Estatísticas Redis - PASSOU
✅ TESTE 5: Performance Comparison - PASSOU
   Redis: 3.42ms | Disco: 18.76ms
   🚀 Speedup: 5.48x mais rápido
✅ TESTE 6: Metadados do Frame - PASSOU

==========================================================
  RESULTADO FINAL: 6/6 testes passaram
==========================================================

🎉 SUCESSO! Todos os testes passaram!
```

---

## 🎬 Passo 6: Testar Aplicação Completa

### 6.1. Iniciar Aplicação

```bash
python app.py
```

**Logs esperados:**
```
[INIT] Inicializando Redis Manager...
✓ Conectado ao Redis em localhost:6379 (DB 0)
  TTL de frames: 30s | Tamanho máximo da fila: 100
[INIT] ✓ Redis conectado e pronto para uso
```

### 6.2. Testar Transmissão

1. Abra navegador: `http://localhost:5000`
2. Login: `curitiba_user` / `senha_curitiba`
3. Clique em "Compartilhar Tela"
4. Selecione tela e inicie transmissão

**Logs esperados:**
```
[upload_frame] ✓ Frame de curitiba salvo no Redis
[upload_frame] ✓ Frame de curitiba salvo no disco
Frame salvo para curitiba por curitiba_user (Redis: True, Disco: True)
```

### 6.3. Visualizar Transmissão

1. Nova aba: `http://localhost:5000/tela/curitiba`
2. Deve ver a tela sendo transmitida

**Logs esperados:**
```
[serve_pil_image] ✓ Frame de curitiba servido do Redis (45231 bytes)
```

### 6.4. Verificar Estatísticas (Admin)

1. Login como admin: `admin` / `admin`
2. Acesse: `http://localhost:5000/admin/redis/stats`

**Resposta esperada:**
```json
{
  "status": "ok",
  "stats": {
    "cache_hits": 25,
    "cache_misses": 2,
    "cache_hit_rate": 92.59,
    "frames_saved": 30,
    "frames_queued": 30,
    "errors": 0,
    "redis_available": true
  }
}
```

---

## 📊 Passo 7: Monitorar Redis (Opcional)

### Ver comandos em tempo real

```bash
docker exec screenshare_redis redis-cli monitor
```

### Ver estatísticas

```bash
docker exec screenshare_redis redis-cli info stats
```

### Ver chaves armazenadas

```bash
docker exec screenshare_redis redis-cli keys "*"
```

### Ver frames salvos

```bash
# Ver frame de Curitiba
docker exec screenshare_redis redis-cli get "frame:curitiba:current"

# Ver tamanho da fila
docker exec screenshare_redis redis-cli llen "queue:curitiba:frames"
```

---

## 🎯 Validação Final Local

Execute este checklist:

```bash
# 1. Docker está rodando
docker ps | grep screenshare_redis
# ✅ Deve mostrar container UP

# 2. Redis responde
docker exec screenshare_redis redis-cli ping
# ✅ PONG

# 3. Testes automatizados passam
python test_redis.py
# ✅ 6/6 testes passaram

# 4. Aplicação conecta ao Redis
python app.py
# ✅ Logs mostram "Redis conectado"

# 5. Upload funciona
# Inicie transmissão e observe logs
# ✅ "Frame salvo no Redis"

# 6. Download do Redis funciona
# Abra /tela/curitiba e observe logs
# ✅ "Frame servido do Redis"

# 7. Estatísticas funcionam
curl http://localhost:5000/admin/redis/stats
# ✅ {"status": "ok", ...}
```

---

## 🔄 Comandos Úteis Docker

### Gerenciar container

```bash
# Iniciar Redis
docker-compose up -d

# Parar Redis (mantém dados)
docker-compose stop

# Parar e remover (apaga dados)
docker-compose down

# Parar e remover incluindo volumes
docker-compose down -v

# Ver logs do Redis
docker-compose logs -f redis

# Reiniciar Redis
docker-compose restart

# Ver status
docker-compose ps
```

### Debug

```bash
# Entrar no container
docker exec -it screenshare_redis sh

# Ver logs do Redis
docker logs screenshare_redis -f

# Verificar uso de memória
docker stats screenshare_redis

# Inspecionar container
docker inspect screenshare_redis
```

---

## 🐛 Troubleshooting

### Problema: "Cannot connect to Docker daemon"

**Solução:**
1. Abra Docker Desktop
2. Aguarde inicializar completamente
3. Tente novamente

### Problema: "Port 6379 already in use"

**Solução:**
```bash
# Ver o que está usando a porta
netstat -ano | findstr :6379

# Parar container existente
docker stop screenshare_redis
docker rm screenshare_redis

# Ou mudar a porta no docker-compose.yml:
ports:
  - "6380:6379"  # Usar 6380 no host

# E no .env:
REDIS_PORT=6380
```

### Problema: "Testes falhando"

**Diagnóstico:**
```bash
# 1. Verificar se Redis está UP
docker ps | grep redis

# 2. Verificar conectividade
docker exec screenshare_redis redis-cli ping

# 3. Ver logs do Redis
docker logs screenshare_redis

# 4. Testar conexão Python
python -c "import redis; r=redis.Redis(); print(r.ping())"
```

### Problema: "Aplicação não conecta ao Redis"

**Verificar:**
```bash
# 1. Variável de ambiente
cat .env | grep REDIS_ENABLED
# Deve ser: REDIS_ENABLED=True

# 2. Host correto
cat .env | grep REDIS_HOST
# Deve ser: REDIS_HOST=localhost

# 3. Porta correta
cat .env | grep REDIS_PORT
# Deve ser: REDIS_PORT=6379

# 4. Testar diretamente
python -c "from redis_manager import init_redis_manager; m=init_redis_manager(); print(m.is_available())"
# Deve imprimir: True
```

---

## 🌍 Após Validar Local → Deploy em Produção

### Quando tudo funcionar localmente:

1. ✅ **Parar Docker local**
```bash
docker-compose stop
```

2. ✅ **Conectar ao servidor**
```bash
ssh root@31.97.156.167
```

3. ✅ **Instalar Redis no servidor**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
redis-cli ping  # Deve retornar: PONG
```

4. ✅ **Atualizar código**
```bash
cd /root/screenshare2
git pull origin backup-commit-c083e14
pip install redis==5.0.1
```

5. ✅ **Verificar .env produção**
```bash
cat .env | grep REDIS
# Deve ter todas as configurações Redis
```

6. ✅ **Reiniciar aplicação**
```bash
tmux attach -t novo_screenshare
# Ctrl+C para parar
python app.py
# Observe: "[INIT] ✓ Redis conectado"
```

7. ✅ **Monitorar logs**
```bash
tail -f app.log | grep -i redis
```

---

## 📈 Comparação: Local vs Produção

| Aspecto | Local (Docker) | Produção (VPS) |
|---------|----------------|----------------|
| Redis | Container Docker | Processo nativo |
| Instalação | `docker-compose up -d` | `apt install redis-server` |
| Configuração | docker-compose.yml | /etc/redis/redis.conf |
| Persistência | Volume Docker | Disco do servidor |
| Performance | Boa (virtualizado) | Melhor (nativo) |
| Gerenciamento | Docker commands | systemctl commands |

---

## 🎯 Checklist de Sucesso

Antes de ir para produção, confirme:

- [ ] Docker Desktop instalado e rodando
- [ ] Container Redis UP: `docker ps`
- [ ] Redis responde: `docker exec screenshare_redis redis-cli ping`
- [ ] Dependências instaladas: `pip list | grep redis`
- [ ] Testes passam: `python test_redis.py` → 6/6 ✅
- [ ] App conecta: logs mostram "Redis conectado"
- [ ] Upload salva no Redis: logs mostram "Frame salvo no Redis"
- [ ] Download busca do Redis: logs mostram "Frame servido do Redis"
- [ ] Header correto: `X-Frame-Source: redis`
- [ ] Estatísticas funcionam: `/admin/redis/stats` retorna dados
- [ ] Cache hit rate > 80% após alguns minutos de uso
- [ ] Performance melhorou visualmente (transmissão mais fluida)

**Só siga para produção após TODOS os itens acima estarem ✅**

---

## 💡 Dicas

1. **Mantenha Docker Desktop aberto** enquanto testa
2. **Use logs** para debug: `docker logs screenshare_redis -f`
3. **Monitor em tempo real**: `docker exec screenshare_redis redis-cli monitor`
4. **Limpe dados** se necessário: `docker-compose down -v`
5. **Performance**: Docker no Windows é ~10-20% mais lento que nativo, mas suficiente para testes

---

## 🎉 Próximo Passo

**Execute agora:**

```bash
# 1. Iniciar Redis
docker-compose up -d

# 2. Verificar
docker exec screenshare_redis redis-cli ping

# 3. Testar
python test_redis.py

# 4. Se tudo passar, iniciar app
python app.py
```

**Boa sorte! 🚀**
