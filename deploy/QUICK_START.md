# 🚀 Quick Start - Deploy ScreenShare

## 📋 Informações do Servidor

- **IP**: 31.97.156.167
- **Domínio**: https://screenshare.itfolkstech.com
- **OS**: Ubuntu 24.04.3 LTS
- **SSL**: Let's Encrypt (válido até 03/03/2026)

## ⚡ Deploy Rápido

### 1️⃣ No Windows (Local)

```bash
cd c:\Users\pf388\OneDrive\Documents\screenshare_novo\screenshare2
deploy\package.bat
```

Isso criará um arquivo `screenshare_deploy_YYYYMMDD_HHMMSS.tar.gz`

### 2️⃣ Transferir para o Servidor

**Opção A - Via MobaXterm:**
1. Conecte-se ao servidor via SSH no MobaXterm
2. Use o navegador de arquivos lateral para arrastar o arquivo .tar.gz para `/opt/`

**Opção B - Via SCP:**
```bash
scp screenshare_deploy_*.tar.gz root@31.97.156.167:/opt/
```

### 3️⃣ No Servidor

```bash
# Conectar ao servidor
ssh root@31.97.156.167

# Criar diretório e extrair
mkdir -p /opt/screenshare
cd /opt
tar -xzf screenshare_deploy_*.tar.gz -C /opt/screenshare/

# Executar deploy
cd /opt/screenshare
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

### 4️⃣ Configurar Senhas

```bash
# Editar .env e alterar as senhas
nano /opt/screenshare/.env
```

Altere:
- `DB_PASSWORD=` (senha do PostgreSQL)
- `SECRET_KEY=` (já gerado automaticamente)

### 5️⃣ Alterar Senha do PostgreSQL

```bash
sudo -u postgres psql
ALTER USER screenshare_user WITH PASSWORD 'SuaNovaSenhaSegura123!';
\q
```

Atualize a mesma senha no arquivo `.env`

### 6️⃣ Reiniciar e Testar

```bash
systemctl restart screenshare
systemctl status screenshare

# Ver logs
tail -f /var/log/screenshare/error.log
```

### 7️⃣ Acessar Aplicação

URL: https://screenshare.itfolkstech.com

**Login Inicial:**
- Usuário: `admin`
- Senha: `admin123`

⚠️ **IMPORTANTE**: Altere a senha imediatamente após o primeiro login!

## 🔍 Comandos Úteis

### Verificar Status
```bash
systemctl status screenshare    # Status da aplicação
systemctl status nginx          # Status do Nginx
systemctl status postgresql     # Status do PostgreSQL
```

### Ver Logs
```bash
# Logs da aplicação
tail -f /var/log/screenshare/error.log
tail -f /var/log/screenshare/access.log

# Logs do systemd
journalctl -u screenshare -f
```

### Reiniciar Serviços
```bash
systemctl restart screenshare
systemctl restart nginx
systemctl restart postgresql
```

### Monitorar Recursos
```bash
htop                    # CPU e Memória
df -h                   # Espaço em disco
du -sh /opt/screenshare # Tamanho da aplicação
```

### Backup Manual
```bash
/opt/screenshare/backup.sh
```

### Verificar Certificado SSL
```bash
certbot certificates
certbot renew --dry-run
```

## 🔧 Troubleshooting Rápido

### Aplicação não inicia
```bash
# Ver erro específico
journalctl -u screenshare -n 50

# Testar manualmente
cd /opt/screenshare
source venv/bin/activate
python app.py
```

### Erro 502 Bad Gateway
```bash
# Verificar se está rodando
netstat -tulpn | grep 5000

# Reiniciar
systemctl restart screenshare
```

### Erro de Conexão com Banco
```bash
# Verificar PostgreSQL
systemctl status postgresql

# Testar conexão
psql -U screenshare_user -d screenshare -h localhost
```

### Limpar Logs
```bash
# Truncar logs grandes
truncate -s 0 /var/log/screenshare/access.log
truncate -s 0 /var/log/screenshare/error.log
```

## 📁 Estrutura de Diretórios

```
/opt/screenshare/
├── app.py                  # Aplicação principal
├── security_utils.py       # Utilitários de segurança
├── requirements.txt        # Dependências Python
├── .env                    # Configurações (SENHAS!)
├── venv/                   # Ambiente virtual Python
├── templates/              # Templates HTML
├── static/                 # Arquivos estáticos
├── uploads/                # Uploads dos usuários
├── sql/                    # Scripts SQL
└── deploy/                 # Scripts de deploy

/var/log/screenshare/
├── access.log              # Log de acesso
└── error.log               # Log de erros

/etc/nginx/sites-available/
└── screenshare.itfolkstech.com  # Config Nginx

/etc/letsencrypt/live/screenshare.itfolkstech.com/
├── fullchain.pem           # Certificado SSL
└── privkey.pem             # Chave privada SSL
```

## 🔄 Atualização Rápida

```bash
# No Windows: Criar novo pacote
deploy\package.bat

# Transferir para servidor

# No servidor
cd /opt
systemctl stop screenshare
tar -xzf screenshare_deploy_*.tar.gz -C /opt/screenshare/
cd /opt/screenshare
source venv/bin/activate
pip install -r requirements.txt
systemctl start screenshare
tail -f /var/log/screenshare/error.log
```

## 📞 Checklist de Deploy

- [ ] Servidor acessível via SSH
- [ ] Arquivos transferidos para `/opt/screenshare`
- [ ] Script de deploy executado
- [ ] Senhas alteradas no `.env`
- [ ] Senha do PostgreSQL alterada
- [ ] Serviço screenshare rodando
- [ ] Nginx rodando
- [ ] SSL ativo e válido
- [ ] Aplicação acessível via HTTPS
- [ ] Senha do admin alterada
- [ ] Backup automático configurado
- [ ] Logs verificados sem erros

## 🎯 URLs Importantes

- **Aplicação**: https://screenshare.itfolkstech.com
- **Login Admin**: https://screenshare.itfolkstech.com/login
- **Dashboard**: https://screenshare.itfolkstech.com/dashboard_admin

---

**Última atualização**: 03/12/2025
**Versão**: 1.0
**Servidor**: 31.97.156.167
