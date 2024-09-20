import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for, send_file, jsonify
from flask import Flask, render_template, request, redirect, session, url_for, send_file
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Caminho para salvar a imagem do frame
frame_path = 'current_frame.png'

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
    
# Function to update password and display the new password
def update_password(username, new_password):
    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET password = ? WHERE username = ?", (new_password, username)
    )
    conn.commit()
    user = conn.execute(
        "SELECT password FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if user:
        updated_password = user["password"]
        print(f"The new password for {username} is: {updated_password}")
def add_user(username, password, localidade):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password, localidade) VALUES (?, ?, ?)",
            (username, password, localidade),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return False  # Retorna False se o usuário já existe
    conn.close()
    return True

# Rota para login
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    localidade, is_admin = check_login(username, password)
    if localidade:
        session['logged_in'] = True
        session['username'] = username
        session['localidade'] = localidade
        session['is_admin'] = is_admin
        if is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('share_screen'))
    return redirect(url_for('index'))

# Rota para logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Rota para receber os frames da aba selecionada
@app.route('/upload_frame', methods=['POST'])
def upload_frame():
    if 'frame' in request.files:
        frame = request.files['frame']
        try:
            # Salva a imagem recebida como 'current_frame.png'
            frame.save(frame_path)
            print('Frame recebido e salvo com sucesso.')
        except Exception as e:
            print(f'Erro ao salvar o frame: {e}')
            return '', 500
    else:
        print('Nenhum frame recebido.')
    return '', 204

# Rota para servir a imagem mais recente
@app.route('/screen.png')
def serve_pil_image():
    if os.path.exists(frame_path):
        print('Servindo a imagem mais recente.')
        return send_file(frame_path, mimetype='image/png')
    else:
        print('Arquivo de imagem não encontrado.')
        return '', 404

# Rota pública para visualizar a tela (acessível externamente)
@app.route('/view_screen')
def view_screen():
    return render_template('view_screen.html')
    if 'logged_in' in session:
        return render_template('view_screen.html')
    return redirect(url_for('index'))

# Rota para renderizar a página de compartilhamento de tela

@app.route("/<localidade>/view_screen")
def view_screen_by_region(localidade):
    if "logged_in" in session and session.get("localidade") == localidade:
        # Renderiza o template com a variável localidade/região
        return render_template("view_screen.html", regiao=localidade)
    else:
        return redirect(
            url_for("index")
        )  # Redireciona se a localidade não estiver correta


# Rota para gerar o link de compartilhamento por localidade
@app.route("/<localidade>/share_screen")
def share_screen(localidade):
    if "logged_in" in session and session.get("localidade") == localidade:
        # Gera o link para visualizar a transmissão dessa localidade
        share_link = url_for(
            "view_screen_by_region", localidade=localidade, _external=True
        )
        return render_template(
            "share_screen.html", localidade=localidade, share_link=share_link
        )
    return redirect(url_for("index"))
# Página de login
@app.route("/")
def index():
    if "logged_in" in session:
        if session["is_admin"]:
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("share_screen", localidade=session["localidade"]))
    return render_template("login.html")

# Rota para o painel do administrador (apenas como exemplo)
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'logged_in' in session and session['is_admin']:
        return render_template('admin.html')
    return redirect(url_for('index'))
    
@app.route("/admin/manage_users")
def manage_users():
    if "logged_in" in session and session["is_admin"]:
        conn = get_db_connection()
        users = conn.execute(
            "SELECT * FROM users"
        ).fetchall()  # Fetch all users
        conn.close()
        return render_template("manage_users.html", users=users)
    else:
        return redirect(url_for("index"))
        
@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if "logged_in" in session and session["is_admin"]:
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        flash("User successfully deleted!", "success")
        return redirect(url_for("manage_users"))
    else:
        return redirect(url_for("index"))
        
@app.route("/admin/add_user", methods=["GET", "POST"])
def add_new_user():
    if "logged_in" in session and session["is_admin"]:
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            localidade = request.form["localidade"]
            if add_user(username, password, localidade):
                flash(
                    "User successfully added!", "success"
                )
            else:
                flash("Error: Username already exists!", "error")
            return redirect(url_for("admin_dashboard"))
        return render_template("add_user.html")
        
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if request.method == "POST":
        username = request.form["username"]
        new_password = request.form["new_password"]
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        if user:
            update_password(username, new_password)
            return redirect("/")
        else:
            return "User not found."

    return render_template("change_password.html")
    
create_database()
# Iniciar o aplicativo com acesso externo
if __name__ == "__main__":
    
    app.run(host='0.0.0.0', port=5000, debug=True)
