import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Função para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row  # Permite acesso aos dados por nome de coluna
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

# Função para atualizar a senha e exibir a nova senha
def update_password(username, new_password):
    conn = get_db_connection()
    conn.execute('UPDATE users SET password = ? WHERE username = ?', (new_password, username))
    conn.commit()

    # Verificando se a senha foi atualizada
    user = conn.execute('SELECT password FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()

    if user:
        updated_password = user['password']
        print(f"A nova senha de {username} é: {updated_password}")

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
        return "Login falhou. Tente novamente."

# Rota para compartilhamento de tela
@app.route('/<localidade>')
def share_screen(localidade):
    if 'logged_in' in session and session['localidade'] == localidade:
        return render_template('share_screen.html', localidade=localidade)
    else:
        return redirect('/')

# Rota para trocar senha
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user:
            update_password(username, new_password)
            return redirect('/')
        else:
            return "Usuário não encontrado."

    return render_template('change_password.html')

# Rota para logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    create_database()  # Garante que o banco de dados e a tabela users sejam criados
    app.run(debug=True)
