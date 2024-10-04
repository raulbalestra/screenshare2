import os
import psycopg2
from flask import (
    Flask,
    flash,
    render_template,
    request,
    redirect,
    session,
    url_for,
    send_from_directory,
    abort,
    jsonify,
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)
app.secret_key = "sua_chave_secreta_aqui"

# Diretório base para armazenar as imagens das localidades
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "static", "images")


def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "nome_do_banco"),
        user=os.getenv("DB_USER", "usuario"),
        password=os.getenv("DB_PASSWORD", "senha"),
        port=os.getenv(
            "DB_PORT", "5432"
        ),  # Verifique se este valor no .env é apenas um número
        sslmode="require",  # Certifique-se de que o SSL está habilitado, se necessário
    )
    return conn


# Função para criar a tabela de usuários no banco de dados PostgreSQL
def create_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            localidade VARCHAR(100) NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE
        )
        """
    )

    # Verifique se há algum usuário já existente
    cursor.execute("SELECT COUNT(*) FROM users")
    user_check = cursor.fetchone()

    # Inserir usuários padrão se a tabela estiver vazia
    if user_check[0] == 0:
        cursor.execute(
            """
            INSERT INTO users (username, password, localidade, is_admin, is_active)
            VALUES
            (%s, %s, %s, %s, %s),
            (%s, %s, %s, %s, %s),
            (%s, %s, %s, %s, %s)
            """,
            (
                "curitiba_user",
                generate_password_hash("senha_curitiba"),
                "curitiba",
                False,
                True,
                "sp_user",
                generate_password_hash("senha_sp"),
                "sp",
                False,
                True,
                "admin",
                generate_password_hash("admin"),
                "admin",
                True,
                True,
            ),
        )

    conn.commit()
    cursor.close()
    conn.close()


# Função para validar o login
def check_login(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and check_password_hash(user[2], password):  # user[2] é a coluna password
        if user[5]:  # user[5] é a coluna is_active
            return user[3], user[4]  # Retorna localidade (user[3]) e is_admin (user[4])
        else:
            return "blocked", None
    return None, None


# Função para adicionar um usuário
def add_user(username, password, localidade):
    conn = get_db_connection()
    cursor = conn.cursor()

    hashed_password = generate_password_hash(password)

    try:
        cursor.execute(
            """
            INSERT INTO users (username, password, localidade, is_admin, is_active)
            VALUES (%s, %s, %s, %s, %s)
        """,
            (username, hashed_password, localidade, False, True),
        )

        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()  # Reverter alterações em caso de erro
        return False  # Retorna False se o usuário já existir
    finally:
        cursor.close()
        conn.close()

    return True


# Função para garantir que a pasta da localidade exista
def ensure_localidade_directory(localidade):
    local_dir = os.path.join(IMAGE_DIR, localidade.lower())
    if not os.path.isdir(local_dir):
        os.makedirs(local_dir)
        # Opcional: Criar um arquivo placeholder para screen.png
        placeholder_path = os.path.join(local_dir, "screen.png")
        if not os.path.isfile(placeholder_path):
            with open(placeholder_path, "wb") as f:
                pass  # Cria um arquivo vazio ou adicione uma imagem padrão
    return local_dir


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


# Rota para upload do frame
@app.route("/<localidade>/upload_frame", methods=["POST"])
def upload_frame(localidade):
    if "logged_in" in session and session.get("localidade") == localidade:
        # Define o caminho correto para salvar a imagem na pasta da localidade
        local_dir = ensure_localidade_directory(localidade)
        frame_path_local = os.path.join(local_dir, "screen.png")
        if "frame" in request.files:
            frame = request.files["frame"]
            try:
                frame.save(frame_path_local)
                print(f"Frame recebido e salvo com sucesso em {frame_path_local}.")
            except Exception as e:
                print(f"Erro ao salvar o frame: {e}")
                return "", 500
        else:
            print("Nenhum frame recebido.")
        return "", 204
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))


# Rota para servir a imagem do frame
@app.route("/serve_pil_image/<localidade>/screen.png")
def serve_pil_image(localidade):
    # Caminho para a pasta da localidade
    local_dir = os.path.join(IMAGE_DIR, localidade.lower())

    # Verifica se a pasta da localidade existe
    if not os.path.isdir(local_dir):
        print(f"Pasta da localidade não encontrada: {local_dir}")
        abort(404, description="Localidade não encontrada.")

    # Caminho completo para o arquivo screen.png
    image_path = os.path.join(local_dir, "screen.png")

    # Verifica se o arquivo screen.png existe
    if not os.path.isfile(image_path):
        print(f"Arquivo de imagem não encontrado no caminho: {image_path}")
        abort(404, description="Imagem não encontrada.")

    # Tentando servir a imagem corretamente
    try:
        response = send_from_directory(local_dir, "screen.png", mimetype="image/png")
        # Evita cache
        response.headers["Cache-Control"] = (
            "no-cache, no-store, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as e:
        print(f"Erro ao servir a imagem: {e}")
        abort(500, description="Erro ao servir a imagem.")


# Rota pública para visualizar a tela (acessível externamente)
@app.route("/tela")
def tela():
    return render_template("tela.html")


# Rota para renderizar a página de visualização de tela por localidade
@app.route("/<localidade>/tela")
def view_screen_by_region(localidade):
    return render_template("tela.html", localidade=localidade)


# Rota para compartilhar a tela
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
    else:
        flash("Acesso não autorizado.", "error")
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


# Rota para gerenciar usuários
@app.route("/admin/manage_users")
def manage_users():
    if "logged_in" in session and session["is_admin"]:
        conn = get_db_connection()
        cursor = conn.cursor()  # Criar um cursor para executar consultas
        cursor.execute(
            "SELECT id, username, localidade, is_admin, is_active FROM users"
        )  # Executar a consulta através do cursor
        users = cursor.fetchall()  # Buscar todos os resultados
        cursor.close()  # Fechar o cursor
        conn.close()  # Fechar a conexão
        return render_template(
            "manage_users.html", users=users
        )  # Passar os usuários como tuplas
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))


# Rota para deletar usuário
@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if "logged_in" in session and session["is_admin"]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Usuário excluído com sucesso!", "success")
        return redirect(url_for("manage_users"))
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))


# Rota para bloquear usuário
@app.route("/admin/block_user/<int:user_id>", methods=["POST"])
def block_user(user_id):
    if "logged_in" in session and session["is_admin"]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Usuário bloqueado com sucesso!", "success")
        return redirect(url_for("manage_users"))
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))


# Rota para desbloquear usuário
@app.route("/admin/unblock_user/<int:user_id>", methods=["POST"])
def unblock_user(user_id):
    if "logged_in" in session and session["is_admin"]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_active = 1 WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Usuário desbloqueado com sucesso!", "success")
        return redirect(url_for("manage_users"))
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))


# Rota para adicionar um novo usuário
@app.route("/admin/add_user", methods=["GET", "POST"])
def add_new_user():
    if "logged_in" in session and session["is_admin"]:
        if request.method == "POST":
            username = request.form["username"].strip()
            password = request.form["password"].strip()
            localidade = request.form["localidade"].strip().lower()

            # Validações básicas
            if not username or not password or not localidade:
                flash("Todos os campos são obrigatórios.", "error")
                return redirect(url_for("add_new_user"))

            # Você pode adicionar mais validações, como verificar formatos, tamanhos, etc.

            if add_user(username, password, localidade):
                # Garantir que a pasta para a localidade exista
                ensure_localidade_directory(localidade)
                flash("Usuário adicionado com sucesso!", "success")
            else:
                flash("Erro: Nome de usuário já existe!", "error")
            return redirect(url_for("manage_users"))
        return render_template("add_user.html")
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))


# Rota para o administrador alterar a senha de um usuário
@app.route("/admin/change_password/<int:user_id>", methods=["GET", "POST"])
def admin_change_password(user_id):
    if "logged_in" in session and session.get("is_admin"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            flash("Usuário não encontrado.", "error")
            return redirect(url_for("manage_users"))

        if request.method == "POST":
            new_password = request.form["new_password"]
            confirm_password = request.form["confirm_password"]

            if not new_password or not confirm_password:
                flash("Ambos os campos de senha são obrigatórios.", "error")
                cursor.close()
                conn.close()
                return redirect(url_for("admin_change_password", user_id=user_id))

            if new_password != confirm_password:
                flash("As senhas não coincidem.", "error")
                cursor.close()
                conn.close()
                return redirect(url_for("admin_change_password", user_id=user_id))

            try:
                hashed_password = generate_password_hash(new_password)
                cursor.execute(
                    "UPDATE users SET password = %s WHERE id = %s",
                    (hashed_password, user_id),
                )
                conn.commit()
                flash(f"Senha do usuário {user[1]} atualizada com sucesso.", "success")
                return redirect(url_for("manage_users"))
            except Exception as e:
                flash(f"Erro ao atualizar a senha: {str(e)}", "error")
                return redirect(url_for("admin_change_password", user_id=user_id))
            finally:
                cursor.close()
                conn.close()
        return render_template("admin_change_password.html", user=user)
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))


# Rota para o administrador alterar sua própria senha
@app.route("/admin/change_own_password", methods=["GET", "POST"])
def admin_change_own_password():
    if "logged_in" in session and session.get("is_admin"):
        if request.method == "POST":
            username = session.get("username")
            current_password = request.form["current_password"]
            new_password = request.form["new_password"]
            confirm_password = request.form["confirm_password"]

            if not current_password or not new_password or not confirm_password:
                flash("Todos os campos são obrigatórios.", "error")
                return redirect(url_for("admin_change_own_password"))

            if new_password != confirm_password:
                flash("As senhas não coincidem.", "error")
                return redirect(url_for("admin_change_own_password"))

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user[2], current_password):
                try:
                    hashed_password = generate_password_hash(new_password)
                    cursor.execute(
                        "UPDATE users SET password = %s WHERE username = %s",
                        (hashed_password, username),
                    )
                    conn.commit()
                    flash("Senha atualizada com sucesso.", "success")
                    return redirect(url_for("admin_dashboard"))
                except Exception as e:
                    flash(f"Erro ao atualizar a senha: {str(e)}", "error")
                    return redirect(url_for("admin_change_own_password"))
                finally:
                    cursor.close()
                    conn.close()
            else:
                flash("Senha atual incorreta.", "error")
                cursor.close()
                conn.close()
                return redirect(url_for("admin_change_own_password"))
        return render_template("admin_change_own_password.html")
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))


# Rota para o usuário alterar sua própria senha
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "logged_in" in session:
        username = session.get("username")
        if request.method == "POST":
            new_password = request.form["new_password"]
            confirm_password = request.form["confirm_password"]

            if not new_password or not confirm_password:
                flash("Ambos os campos de senha são obrigatórios.", "error")
                return redirect(url_for("change_password"))

            if new_password != confirm_password:
                flash("As senhas não coincidem.", "error")
                return redirect(url_for("change_password"))

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            if user:
                try:
                    hashed_password = generate_password_hash(new_password)
                    cursor.execute(
                        "UPDATE users SET password = %s WHERE username = %s",
                        (hashed_password, username),
                    )
                    conn.commit()
                    flash("Senha atualizada com sucesso.", "success")
                    return redirect("/")
                except Exception as e:
                    flash(f"Erro ao atualizar a senha: {str(e)}", "error")
                    return redirect(url_for("change_password"))
                finally:
                    cursor.close()
                    conn.close()
            else:
                flash("Usuário não encontrado.", "error")
                cursor.close()
                conn.close()
                return redirect(url_for("change_password"))
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))

    return render_template("change_password.html")


# Rota para limpar o cache de uma localidade específica
@app.route("/<localidade>/clear_cache", methods=["POST"])
def clear_cache(localidade):
    # Caminho para o arquivo screen.png da localidade
    local_dir = os.path.join(IMAGE_DIR, localidade.lower())
    frame_path_local = os.path.join(local_dir, "screen.png")
    print(
        f"[clear_cache] Recebida requisição para limpar cache da localidade: {localidade}"
    )
    print(f"[clear_cache] Caminho do arquivo: {frame_path_local}")
    try:
        if os.path.exists(frame_path_local):
            os.remove(frame_path_local)
            print("[clear_cache] Arquivo deletado com sucesso.")
            return jsonify({"message": "Cache limpo com sucesso."}), 200
        else:
            print("[clear_cache] Arquivo não encontrado.")
            return (
                jsonify(
                    {
                        "message": "Nenhum cache encontrado para a localidade especificada."
                    }
                ),
                404,
            )
    except Exception as e:
        print(f"[clear_cache] Erro ao deletar o arquivo: {e}")
        return jsonify({"message": f"Erro ao limpar cache: {str(e)}"}), 500


# Página de erro 404 - Página não encontrada
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# Página de erro 500 - Erro interno do servidor
@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


# Inicializar o banco de dados antes de servir qualquer rota
create_database()

# Iniciar o aplicativo com acesso externo
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
