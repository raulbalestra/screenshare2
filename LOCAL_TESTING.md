# 🧪 Guia de Teste Local

## ✅ Configuração Aplicada

O arquivo `.env` foi configurado para **ambiente de desenvolvimento local**.

### 🔧 Mudanças Principais:

| Configuração | Produção | Local (Agora) |
|--------------|----------|---------------|
| `BASE_URL` | https://screenshare.itfolkstech.com | http://localhost:5000 |
| `ALLOWED_ORIGINS` | https://... | http://localhost:5000 |
| `SESSION_COOKIE_SECURE` | True (HTTPS) | **False** (HTTP) |
| `DEBUG` | False | **True** |
| `FLASK_ENV` | production | **development** |
| `RATE_LIMIT_ENABLED` | True | **False** |
| `UPLOAD_FOLDER` | /opt/screenshare/uploads | uploads |

## 🚀 Como Testar Localmente

### 1. Iniciar o Servidor

```bash
cd screenshare2
python app.py
```

Você verá:
```
* Running on http://127.0.0.1:5000
```

### 2. Acessar a Aplicação

**Login:**
- URL: http://localhost:5000
- Usuário: `admin`
- Senha: `admin123`

**Dashboard Admin:**
- URL: http://localhost:5000/dashboard_admin

**Compartilhar Tela (Curitiba):**
- URL: http://localhost:5000/curitiba/tela-compartilhada
- Clique em "Iniciar Compartilhamento"

**Visualizar Tela (Público):**
- URL: http://localhost:5000/curitiba/tela
- Verá a transmissão ao vivo

### 3. Testar Funcionalidades

#### ✅ Teste 1: Login
```
1. Acesse http://localhost:5000
2. Faça login com admin/admin123
3. Deve redirecionar para dashboard
```

#### ✅ Teste 2: Compartilhamento de Tela
```
1. Acesse http://localhost:5000/curitiba/tela-compartilhada
2. Clique "Iniciar Compartilhamento"
3. Permita compartilhamento de tela
4. Deve começar a transmitir
```

#### ✅ Teste 3: Visualização
```
1. Em outra aba, acesse http://localhost:5000/curitiba/tela
2. Deve ver a tela sendo transmitida
3. Teste pausar/retomar transmissão
4. Última imagem deve permanecer visível
```

#### ✅ Teste 4: Dashboard Admin
```
1. Acesse http://localhost:5000/dashboard_admin
2. Deve ver lista de usuários
3. Estatísticas devem aparecer (pode demorar alguns segundos)
```

## 🐛 Troubleshooting

### Erro: "Acesso não autorizado" no Dashboard

**Verificar logs:**
```python
# Procure por:
Dashboard API - Sessão: logged_in=True, is_admin=True
```

Se `is_admin=False`, o usuário não é admin.

### Erro: "Arquivo de imagem não encontrado"

**Normal!** Isso acontece quando:
- Nenhuma transmissão foi iniciada ainda
- A página `/tela` mostra mensagem: "Aguardando transmissão"

**Solução:**
1. Acesse `/curitiba/tela-compartilhada`
2. Inicie o compartilhamento

### Erro: "Rate limit exceeded"

Se isso acontecer (não deveria em modo dev):
```bash
# Edite .env
RATE_LIMIT_ENABLED=False
```

### Erro de Conexão com Banco de Dados

```bash
# Verifique se o PostgreSQL está acessível
psql -h 31.97.156.167 -U postgres -d screenshare
```

Se não conectar:
- Verifique firewall
- Confirme senha: `101410`

## 📁 Estrutura de Arquivos

```
screenshare2/
├── app.py                    # Aplicação principal
├── .env                      # Configurações LOCAL (atual)
├── .env.production          # Configurações PRODUÇÃO (backup)
├── templates/
│   ├── tela.html           # Página de visualização (atualizada)
│   └── tela_compartilhada.html
├── static/
│   └── images/
│       └── curitiba/       # Frames salvos aqui
│           └── screen.png
└── uploads/                 # Diretório de uploads
```

## 🔄 Voltar para Produção

Quando terminar os testes e quiser fazer deploy:

```bash
# Copie as configurações de produção
cp .env.production .env

# Ou edite manualmente:
nano .env
```

Altere:
```env
BASE_URL=https://screenshare.itfolkstech.com
ALLOWED_ORIGINS=https://screenshare.itfolkstech.com
SESSION_COOKIE_SECURE=True
DEBUG=False
FLASK_ENV=production
RATE_LIMIT_ENABLED=True
```

## 📝 Checklist de Teste

- [ ] Servidor iniciou sem erros
- [ ] Login funciona (admin/admin123)
- [ ] Dashboard carrega
- [ ] Tela compartilhada inicia
- [ ] Visualização mostra transmissão
- [ ] Pausar/retomar funciona
- [ ] Última imagem permanece ao pausar
- [ ] Indicador "Pausado" aparece
- [ ] Sem erros no console (F12)

## 💡 Dicas

1. **Console do Navegador (F12)**
   - Veja logs em tempo real
   - Erros de JavaScript aparecem aqui

2. **Terminal do Python**
   - Veja logs do Flask
   - Erros de backend aparecem aqui

3. **Múltiplas Abas**
   - Abra transmissão em uma aba
   - Visualização em outra aba
   - Simula uso real

4. **Diferentes Localidades**
   - Teste: `/curitiba/tela`
   - Teste: `/sp/tela`
   - Teste: `/londrina/tela`

---

**Status**: Configurado para desenvolvimento local ✅
**Banco**: Remoto (31.97.156.167) ✅
**HTTPS**: Desabilitado (HTTP local) ✅
