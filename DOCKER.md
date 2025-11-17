# ScreenShare Docker - Guia de Uso

## 📦 Arquivos Docker

- **`Dockerfile`** - Build all-in-one com API + PostgreSQL + MediaMTX
- **`docker-compose.yml`** - Configuração do container
- **`docker.sh`** - Script para Linux/Mac
- **`docker.bat`** - Script para Windows
- **`.dockerignore`** - Otimização de build

## 🚀 Como usar

### Windows

```bash
cd backend/screenshare2
docker.bat start      # Inicia o container
docker.bat logs       # Ver logs
docker.bat stop       # Para o container
```

### Linux/Mac

```bash
cd backend/screenshare2
chmod +x docker.sh
./docker.sh start     # Inicia o container
./docker.sh logs      # Ver logs
./docker.sh stop      # Para o container
```

## 📋 Comandos disponíveis

| Comando | Descrição |
|---------|-----------|
| `start` | Inicia o container |
| `stop` | Para o container |
| `build` | Faz build da imagem |
| `logs` | Mostra logs em tempo real |
| `shell` | Abre bash no container |
| `restart` | Reinicia o container |

## 🌐 Endpoints

Após iniciar, os serviços estarão disponíveis em:

- **API**: http://localhost:8000
- **HLS**: http://localhost:8888
- **WHIP**: http://localhost:8889
- **MediaMTX API**: http://localhost:9997
- **PostgreSQL**: localhost:5432

## 📊 Estrutura do Container

Um único container rodando:
- ✅ Python + FastAPI (porta 8000)
- ✅ PostgreSQL (porta 5432)
- ✅ MediaMTX (portas 8888, 8889, 9997)
- ✅ Supervisor (gerencia todos os processos)

## 🔧 Variáveis de ambiente

Editáveis no `docker-compose.yml`:

```yaml
environment:
  DATABASE_URL: postgresql://...
  SECRET_KEY: your-secret-key
  DEBUG: 'false'
  ALLOWED_ORIGINS: "*"
```

## 📝 Volumes

- `./logs` - Logs da aplicação
- `./data` - Dados do PostgreSQL

## ✅ Health Check

O container tem health check automático que verifica:
```bash
curl http://localhost:8000/api/health
```

## 🐛 Troubleshooting

**Container não inicia:**
```bash
docker.sh logs  # Ver detalhes do erro
```

**Porta já em uso:**
```bash
# Mudar porta no docker-compose.yml
ports:
  - "8001:8000"  # Mudar primeira porta
```

**Limpar tudo:**
```bash
docker-compose down -v  # Remove containers, networks e volumes
```

## 📦 Build da imagem

```bash
docker.sh build  # Faz rebuild da imagem
```

## 🚀 Deploy na VPS

1. Copiar pasta `backend/screenshare2` para VPS
2. Executar: `docker-compose up -d`
3. Acessar: `http://vps-ip:8000`

## 📞 Suporte

Para mais informações, consulte:
- `DEPLOY_VPS.md` - Guia completo de deploy
- `README.md` - Documentação geral do projeto
