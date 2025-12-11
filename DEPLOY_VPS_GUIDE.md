# 🚀 Deploy Redis para VPS - Guia Completo

**Data:** 11 de dezembro de 2025  
**Servidor:** 31.97.156.167 (srv875853)  
**Domínio:** screenshare.itfolkstech.com

---

## 📋 Pré-requisitos

- ✅ Código testado localmente com Docker
- ✅ Testes passando: `python test_redis.py`
- ✅ Aplicação funcionando local
- ✅ Git configurado com código commitado

---

## 🎯 Estratégia de Deploy

### Etapas:

1. **Commit e Push** do código local
2. **SSH na VPS** e instalar Redis
3. **Pull do código** atualizado
4. **Instalar dependências** Python
5. **Configurar .env** de produção
6. **Testar Redis** no servidor
7. **Reiniciar aplicação** no tmux
8. **Validar funcionamento**

---

## 📦 PASSO 1: Commit e Push do Código

### No seu Windows (terminal local):

```bash
cd C:\Users\pf388\OneDrive\Documents\screenshare_novo\screenshare2

# Ver mudanças
git status

# Adicionar todos os arquivos novos
git add .

# Commit
git commit -m "Implementação Redis com sistema de cache e fila

- Adicionado redis_manager.py para gerenciamento de frames
- Sistema híbrido Redis + Disco com fallback automático
- Cache de frames com TTL de 30 segundos
- Sistema de fila FIFO com limite de 100 frames
- Limpeza automática do Redis ao parar transmissão
- Rotas de monitoramento: /admin/redis/stats e /admin/redis/queue
- Testes automatizados completos (6 testes)
- Documentação completa (REDIS_IMPLEMENTATION_GUIDE.md)
- Suporte Docker para desenvolvimento local"

# Push para repositório
git push origin main
# OU se sua branch principal é master:
# git push origin master
```

---

## 🖥️ PASSO 2: Opção A - Script Automatizado (RECOMENDADO)

### Execute o script de deploy:

```bash
# Dar permissão de execução
chmod +x deploy_redis_vps.sh

# Executar deploy
./deploy_redis_vps.sh
```

**O script vai fazer TUDO automaticamente:**
- ✅ Instalar Redis no servidor
- ✅ Atualizar código
- ✅ Instalar dependências
- ✅ Configurar .env
- ✅ Testar Redis
- ✅ Reiniciar aplicação

---

## 🖥️ PASSO 2: Opção B - Deploy Manual (Passo a Passo)

Se preferir fazer manualmente:

### 2.1. SSH no Servidor

```bash
ssh root@31.97.156.167
```

### 2.2. Instalar Redis

```bash
# Atualizar pacotes
sudo apt update

# Instalar Redis
sudo apt install -y redis-server

# Verificar instalação
redis-server --version

# Habilitar no boot
sudo systemctl enable redis-server

# Iniciar Redis
sudo systemctl start redis-server

# Verificar status
sudo systemctl status redis-server

# Testar conexão
redis-cli ping
# Deve retornar: PONG
```

### 2.3. Atualizar Código

```bash
cd /root/screenshare2

# Backup do .env atual
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Pull do código
git pull origin main
# OU: git pull origin master
```

### 2.4. Instalar Dependências Python

```bash
# Instalar biblioteca redis
pip install redis==5.0.1

# Verificar instalação
python3 -c "import redis; print('Redis:', redis.__version__)"
```

### 2.5. Configurar .env de Produção

```bash
# Adicionar configurações Redis ao .env
cat >> .env << 'EOF'

# Configurações do Redis - PRODUÇÃO
REDIS_ENABLED=True
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_FRAME_TTL=30
REDIS_QUEUE_MAX_SIZE=100
EOF

# Verificar configurações
cat .env | grep REDIS
```

### 2.6. Testar Redis

```bash
# Teste rápido Python
python3 << 'EOF'
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
print("Ping:", r.ping())
print("✓ Redis funcionando!")
EOF

# Teste do RedisFrameManager
python3 << 'EOF'
from redis_manager import init_redis_manager
rm = init_redis_manager()
print("Disponível:", rm.is_available())
print("Stats:", rm.get_stats())
print("✓ RedisFrameManager OK!")
EOF
```

### 2.7. Reiniciar Aplicação

```bash
# Conectar ao tmux
tmux attach -t novo_screenshare

# No tmux:
# 1. Pressione Ctrl+C para parar a aplicação
# 2. Execute:
python app.py

# Procure nos logs por:
# [INIT] ✓ Redis conectado e pronto para uso
```

---

## ✅ PASSO 3: Validação

### 3.1. Verificar Logs no Servidor

Nos logs da aplicação, procure por:

```
[INIT] Inicializando Redis Manager...
✓ Conectado ao Redis em localhost:6379 (DB 0)
  TTL de frames: 30s | Tamanho máximo da fila: 100
[INIT] ✓ Redis conectado e pronto para uso
```

### 3.2. Testar Transmissão

1. **Acesse:** https://screenshare.itfolkstech.com
2. **Login:** `curitiba_user` / `senha_curitiba`
3. **Inicie transmissão** de tela
4. **Observe logs no tmux:**

```
[upload_frame] ✓ Frame de curitiba salvo no Redis
[upload_frame] ✓ Frame de curitiba salvo no disco
Frame salvo para curitiba (Redis: True, Disco: True)
```

### 3.3. Visualizar Transmissão

1. **Abra outra aba:** https://screenshare.itfolkstech.com/tela/curitiba
2. **Observe logs:**

```
[serve_pil_image] ✓ Frame de curitiba servido do Redis (45231 bytes)
```

### 3.4. Verificar Estatísticas Redis

Como admin, acesse:

```
https://screenshare.itfolkstech.com/admin/redis/stats
```

Deve retornar:

```json
{
  "status": "ok",
  "stats": {
    "cache_hits": 50,
    "cache_misses": 2,
    "cache_hit_rate": 96.15,
    "frames_saved": 60,
    "frames_queued": 60,
    "redis_available": true
  }
}
```

---

## 🔍 Monitoramento

### Comandos Redis

```bash
# Status do serviço
systemctl status redis-server

# Ver logs Redis
journalctl -u redis-server -f

# Conectar ao Redis CLI
redis-cli

# Dentro do redis-cli:
> ping
> keys "frame:*"
> get "frame:curitiba:current"
> llen "queue:curitiba:frames"
> info stats
> exit
```

### Monitorar Comandos em Tempo Real

```bash
redis-cli monitor
```

### Ver Info de Memória

```bash
redis-cli info memory
```

### Ver Estatísticas

```bash
redis-cli info stats
```

---

## 🧪 Teste de Carga (Opcional)

### No servidor:

```bash
cd /root/screenshare2

# Executar teste de stress (se existir)
python stress_test.py
```

### Monitorar durante teste:

```bash
# Terminal 1: Monitor Redis
redis-cli monitor

# Terminal 2: Logs da aplicação
tail -f app.log | grep -i redis

# Terminal 3: Stats Redis
watch -n 2 'curl -s https://screenshare.itfolkstech.com/admin/redis/stats | jq'
```

---

## 🐛 Troubleshooting

### Problema: Redis não inicia

```bash
# Ver erro detalhado
systemctl status redis-server -l

# Ver logs
journalctl -u redis-server -n 50

# Tentar iniciar manualmente
redis-server /etc/redis/redis.conf
```

### Problema: Aplicação não conecta ao Redis

```bash
# Verificar se Redis está escutando
netstat -tulpn | grep 6379

# Testar conexão
redis-cli ping

# Verificar .env
cat /root/screenshare2/.env | grep REDIS

# Testar Python
cd /root/screenshare2
python3 -c "from redis_manager import init_redis_manager; print(init_redis_manager().is_available())"
```

### Problema: Performance não melhorou

```bash
# Ver headers HTTP
curl -I https://screenshare.itfolkstech.com/serve_pil_image/curitiba/screen.png

# Procure por: X-Frame-Source: redis
# Se vier "disk", Redis não está sendo usado

# Ver logs
tail -f /root/screenshare2/app.log | grep serve_pil_image
```

### Problema: Memória Redis cheia

```bash
# Ver uso de memória
redis-cli info memory | grep used_memory_human

# Limpar manualmente se necessário
redis-cli FLUSHDB

# Ou limpar tudo
redis-cli FLUSHALL
```

---

## 📊 Comandos de Administração

### Gerenciar Serviço Redis

```bash
# Iniciar
sudo systemctl start redis-server

# Parar
sudo systemctl stop redis-server

# Reiniciar
sudo systemctl restart redis-server

# Status
sudo systemctl status redis-server

# Desabilitar boot automático
sudo systemctl disable redis-server

# Habilitar boot automático
sudo systemctl enable redis-server
```

### Backup Redis (Opcional)

```bash
# Redis faz backup automático, mas pode forçar:
redis-cli SAVE

# Arquivo de backup fica em:
ls -lh /var/lib/redis/dump.rdb
```

### Limpar Dados Redis

```bash
# Limpar apenas fila de uma localidade
redis-cli DEL "queue:curitiba:frames"

# Limpar frame de uma localidade
redis-cli DEL "frame:curitiba:current"

# Limpar tudo de uma localidade
redis-cli KEYS "frame:curitiba:*" | xargs redis-cli DEL
redis-cli KEYS "queue:curitiba:*" | xargs redis-cli DEL

# Limpar TUDO (cuidado!)
redis-cli FLUSHDB
```

---

## 🎯 Checklist Final de Validação

Antes de considerar o deploy completo:

- [ ] Redis instalado: `systemctl status redis-server`
- [ ] Redis respondendo: `redis-cli ping`
- [ ] Código atualizado: `git pull` sem erros
- [ ] Dependências instaladas: `pip list | grep redis`
- [ ] .env configurado: `grep REDIS_ENABLED .env`
- [ ] Aplicação iniciou: logs mostram "Redis conectado"
- [ ] Upload funciona: logs mostram "Frame salvo no Redis"
- [ ] Download funciona: logs mostram "Frame servido do Redis"
- [ ] Header correto: `X-Frame-Source: redis`
- [ ] Stats funcionam: `/admin/redis/stats` retorna dados
- [ ] Parar transmissão limpa Redis: logs mostram "Redis limpo"
- [ ] Performance melhorou: transmissão mais fluida

---

## 🔄 Rollback (Se necessário)

Se algo der errado e precisar voltar:

```bash
# Parar Redis
sudo systemctl stop redis-server
sudo systemctl disable redis-server

# Restaurar .env anterior
cd /root/screenshare2
cp .env.backup.XXXXXXXX .env

# Voltar código anterior
git reset --hard HEAD~1

# Reiniciar aplicação
tmux attach -t novo_screenshare
# Ctrl+C e depois:
python app.py
```

---

## 📈 Próximos Passos

Após deploy bem-sucedido:

1. **Monitorar por 24h** - verificar estabilidade
2. **Coletar métricas** - cache hit rate, performance
3. **Ajustar TTL** se necessário - padrão 30s
4. **Ajustar tamanho da fila** - padrão 100 frames
5. **Configurar alertas** (opcional) - Prometheus, Grafana
6. **Backup periódico** (opcional) - script de backup Redis

---

## 📞 Suporte

Se encontrar problemas:

1. **Logs da aplicação:** `tail -f /root/screenshare2/app.log`
2. **Logs do Redis:** `journalctl -u redis-server -f`
3. **Testar conexão:** `redis-cli ping`
4. **Ver stats:** `curl https://screenshare.itfolkstech.com/admin/redis/stats`

**Lembre-se:** O sistema funciona em modo fallback (disco) se Redis falhar!

---

## 🎉 Conclusão

Com este guia você:
- ✅ Instalou Redis no servidor
- ✅ Atualizou o código
- ✅ Configurou tudo corretamente
- ✅ Validou o funcionamento
- ✅ Sistema em produção com performance otimizada!

**Boa sorte com o deploy! 🚀**
