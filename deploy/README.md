# 📦 Deploy Scripts - ScreenShare

Scripts e guias para deploy da aplicação ScreenShare no servidor de produção.

## 📄 Arquivos

### Scripts

- **`package.bat`** - Script Windows para empacotar arquivos para deploy
- **`deploy.sh`** - Script Linux para instalação e configuração automática no servidor

### Documentação

- **`QUICK_START.md`** - Guia rápido de deploy (recomendado para começar)
- **`../DEPLOY_GUIDE.md`** - Guia completo e detalhado de deploy

## 🚀 Como Usar

### 1. Empacotar (Windows)

Execute na raiz do projeto:

```cmd
deploy\package.bat
```

Isso criará um arquivo `.tar.gz` com todos os arquivos necessários.

### 2. Transferir para Servidor

Use MobaXterm, WinSCP ou scp para transferir o arquivo:

```bash
scp screenshare_deploy_*.tar.gz root@31.97.156.167:/opt/
```

### 3. Deploy no Servidor

```bash
ssh root@31.97.156.167

mkdir -p /opt/screenshare
tar -xzf /opt/screenshare_deploy_*.tar.gz -C /opt/screenshare/
cd /opt/screenshare
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

### 4. Configurar e Iniciar

Siga as instruções do script para:
- Configurar senhas no `.env`
- Alterar senha do PostgreSQL
- Alterar senha do admin na aplicação

## 📚 Documentação

Para informações detalhadas, consulte:

- **Início Rápido**: `QUICK_START.md`
- **Guia Completo**: `../DEPLOY_GUIDE.md`

## 🔗 Links Úteis

- **Aplicação**: https://screenshare.itfolkstech.com
- **Servidor**: 31.97.156.167
- **SSL**: Let's Encrypt (expira 03/03/2026)

## ⚙️ Requisitos do Servidor

- Ubuntu 24.04 LTS (ou similar)
- Python 3.10+
- PostgreSQL 14+
- Nginx
- Certbot (Let's Encrypt)
- FFmpeg

## 🛠️ O que o deploy.sh faz

1. ✅ Cria backup da instalação anterior
2. ✅ Cria estrutura de diretórios
3. ✅ Instala dependências do sistema
4. ✅ Configura ambiente virtual Python
5. ✅ Instala pacotes Python
6. ✅ Configura PostgreSQL
7. ✅ Cria arquivo .env
8. ✅ Configura serviço systemd
9. ✅ Configura firewall (UFW)
10. ✅ Cria script de backup automático
11. ✅ Ajusta permissões
12. ✅ Inicia serviços

## 📝 Notas

- Sempre faça backup antes de atualizar
- Altere todas as senhas padrão após o deploy
- Monitore os logs após cada deploy
- Teste a aplicação em ambiente de staging primeiro (se disponível)

---

**Data**: 03/12/2025
**Versão**: 1.0
