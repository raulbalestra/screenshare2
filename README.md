
# Screen Sharing App

Este é um aplicativo Flask que permite o login de usuários, troca de senha e compartilhamento de tela. O projeto utiliza um banco de dados SQLite para armazenar informações de login e senha, e fornece uma interface simples para os usuários interagirem.

## Estrutura do Projeto

Screen_Sharing/ │ ├── app.py # Arquivo principal do Flask com todas as rotas e lógica ├── create_db.py # Script para criar e popular o banco de dados ├── users.db # Arquivo de banco de dados SQLite (gerado após executar create_db.py) ├── templates/ # Diretório para armazenar arquivos HTML │ ├── login.html # Página de login │ ├── change_password.html # Página de troca de senha │ └── share_screen.html # Página de compartilhamento de tela └── static/ # Diretório para arquivos estáticos (CSS, imagens, etc.) └── styles.css # Arquivo CSS para estilos adicionais (opcional)

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
