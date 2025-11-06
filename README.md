
# ScreenShare HLS - Sistema Completo de Transmissão

Sistema profissional de compartilhamento de tela com streaming HLS, separação por estados e autenticação JWT.

## 🚀 Características

- **Frontend**: HTML5 + Bootstrap 5 (sem frameworks complexos)
- **Backend**: FastAPI com autenticação JWT
- **Streaming**: MediaMTX com WHIP ingest + LL-HLS output
- **Separação**: Cada estado tem suas próprias sessões isoladas
- **Baixa Latência**: LL-HLS com segmentos de 1s e partes de 200ms
- **Banco**: SQLite para simplicidade
- **QR Code**: Geração automática para acesso móvel

## 📋 Requisitos

- Python 3.11+
- MediaMTX (baixado automaticamente)
- Navegador moderno com suporte a WebRTC/getDisplayMedia
- Ubuntu 20.04+ (para produção)

## 🛠️ Instalação Local (Desenvolvimento)

### 1. Configurar Ambiente
```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar Variáveis (.env)
```bash
cat > .env << EOF
APP_HOST=localhost
APP_PORT=8000
DEBUG=True
JWT_SECRET_KEY=sua_chave_jwt_super_secreta_aqui
MEDIAMTX_HOST=localhost
MEDIAMTX_WHIP_PORT=8889
MEDIAMTX_HLS_PORT=8888
ALLOWED_STATES=SP,RJ,MG,PR,SC,RS,BA,PE,CE,GO
DATABASE_PATH=sessions.db
EOF
```

### 3. Iniciar Sistema
```bash
# Dar permissão aos scripts
chmod +x scripts/*.sh

# Iniciar em modo desenvolvimento
./scripts/start.sh dev
```

### 4. Acessar Sistema
- **Interface Web**: http://localhost:8000
- **Transmitir**: http://localhost:8000/publish
- **Assistir**: http://localhost:8000/play/{session_id}

## 🌐 Instalação VPS (Produção)

### Instalação Automática Ubuntu
```bash
# Download e execução do script
curl -sSL https://raw.githubusercontent.com/seu-repo/screenshare2/main/scripts/install.sh | bash
```

## 📡 Como Usar

### 1. Criar Sessão de Transmissão
1. Acesse `/publish`
2. Selecione o estado (SP, RJ, MG, etc.)
3. Digite seu nome
4. Clique "Criar Sessão"
5. Clique "Iniciar Captura" e selecione a tela
6. Compartilhe o link ou QR Code gerado

### 2. Assistir Transmissão
1. Acesse o link `/play/{session_id}` 
2. Ou use o QR Code no celular
3. O vídeo iniciará automaticamente

### 3. Estados e Isolamento
- Cada estado (SP, RJ, MG...) tem streams independentes
- URLs seguem padrão: `/hls/{estado}/{session_id}/index.m3u8`
- Não há conflito entre sessões de estados diferentes

## 📊 API Endpoints

### Sessões
- `POST /api/session/create` - Criar sessão
- `GET /api/session/{id}/play` - Info para reprodução
- `GET /api/health` - Health check

### Streaming
- `POST /whip/{estado}/{session_id}` - WHIP ingest
- `GET /hls/{estado}/{session_id}/index.m3u8` - HLS playlist

## 🔒 Segurança

### JWT Tokens
- **Publish Token**: Permite transmitir na sessão
- **Play Token**: Permite assistir a sessão
- Expiração configurável (24h padrão)

## 🐛 Troubleshooting

### 1. MediaMTX não inicia
```bash
# Verificar logs
sudo journalctl -u mediamtx -f

# Reiniciar
sudo systemctl restart mediamtx
```

### 2. Captura de tela não funciona
- Verificar se está usando HTTPS (necessário para getDisplayMedia)
- Testar em navegadores diferentes
- Verificar permissões do navegador

### 3. HLS não carrega
```bash
# Testar URL diretamente
curl http://localhost:8888/hls/SP/test-session/index.m3u8
```

bash
Copiar código

## Pré-requisitos

Antes de rodar o projeto, certifique-se de ter instalado:

- Python 3.x
- Virtualenv (opcional, mas recomendado)
- Flask e dependências do Python

## Configuração do Ambiente

### 1. Clone o Repositório

```bash
git clone https://github.com/seu_usuario/screen-sharing-app.git
cd screen-sharing-app
2. Crie um Ambiente Virtual (Opcional, mas Recomendado)
bash
Copiar código
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
.venv\Scripts\activate       # Windows
3. Instale as Dependências
Instale os pacotes necessários usando o pip:

bash
Copiar código
pip install flask
4. Crie o Banco de Dados
Execute o script para criar e popular o banco de dados SQLite:

bash
Copiar código
python create_db.py
5. Execute a Aplicação
Depois de configurar o ambiente e o banco de dados, execute o aplicativo Flask:

bash
Copiar código
python app.py
Acesse a aplicação no navegador no endereço http://127.0.0.1:5000.

Funcionalidades

Login de Usuário: Os usuários podem fazer login com seu nome de usuário e senha.
Troca de Senha: Os usuários podem redefinir suas senhas na página de troca de senha.
Compartilhamento de Tela: Após o login, os usuários podem acessar a página de compartilhamento de tela.
Estrutura do Banco de Dados

O banco de dados SQLite users.db contém uma tabela users com as seguintes colunas:

id: Chave primária (autoincremento)
username: Nome de usuário (único)
password: Senha do usuário
localidade: Localidade do usuário
Contribuição

Se você quiser contribuir para o projeto, faça um fork do repositório, crie uma nova branch, e faça um pull request com suas mudanças.

Faça o fork do projeto.
Crie uma nova branch (git checkout -b nova-feature).
Commit suas mudanças (git commit -m 'Adiciona nova feature').
Envie para a branch (git push origin nova-feature).
Abra um pull request.
Licença

Este projeto está licenciado sob a MIT License - veja o arquivo LICENSE para mais detalhes.

markdown
Copiar código

### Explicação:

- **Estrutura do Projeto**: Descreve a organização dos arquivos no projeto.
- **Pré-requisitos**: Lista as ferramentas necessárias para rodar o projeto.
- **Configuração do Ambiente**: Passos detalhados para configurar o projeto, incluindo criação de ambiente virtual, instalação de dependências e inicialização do banco de dados.
- **Funcionalidades**: Descreve o que o projeto faz.
- **Estrutura do Banco de Dados**: Explica a estrutura da tabela `users` no banco de dados SQLite.
- **Contribuição**: Orienta como contribuir para o projeto.
- **Licença**: Informa sobre a licença usada no projeto.

Você pode modificar o conteúdo de ac
