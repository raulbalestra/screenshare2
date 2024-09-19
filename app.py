import os
import io
import redis
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
    make_response,
)

app = Flask(__name__)
app.secret_key = "sua_chave_secreta_aqui"

# Configuração do Redis usando a URL fornecida
redis_url = os.getenv('REDIS_URL', 'redis://red-crm4cde8ii6s738s0acg:6379')
redis_client = redis.Redis.from_url(redis_url)

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
            is_admin INTEGER DEFAULT 0  -- 0 para usuários comuns, 1 para admin
        )
    """
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO users (username, password, localidade, is_admin)
        VALUES
        ('curitiba_user', 'senha_curitiba', 'curitiba', 0),
        ('sp_user', 'senha_sp', 'sp', 0),
        ('admin', 'admin', 'admin', 1)  -- Admin com valor 1
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
        return user["localidade"], user["is_admin"]  # Retorna a localidade e se é admin
    return None, None

# Função para armazenar frame no Redis com expiração de 2 segundos
def save_frame_to_cache(localidade, frame_data):
    redis_client.setex(f'frame:{localidade}', 2, frame_data)  # Expira após 2 segundos

# Função para recuperar frame do Redis
def get_frame_from_cache(localidade):
    return redis_client.get(f'frame:{localidade}')

# Rota para login
@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    localidade, is_admin = check_login(username, password)
    if localidade:
        session["logged_in"] = True
        session["username"] = username
        session["localidade"] = localidade
        session["is_admin"] = is_admin
        if is_admin:
            return redirect(url_for("admin_dashboard"))
        else:
            # Redireciona para a rota de compartilhar tela com username
            return redirect(url_for("compartilhar_tela", username=username))

    return redirect(url_for("index"))

# Rota para receber os frames da aba selecionada
@app.route("/<localidade>/upload_frame", methods=["POST"])
def upload_frame(localidade):
    if "logged_in" in session and session.get("localidade") == localidade:
        if "frame" in request.files:
            frame = request.files["frame"]
            try:
                frame_data = frame.read()
                save_frame_to_cache(localidade, frame_data)
                print(f"Frame recebido e salvo no cache para {localidade}.")
            except Exception as e:
                print(f"Erro ao salvar o frame no cache: {e}")
                return "", 500
        else:
            print("Nenhum frame recebido.")
        return "", 204
    return redirect(url_for("index"))

# Rota para servir o frame
@app.route("/<localidade>/screen.png")
def serve_pil_image(localidade):
    if "logged_in" in session and session.get("localidade") == localidade:
        frame_data = get_frame_from_cache(localidade)
        if frame_data:
            return make_response(frame_data, 200, {'Content-Type': 'image/png'})
        else:
            return "Frame não encontrado.", 404
    return redirect(url_for("index"))

# Rota para compartilhar tela com nome de usuário na URL
@app.route("/<username>/compartilhar-tela")
def compartilhar_tela(username):
    if "logged_in" in session and session.get("username") == username:
        localidade = session.get("localidade")
        # Gera o link para visualizar a tela do usuário, incluindo o username na URL
        share_link = url_for("view_screen_by_region", username=username, _external=True)
        return render_template(
            "tela-compartilhada.html",
            localidade=localidade,
            username=username,
            share_link=share_link,
        )
    return redirect(url_for("index"))

# Rota para visualizar a tela compartilhada pelo usuário
@app.route("/<username>/tela", endpoint="view_screen_by_region")
def view_screen_by_region(username):
    if "logged_in" in session and session.get("username") == username:
        localidade = session["localidade"]
        # Renderiza o template de visualização da tela
        return render_template("tela.html", regiao=localidade, username=username)
    else:
        return redirect(url_for("index"))

# Página de login
@app.route("/")
def index():
    if "logged_in" in session:
        if session["is_admin"]:
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("compartilhar_tela", username=session["username"]))
    return render_template("login.html")

# Rota para o painel do administrador (apenas como exemplo)
@app.route("/admin_dashboard")
def admin_dashboard():
    if "logged_in" in session and session["is_admin"]:
        return render_template("admin.html")
    return redirect(url_for("index"))

# Rota para trocar senha
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

# Rota para adicionar novos usuários
@app.route("/admin/add_user", methods=["GET", "POST"])
def add_new_user():
    if "logged_in" in session and session["is_admin"]:
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            localidade = request.form["localidade"]
            if add_user(username, password, localidade):
                flash(
                    "Usuário adicionado com sucesso!", "success"
                )  # Mensagem de sucesso
            else:
                flash("Erro: Nome de usuário já existe!", "error")  # Mensagem de erro
            return redirect(
                url_for("admin_dashboard")
            )  # Redireciona para a página do admin
        return render_template("add_user.html")

# Rota para gerenciar usuários
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

# Rota para deletar usuário
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

# Função para atualizar a senha e exibir a nova senha
def update_password(username, new_password):
    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET password = ? WHERE username = ?", (new_password, username)
    )
    conn.commit()

    # Verificando se a senha foi atualizada
    user = conn.execute(
        "SELECT password FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if user:
        updated_password = user["password"]
        print(f"A nova senha de {username} é: {updated_password}")

# Rota para adicionar usuários no banco de dados
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

# Rota para logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

# Criação do banco de dados ao iniciar
create_database()

# Iniciar o aplicativo com acesso externo
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
