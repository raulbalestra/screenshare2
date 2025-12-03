# Correções Necessárias para Produção

## ⚠️ Problemas Identificados nos Logs

### 1. Sessão Inválida para Usuário 2
**Sintoma:**
```
Sessão inválida detectada para usuário 2
```

**Causa:** 
- Verificação de sessão nas linhas 115-135 do `app.py` está forçando validação em rotas que deveriam ser públicas
- `serve_pil_image` e `tela` estão marcadas como `protected_routes` mas precisam acesso público

**Solução:**
```python
# No app.py, linha 117-120, REMOVER estas rotas:
protected_routes = [
    'upload_frame',  # MANTER - precisa auth
    # 'serve_pil_image',  # REMOVER - precisa ser pública para visualização
    # 'tela',  # REMOVER - precisa ser pública para visualização
    'tela_compartilhada',  # MANTER - precisa auth
    'hls_ingest', 'hls_start', 'hls_stop', 'hls_status'
]
```

### 2. Diretório de Imagens Incorreto
**Sintoma:**
```
Arquivo de imagem não encontrado no caminho: /root/screenshare2/static/images/curitiba/screen.png
```

**Causa:**
- O diretório `/root/screenshare2/static/images/curitiba` não existe
- A criação automática só funciona para diretórios na linha 98, mas não cria subdiretórios por localidade

**Solução:**
A função `ensure_localidade_directory` (linha 826) já existe, mas precisa ser chamada antes de servir imagens.

### 3. Acesso Não Autorizado em Upload
**Sintoma:**
```
Acesso não autorizado para upload_frame - localidade: curitiba, IP: 201.15.48.212
```

**Causa:**
- Usuário tentando fazer upload sem estar logado corretamente
- Sessão foi perdida/expirou

**Solução:** Isso é comportamento correto - usuário precisa fazer login em `/` primeiro.

---

## 🔧 Correções Imediatas Necessárias

### Correção 1: Liberar Rotas de Visualização

**Arquivo:** `app.py` (linhas 117-120)

**Antes:**
```python
protected_routes = [
    'upload_frame', 'serve_pil_image', 'tela', 'tela_compartilhada',
    'hls_ingest', 'hls_start', 'hls_stop', 'hls_status'
]
```

**Depois:**
```python
protected_routes = [
    'upload_frame', 'tela_compartilhada',
    'hls_ingest', 'hls_start', 'hls_stop', 'hls_status'
]
# Nota: 'tela' e 'serve_pil_image' DEVEM ser públicas para permitir visualização
```

### Correção 2: Criar Diretórios de Localidade

**Arquivo:** `app.py` (adicionar após linha 105)

**Adicionar:**
```python
# Criar diretórios para localidades conhecidas
for localidade in ['curitiba', 'saopaulo', 'riodejaneiro']:
    localidade_dir = os.path.join(IMAGE_DIR, localidade.lower())
    if not os.path.exists(localidade_dir):
        os.makedirs(localidade_dir)
        print(f"[INIT] Diretório criado: {localidade_dir}")
```

### Correção 3: Verificar Sessão no Upload

**Arquivo:** `app.py` (linha ~1450-1460 na rota upload_frame)

Verificar se o código tem:
```python
@app.route("/<localidade>/upload_frame", methods=["POST"])
def upload_frame(localidade):
    """Upload de frame via POST"""
    
    # Verificar autenticação
    if not is_user_logged_in():
        security_logger.warning(f"Acesso não autorizado para upload_frame - localidade: {localidade}, IP: {get_client_ip()}")
        return redirect(url_for('index'))
```

Isso está correto - mantenha como está.

---

## 📋 Checklist de Deploy

Antes de reiniciar a aplicação:

- [ ] Editar `app.py` linha 117-120: remover `'serve_pil_image'` e `'tela'` de `protected_routes`
- [ ] Adicionar criação de diretórios de localidades após linha 105
- [ ] Verificar que `.env` tem configurações corretas de produção
- [ ] Criar diretórios manualmente se necessário:
  ```bash
  mkdir -p /root/screenshare2/static/images/curitiba
  mkdir -p /root/screenshare2/static/images/saopaulo
  mkdir -p /opt/screenshare/uploads
  mkdir -p /opt/screenshare/sessions
  ```
- [ ] Reiniciar aplicação: `systemctl restart screenshare` ou `python app.py`
- [ ] Fazer login em `https://screenshare.itfolkstech.com`
- [ ] Acessar `/curitiba/tela-compartilhada` e iniciar transmissão
- [ ] Verificar `/curitiba/tela` está mostrando frames

---

## 🚀 Comandos para Aplicar Correções

**No servidor (via SSH):**

```bash
# 1. Criar diretórios necessários
cd /root/screenshare2
mkdir -p static/images/curitiba
mkdir -p static/images/saopaulo
mkdir -p /opt/screenshare/uploads
mkdir -p /opt/screenshare/sessions

# 2. Fazer backup do app.py
cp app.py app.py.backup

# 3. Editar app.py (use nano ou vi)
nano app.py
# Faça as correções nas linhas 117-120 e após linha 105

# 4. Reiniciar aplicação
# Se usando systemd:
sudo systemctl restart screenshare

# OU se rodando diretamente:
pkill -f "python app.py"
python app.py
```

---

## 🔍 Validação Pós-Deploy

Após aplicar correções, verificar logs:

```bash
# Ver logs em tempo real
tail -f /var/log/screenshare/app.log

# OU se rodando diretamente:
# Observe a saída do terminal
```

**Comportamento esperado:**
- ✅ `GET /curitiba/tela HTTP/1.1" 200` - página carrega sem redirect
- ✅ `GET /serve_pil_image/curitiba/screen.png` - imagem carrega (pode ser 404 se sem transmissão, mas não 302)
- ✅ `POST /curitiba/upload_frame HTTP/1.1" 302` - redirect para login se não autenticado (correto)
- ❌ NÃO deve aparecer: `"Sessão inválida detectada"` ao acessar `/tela`

---

## 📝 Notas Importantes

1. **Segurança**: As rotas de visualização (`/tela` e `/serve_pil_image`) DEVEM ser públicas para permitir que múltiplos usuários vejam a transmissão sem login.

2. **Upload**: A rota `/upload_frame` DEVE permanecer protegida - apenas usuários autenticados podem transmitir.

3. **Diretórios**: O sistema cria automaticamente os diretórios principais, mas precisa criar subdiretórios por localidade.

4. **Sessões**: Usuários podem ter apenas 1 sessão ativa. Login em novo dispositivo invalida sessão anterior.
