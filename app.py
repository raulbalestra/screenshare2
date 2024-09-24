import os
import sqlite3
from flask import (
    Flask,
    flash,
    render_template,
    request,
    redirect,
    session,
    url_for,
    send_file,
    jsonify,
)

app = Flask(__name__)
app.secret_key = "sua_chave_secreta_aqui"

# Função para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn

# Função para criar o banco de dados
def create_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            localidade TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,  -- 0 para usuários comuns, 1 para admin
            is_active INTEGER DEFAULT 1  -- 1 para ativo, 0 para bloqueado
        )
        """
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO users (username, password, localidade, is_admin, is_active)
        VALUES
        ('curitiba_user', 'senha_curitiba', 'curitiba', 0, 1),
        ('sp_user', 'senha_sp', 'sp', 0, 1),
        ('admin', 'admin', 'admin', 1, 1)
        """
    )
    conn.commit()
    conn.close()

# Função para validar o login
def check_login(username, password):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?", (username, password)
    ).fetchone()
    conn.close()
    if user:
        if user["is_active"]:
            return (
                user["localidade"],
                user["is_admin"],
            )  # Retorna a localidade e se é admin
        else:
            return "blocked", None
    return None, None

# Função para atualizar a senha e exibir a nova senha
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
        print(f"A nova senha para {username} é: {updated_password}")

def add_user(username, password, localidade):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password, localidade, is_active) VALUES (?, ?, ?, 1)",
            (username, password, localidade),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return False  # Retorna False se o usuário já existe
    conn.close()
    return True

# Rota para login
@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    localidade, is_admin = check_login(username, password)
    if localidade == "blocked":
        flash("Seu acesso foi bloqueado pelo administrador.", "error")
        return redirect(url_for("index"))
    elif localidade:
        session["logged_in"] = True
        session["username"] = username
        session["localidade"] = localidade
        session["is_admin"] = is_admin
        if is_admin:
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("share_screen", localidade=localidade))
    else:
        flash("Nome de usuário ou senha inválidos.", "error")
        return redirect(url_for("index"))

# Rota para logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/<localidade>/upload_frame", methods=["POST"])
def upload_frame(localidade):
    frame_path_local = os.path.join(os.getcwd(), f"{localidade}_screen.png")  # Nome fixo para cada localidade

    if "frame" in request.files:
        frame = request.files["frame"]
        try:
            # Salva a imagem recebida como 'localidade_screen.png'
            frame.save(frame_path_local)
            print(f"Frame recebido e salvo com sucesso em {frame_path_local}.")
        except Exception as e:
            print(f"Erro ao salvar o frame: {e}")
            return "", 500
    else:
        print("Nenhum frame recebido.")
    return "", 204

@app.route("/<localidade>/screen.png")
def serve_pil_image(localidade):
    frame_path_local = os.path.join(os.getcwd(), f"{localidade}_screen.png")
    if os.path.exists(frame_path_local):
        print(f"Servindo a imagem mais recente para {localidade}.")
        response = send_file(frame_path_local, mimetype="image/png")
        # Cabeçalhos para evitar cache
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    else:
        print(f"Arquivo de imagem não encontrado no caminho: {frame_path_local}")
        return "", 404

# Rota pública para visualizar a tela (acessível externamente)
@app.route("/tela")
def tela():
    return render_template("tela.html")

# Rota para renderizar a página de visualização de tela por localidade
@app.route("/<localidade>/tela")
def view_screen_by_region(localidade):
    return render_template("tela.html", localidade=localidade)

@app.route("/<localidade>/tela-compartilhada")
def share_screen(localidade):
    if "logged_in" in session and session.get("localidade") == localidade:
        # Gera o link para visualizar a transmissão dessa localidade
        share_link = url_for(
            "view_screen_by_region", localidade=localidade, _external=True
        )
        username = session.get("username")
        return render_template(
            "tela_compartilhada.html",
            localidade=localidade,
            share_link=share_link,
            username=username,
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

# Rota para o painel do administrador
@app.route("/admin_dashboard")
def admin_dashboard():
    if "logged_in" in session and session["is_admin"]:
        return render_template("admin.html")
    return redirect(url_for("index"))

@app.route("/admin/manage_users")
def manage_users():
    if "logged_in" in session and session["is_admin"]:
        conn = get_db_connection()
        users = conn.execute(
            "SELECT * FROM users"
        ).fetchall()  # Busca todos os usuários
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
        flash("Usuário excluído com sucesso!", "success")
        return redirect(url_for("manage_users"))
    else:
        return redirect(url_for("index"))

@app.route("/admin/block_user/<int:user_id>", methods=["POST"])
def block_user(user_id):
    if "logged_in" in session and session["is_admin"]:
        conn = get_db_connection()
        conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        flash("Usuário bloqueado com sucesso!", "success")
        return redirect(url_for("manage_users"))
    else:
        return redirect(url_for("index"))

@app.route("/admin/unblock_user/<int:user_id>", methods=["POST"])
def unblock_user(user_id):
    if "logged_in" in session and session["is_admin"]:
        conn = get_db_connection()
        conn.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        flash("Usuário desbloqueado com sucesso!", "success")
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
                flash("Usuário adicionado com sucesso!", "success")
            else:
                flash("Erro: Nome de usuário já existe!", "error")
            return redirect(url_for("admin_dashboard"))
        return render_template("add_user.html")
    else:
        return redirect(url_for("index"))

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
            return "Usuário não encontrado."
    return render_template("change_password.html")

# Rota para limpar o cache de uma localidade específica
@app.route("/<localidade>/clear_cache", methods=["POST"])
def clear_cache(localidade):
    frame_path_local = os.path.join(os.getcwd(), f"{localidade}_screen.png")
    print(f"[clear_cache] Recebida requisição para limpar cache da localidade: {localidade}")
    print(f"[clear_cache] Caminho do arquivo: {frame_path_local}")
    try:
        if os.path.exists(frame_path_local):
            os.remove(frame_path_local)
            print("[clear_cache] Arquivo deletado com sucesso.")
            return jsonify({"message": "Cache limpo com sucesso."}), 200
        else:
            print("[clear_cache] Arquivo não encontrado.")
            return jsonify({"message": "Nenhum cache encontrado para a localidade especificada."}), 404
    except Exception as e:
        print(f"[clear_cache] Erro ao deletar o arquivo: {e}")
        return jsonify({"message": f"Erro ao limpar cache: {str(e)}"}), 500

create_database()

# Iniciar o aplicativo com acesso externo
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
