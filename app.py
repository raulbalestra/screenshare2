import os
import sqlite3
import pyscreenshot
from flask import Flask, render_template, request, redirect, session, url_for, send_file
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Função para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para criar o banco de dados
def create_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            localidade TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0  -- 0 para usuários comuns, 1 para admin
        )
    ''')
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password, localidade, is_admin)
        VALUES
        ('curitiba_user', 'senha_curitiba', 'curitiba', 0),
        ('sp_user', 'senha_sp', 'sp', 0),
        ('admin', 'admin', 'admin', 1)  -- Admin com valor 1
    ''')
    conn.commit()
    conn.close()

# Função para validar o login
def check_login(username, password):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
    conn.close()
    if user:
        return user['localidade'], user['is_admin']  # Retorna a localidade e se é admin
    return None, None

# Rota para capturar e servir a imagem da tela usando `pyscreenshot`
@app.route('/screen.png')
def serve_pil_image():
    img_buffer = BytesIO()
    # Captura a tela usando pyscreenshot
    pyscreenshot.grab().save(img_buffer, 'PNG', quality=50)
    img_buffer.seek(0)
    return send_file(img_buffer, mimetype='image/png')

# Rota pública para visualizar a tela (acessível externamente)
@app.route('/view_screen')
def view_screen():
    return render_template('view_screen.html')

# Rota para renderizar a página de compartilhamento de tela
@app.route('/share_screen')
def share_screen():
    if 'logged_in' in session:
        return render_template('share_screen.html', localidade=session['localidade'])
    return redirect(url_for('index'))

# Outras funções de gerenciamento de usuários...

# Página de login
@app.route('/')
def index():
    if 'logged_in' in session:
        if session['is_admin']:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('share_screen'))
    return render_template('login.html')

# Criação do banco de dados ao iniciar
create_database()

# Iniciar o aplicativo com acesso externo
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
