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
    make_response,
)
from flask_socketio import SocketIO, emit
from PIL import Image
import base64

app = Flask(__name__)
app.secret_key = "sua_chave_secreta_aqui"
socketio = SocketIO(app)

# Configuração do Redis usando a URL fornecida
redis_url = os.getenv('REDIS_URL', 'redis://red-crm4cde8ii6s738s0acg:6379')
redis_client = redis.Redis.from_url(redis_url, max_connections=100)

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

# Função para comprimir o frame
def compress_frame(frame_data):
    image = Image.open(io.BytesIO(frame_data))
    output = io.BytesIO()
    # Compressão com qualidade 50% para reduzir o tamanho
    image.save(output, format='JPEG', quality=50)
    return output.getvalue()

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
                compressed_frame = compress_frame(frame_data)  # Comprimir o frame
                save_frame_to_cache(localidade, compressed_frame)
                broadcast_frame(localidade, compressed_frame)  # Enviar via WebSocket
                print(f"Frame recebido e salvo no cache para {localidade}.")
            except Exception as e:
                print(f"Erro ao salvar o frame no cache: {e}")
                return "", 500
        else:
            print("Nenhum frame recebido.")
        return "", 204
    return redirect(url_for("index"))

# Função para enviar frame via WebSocket
def broadcast_frame(localidade, frame_data):
    # Codificar o frame em base64 para envio via WebSocket
    frame_b64 = base64.b64encode(frame_data).decode('utf-8')
    socketio.emit('frame_update', {'localidade': localidade, 'frame': frame_b64}, broadcast=True)

# Evento WebSocket para atualizar o frame no cliente
@socketio.on('connect')
def handle_connect():
    emit('connect', {'message': 'Conectado ao servidor WebSocket'})

# Rota para compartilhar tela com nome de usuário na URL
@app.route("/<username>/compartilhar-tela")
def compartilhar_tela(username):
    if "logged_in" in session and session.get("username") == username:
        localidade = session.get("localidade")
        return render_template(
            "tela-compartilhada.html",
            localidade=localidade,
            username=username,
        )
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

# Função para adicionar usuários no banco de dados
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
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
