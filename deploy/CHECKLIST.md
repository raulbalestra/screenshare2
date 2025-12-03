# ✅ Checklist de Deploy - ScreenShare

## 📋 Pré-Deploy

### Servidor
- [ ] Acesso SSH configurado (root@31.97.156.167)
- [ ] Ubuntu 24.04 LTS instalado
- [ ] Domínio configurado (screenshare.itfolkstech.com)
- [ ] DNS apontando para 31.97.156.167

### Local (Windows)
- [ ] Código atualizado e testado
- [ ] Arquivo `.env` configurado
- [ ] Dependências listadas em `requirements.txt`
- [ ] Scripts de deploy preparados

---

## 🚀 Processo de Deploy

### 1. Empacotar Aplicação
- [ ] Executar `deploy\package.bat`
- [ ] Verificar criação do arquivo `.tar.gz`
- [ ] Arquivo contém todos os arquivos necessários

### 2. Transferir para Servidor
- [ ] Arquivo transferido para `/opt/` via SCP ou MobaXterm
- [ ] Permissões de leitura corretas

### 3. Preparar Servidor
```bash
# No servidor
- [ ] Conectado via SSH
- [ ] Diretório `/opt/screenshare` criado
- [ ] Arquivo extraído em `/opt/screenshare/`
- [ ] Script de deploy com permissão de execução
```

### 4. Executar Deploy Automatizado
```bash
cd /opt/screenshare
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

- [ ] Script executado sem erros
- [ ] Todas as dependências instaladas
- [ ] Banco de dados criado
- [ ] Serviço systemd configurado
- [ ] Nginx configurado
- [ ] Firewall configurado

---

## 🔐 Configurações de Segurança

### PostgreSQL
- [ ] Banco de dados `screenshare` criado
- [ ] Usuário `screenshare_user` criado
- [ ] Senha forte configurada
- [ ] Permissões corretas concedidas
- [ ] Conexão testada

```sql
-- Verificar usuário
SELECT usename FROM pg_user WHERE usename = 'screenshare_user';

-- Verificar banco
\l screenshare
```

### Arquivo .env
- [ ] Arquivo `.env` em `/opt/screenshare/`
- [ ] Permissões 600 (`chmod 600 .env`)
- [ ] `SECRET_KEY` gerada (única e segura)
- [ ] `DB_PASSWORD` atualizada
- [ ] `BASE_URL` correto (https://screenshare.itfolkstech.com)
- [ ] Todas as variáveis configuradas

```bash
# Gerar nova SECRET_KEY
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### Firewall (UFW)
- [ ] UFW habilitado
- [ ] Porta 22 (SSH) aberta
- [ ] Porta 80 (HTTP) aberta
- [ ] Porta 443 (HTTPS) aberta
- [ ] Porta 5432 (PostgreSQL) fechada externamente

```bash
sudo ufw status
```

---

## 🌐 Nginx e SSL

### Nginx
- [ ] Arquivo de configuração em `/etc/nginx/sites-available/`
- [ ] Link simbólico criado em `/etc/nginx/sites-enabled/`
- [ ] Configuração testada (`nginx -t`)
- [ ] Nginx recarregado (`systemctl reload nginx`)
- [ ] Proxy reverso funcionando (porta 5000)

### SSL/HTTPS
- [ ] Certbot instalado
- [ ] Certificado Let's Encrypt obtido
- [ ] Certificado instalado no Nginx
- [ ] Redirecionamento HTTP→HTTPS funcionando
- [ ] Certificado válido até 03/03/2026
- [ ] Renovação automática configurada

```bash
certbot certificates
certbot renew --dry-run
```

---

## 🖥️ Serviços

### Systemd Service
- [ ] Arquivo `/etc/systemd/system/screenshare.service` criado
- [ ] Daemon recarregado (`systemctl daemon-reload`)
- [ ] Serviço habilitado (`systemctl enable screenshare`)
- [ ] Serviço iniciado (`systemctl start screenshare`)
- [ ] Serviço rodando sem erros

```bash
systemctl status screenshare
journalctl -u screenshare -f
```

### Processos
- [ ] Gunicorn rodando com 4 workers
- [ ] Aplicação ouvindo em 127.0.0.1:5000
- [ ] Nginx ouvindo em 0.0.0.0:80 e 443
- [ ] PostgreSQL rodando

```bash
ps aux | grep gunicorn
netstat -tulpn | grep 5000
```

---

## 📊 Logs e Monitoramento

### Configuração de Logs
- [ ] Diretório `/var/log/screenshare/` criado
- [ ] Arquivo `access.log` criado
- [ ] Arquivo `error.log` criado
- [ ] Permissões corretas nos logs

### Verificação de Logs
- [ ] Logs sem erros críticos
- [ ] Aplicação iniciando corretamente
- [ ] Conexão com banco de dados OK

```bash
tail -f /var/log/screenshare/error.log
tail -f /var/log/screenshare/access.log
```

---

## 💾 Backup

### Configuração de Backup
- [ ] Script de backup em `/opt/screenshare/backup.sh`
- [ ] Permissão de execução (`chmod +x backup.sh`)
- [ ] Diretório de backup `/opt/backups/screenshare/` criado
- [ ] Crontab configurado (diário às 2h)
- [ ] Backup manual testado

```bash
./backup.sh
ls -lh /opt/backups/screenshare/
```

---

## 🧪 Testes de Funcionalidade

### Acesso à Aplicação
- [ ] URL acessível: https://screenshare.itfolkstech.com
- [ ] Certificado SSL válido (cadeado verde)
- [ ] Página de login carrega
- [ ] Assets estáticos carregam (CSS, JS)

### Login e Autenticação
- [ ] Login com admin/admin123 funciona
- [ ] Redirecionamento para dashboard
- [ ] Senha do admin alterada
- [ ] Novo login com senha nova funciona

### Funcionalidades Principais
- [ ] Dashboard carrega sem erros
- [ ] Listagem de usuários funciona
- [ ] Criação de novo usuário funciona
- [ ] Compartilhamento de tela funciona
- [ ] WebSocket conecta corretamente
- [ ] Upload de frames funciona
- [ ] Visualização de tela compartilhada funciona

### Performance
- [ ] Página carrega em < 3 segundos
- [ ] WebSocket mantém conexão estável
- [ ] Sem erros no console do navegador
- [ ] Uso de CPU < 50% em idle
- [ ] Uso de memória < 1GB em idle

---

## 🔍 Verificações Finais

### Status dos Serviços
```bash
- [ ] systemctl status screenshare     # ✓ active (running)
- [ ] systemctl status nginx           # ✓ active (running)
- [ ] systemctl status postgresql      # ✓ active (running)
```

### Conectividade
```bash
- [ ] curl http://127.0.0.1:5000       # ✓ Responde
- [ ] curl https://screenshare.itfolkstech.com  # ✓ Responde
```

### Banco de Dados
```bash
- [ ] Tabelas criadas (users, usage_events)
- [ ] Usuário admin existe
- [ ] Índices criados
- [ ] Views criadas (user_usage_summary)
```

### Segurança
- [ ] Senhas padrão alteradas
- [ ] Firewall ativo e configurado
- [ ] SSL/HTTPS funcionando
- [ ] Headers de segurança configurados
- [ ] Rate limiting ativo
- [ ] CSRF protection ativa

---

## 📱 Credenciais Finais

### Aplicação
- URL: https://screenshare.itfolkstech.com
- Usuário Admin: `admin`
- Senha: [ALTERADA - anote em local seguro]

### Banco de Dados
- Host: localhost (31.97.156.167)
- Database: `screenshare`
- Usuário: `postgres` (ou `screenshare_user`)
- Senha: [anote em local seguro]

### Servidor SSH
- Host: 31.97.156.167
- Usuário: root
- Porta: 22

---

## 📞 Pós-Deploy

### Comunicação
- [ ] Equipe notificada sobre deploy
- [ ] URL compartilhada com stakeholders
- [ ] Credenciais enviadas de forma segura
- [ ] Documentação atualizada

### Monitoramento (Primeiras 24h)
- [ ] Verificar logs a cada 2 horas
- [ ] Monitorar uso de recursos (CPU, RAM, Disco)
- [ ] Verificar logs de erro
- [ ] Testar funcionalidades críticas
- [ ] Verificar performance de resposta

### Documentação
- [ ] Checklist de deploy preenchido
- [ ] Senhas documentadas em local seguro
- [ ] Procedimentos de rollback documentados
- [ ] Contatos de emergência atualizados

---

## 🆘 Rollback (se necessário)

Em caso de problemas:

```bash
# 1. Parar serviço
systemctl stop screenshare

# 2. Restaurar backup
cd /opt
mv screenshare screenshare_failed
tar -xzf /opt/backups/screenshare/app_backup_YYYYMMDD_HHMMSS.tar.gz

# 3. Restaurar banco de dados
psql -U screenshare_user screenshare < /opt/backups/screenshare/db_YYYYMMDD_HHMMSS.sql

# 4. Reiniciar serviço
systemctl start screenshare
```

---

## ✅ Deploy Concluído

Data: ___/___/______
Responsável: _________________
Versão: _________________

**Observações:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

**Próxima Revisão**: 1 semana após deploy
**Renovação SSL**: 03/03/2026
