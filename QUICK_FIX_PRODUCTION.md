# 🚀 Correção Rápida - Erro 404 na Transmissão (Produção)

## 🔴 Problema
```
Arquivo de imagem não encontrado no caminho: /root/screenshare2/static/images/curitiba/screen.png
```

## ✅ Solução Rápida

### Opção 1: Script Automático (Recomendado)

**No servidor (via SSH):**

```bash
# 1. Fazer upload do script
scp fix_production_dirs.sh root@31.97.156.167:/root/screenshare2/

# 2. Conectar ao servidor
ssh root@31.97.156.167

# 3. Executar script de correção
cd /root/screenshare2
chmod +x fix_production_dirs.sh
bash fix_production_dirs.sh

# 4. Reiniciar aplicação
systemctl restart screenshare
# OU se rodando diretamente:
pkill -f "python app.py"
python app.py
```

### Opção 2: Comandos Manuais

**Se preferir fazer manualmente, execute no servidor:**

```bash
# Conectar ao servidor
ssh root@31.97.156.167

# Ir para diretório do projeto
cd /root/screenshare2

# Criar diretórios necessários
mkdir -p static/images/curitiba
mkdir -p static/images/saopaulo
mkdir -p static/images/riodejaneiro
mkdir -p sessions
mkdir -p hls_streams
mkdir -p /opt/screenshare/uploads
mkdir -p /opt/screenshare/sessions

# Configurar permissões
chmod -R 755 static/images
chmod -R 755 sessions
chmod -R 755 /opt/screenshare/uploads

# Verificar estrutura
ls -la static/images/

# Reiniciar aplicação
systemctl restart screenshare
```

## 📋 Verificação Pós-Correção

Após reiniciar, teste:

1. **Acessar página de compartilhamento:**
   ```
   https://screenshare.itfolkstech.com/curitiba/tela-compartilhada
   ```

2. **Iniciar transmissão** - deve começar a enviar frames

3. **Abrir página de visualização** em outra aba/dispositivo:
   ```
   https://screenshare.itfolkstech.com/curitiba/tela
   ```

4. **Verificar logs:**
   ```bash
   tail -f /var/log/screenshare/app.log
   # OU se rodando diretamente, ver saída do terminal
   ```

## 🔍 Logs Esperados Após Correção

**✅ Sucesso:**
```
[INIT] Diretório criado: /root/screenshare2/static/images
[INIT] BASE_DIR: /root/screenshare2
[INIT] IMAGE_DIR: /root/screenshare2/static/images
POST /curitiba/upload_frame HTTP/1.1" 200
GET /serve_pil_image/curitiba/screen.png HTTP/1.1" 200
```

**❌ Se ainda tiver erro:**
```
Arquivo de imagem não encontrado no caminho: ...
```

Então verifique:
- Permissões dos diretórios: `ls -la static/images/curitiba/`
- Proprietário dos arquivos: `chown -R root:root static/`
- Se o processo pode escrever: `touch static/images/curitiba/test.txt && rm static/images/curitiba/test.txt`

## 🔧 Prevenção Futura

O código já foi atualizado para criar diretórios automaticamente quando necessário. Após aplicar as correções do `app.py` atualizado, novos diretórios de localidades serão criados dinamicamente.

## 📝 Notas Importantes

1. **Localidades dinâmicas**: Após a correção, qualquer nova localidade terá seu diretório criado automaticamente
2. **Backup antes de reiniciar**: Sempre bom fazer backup antes de grandes mudanças
3. **Logs de debug**: Os prints de `[INIT]` ajudam a verificar caminhos corretos

## 🆘 Se Nada Funcionar

Execute diagnóstico completo:

```bash
cd /root/screenshare2

echo "=== Diagnóstico Completo ==="
echo "1. Estrutura de diretórios:"
tree -L 2 static/

echo "2. Permissões:"
ls -la static/images/

echo "3. Espaço em disco:"
df -h

echo "4. Arquivos recentes:"
find static/images/ -type f -mmin -5

echo "5. Processo Python rodando:"
ps aux | grep python
```

Envie o resultado para análise detalhada.
