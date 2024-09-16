import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'  # Substitua por uma chave segura
socketio = SocketIO(app, logger=True, engineio_logger=True)

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
            localidade TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password, localidade)
        VALUES
        ('curitiba_user', 'senha_curitiba', 'curitiba'),
        ('sp_user', 'senha_sp', 'sp')
    ''')
    conn.commit()
    conn.close()

# Função para validar o login
def check_login(username, password):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
    conn.close()
    return user['localidade'] if user else None

# Página de login
@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('share_screen', localidade=session['localidade']))
    return render_template('login.html')

# Rota para login
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    localidade = check_login(username, password)
    if localidade:
        session['logged_in'] = True
        session['localidade'] = localidade
        return redirect(url_for('share_screen', localidade=localidade))
    else:
        return "Login falhou. Tente novamente. <a href='/'>Voltar</a>"

# Rota para compartilhar a tela
@app.route('/<localidade>')
def share_screen(localidade):
    if 'logged_in' in session and session['localidade'] == localidade:
        return render_template('share_screen.html', localidade=localidade)
    else:
        return redirect('/')

# Rota para visualizar a tela compartilhada
@app.route('/<localidade>/view')
def view_screen(localidade):
    return render_template('view_screen.html', localidade=localidade)

# WebRTC signaling
@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    emit('webrtc_offer', data, broadcast=True)

@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    emit('webrtc_answer', data, broadcast=True)

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    emit('ice_candidate', data, broadcast=True)

# Rota para logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    create_database()  # Garante que o banco de dados e a tabela users sejam criados
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
