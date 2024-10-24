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
app.secret_key = os.getenv("SECRET_KEY", "sua_chave_secreta_aqui")

# Diretório base para armazenar as imagens das localidades
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "static", "images")

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "nome_do_banco"),
        user=os.getenv("DB_USER", "usuario"),
        password=os.getenv("DB_PASSWORD", "senha"),
        port=os.getenv("DB_PORT", "5432"),
        sslmode="require",
    )
    return conn

def create_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            localidade VARCHAR(100) NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE
        );
        """
    )
    cursor.execute("SELECT COUNT(*) FROM users")
    user_check = cursor.fetchone()
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

def check_login(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and check_password_hash(user[2], password):
        if user[5]:
            return user[3], user[4]
        else:
            return "blocked", None
    return None, None

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
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()
    return True

def ensure_localidade_directory(localidade):
    local_dir = os.path.join(IMAGE_DIR, localidade.lower())
    if not os.path.isdir(local_dir):
        os.makedirs(local_dir)
        placeholder_path = os.path.join(local_dir, "screen.png")
        if not os.path.isfile(placeholder_path):
            with open(placeholder_path, "wb") as f:
                pass
    return local_dir

def clean_cache(localidade):
    local_dir = os.path.join(IMAGE_DIR, localidade.lower())
    frame_path = os.path.join(local_dir, "screen.png")
    try:
        if os.path.exists(frame_path):
            os.remove(frame_path)
            print(f"Cache limpo para a localidade: {localidade}")
    except Exception as e:
        print(f"Erro ao limpar o cache: {e}")

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

@app.route("/logout")
def logout():
    if "localidade" in session:
        clean_cache(session["localidade"])
    session.clear()
    return redirect(url_for("index"))

@app.route("/<localidade>/upload_frame", methods=["POST"])
def upload_frame(localidade):
    if "logged_in" in session and session.get("localidade") == localidade:
        local_dir = ensure_localidade_directory(localidade)
        frame_path = os.path.join(local_dir, "screen.png")
        if "frame" in request.files:
            frame = request.files["frame"]
            try:
                frame.save(frame_path)
                print(f"Frame salvo com sucesso em {frame_path}.")
            except Exception as e:
                print(f"Erro ao salvar o frame: {e}")
                return "", 500
        else:
            print("Nenhum frame recebido.")
        return "", 204
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))

@app.route("/serve_pil_image/<localidade>/screen.png")
def serve_pil_image(localidade):
    local_dir = os.path.join(IMAGE_DIR, localidade.lower())
    image_path = os.path.join(local_dir, "screen.png")
    if not os.path.isfile(image_path):
        abort(404, description="Imagem não encontrada.")
    try:
        response = send_from_directory(local_dir, "screen.png", mimetype="image/png")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as e:
        abort(500, description="Erro ao servir a imagem.")

@app.route("/<localidade>/clear_cache", methods=["POST"])
def clear_cache_route(localidade):
    if "logged_in" in session and session.get("localidade") == localidade:
        clean_cache(localidade)
        return jsonify({"message": "Cache limpo com sucesso."}), 200
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))

# Inicializar o banco de dados
create_database()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
