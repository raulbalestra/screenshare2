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
)
from flask_socketio import SocketIO, emit
from PIL import Image
import base64
from io import BytesIO
import pyscreenshot  # Para capturar a tela

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
            is_admin INTEGER DEFAULT 0
        )
    """
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO users (username, password, localidade, is_admin)
        VALUES
        ('curitiba_user', 'senha_curitiba', 'curitiba', 0),
        ('sp_user', 'senha_sp', 'sp', 0),
        ('admin', 'admin', 'admin', 1)
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
        return user["localidade"], user["is_admin"]
    return None, None

# Função para capturar a tela e salvar no Redis
def capture_screen():
    try:
        img_buffer = BytesIO()
        pyscreenshot.grab().save(img_buffer, 'PNG', quality=50)  # Captura a tela
        img_buffer.seek(0)
        frame_data = img_buffer.read()

        # Salva o frame no Redis com expiração de 5 segundos
        redis_client.setex('screen_frame', 5, frame_data)
        return frame_data
    except Exception as e:
        print(f"Erro ao capturar a tela: {e}")
        return None

# Função para transmitir o frame capturado via WebSocket
def broadcast_frame(frame_data):
    try:
        frame_b64 = base64.b64encode(frame_data).decode('utf-8')
        socketio.emit('frame_update', {'frame': frame_b64}, broadcast=True)
        print("Frame transmitido via WebSocket.")
    except Exception as e:
        print(f"Erro ao transmitir o frame via WebSocket: {e}")

# Rota para capturar a tela e servir como imagem estática via URL
@app.route('/screen.png')
def serve_pil_image():
    frame_data = capture_screen()  # Captura a tela
    if frame_data:
        return send_file(BytesIO(frame_data), mimetype='image/png')
    else:
        return "Erro ao capturar a tela", 500

# Evento WebSocket para atualizar o frame no cliente
@socketio.on('connect')
def handle_connect():
    emit('connect', {'message': 'Conectado ao servidor WebSocket'})

# Função para enviar o frame periodicamente para os clientes via WebSocket
def periodic_broadcast():
    while True:
        frame_data = capture_screen()
        if frame_data:
            broadcast_frame(frame_data)
        socketio.sleep(1)  # Intervalo de 1 segundo entre transmissões

# Inicia a transmissão periódica quando o servidor é iniciado
@socketio.on('start_broadcast')
def start_broadcast():
    socketio.start_background_task(target=periodic_broadcast)

# Rota para visualizar a tela capturada
@app.route('/<username>/tela')
def view_screen(username):
    if "logged_in" in session and session.get("username") == username:
        return render_template("tela.html", username=username)
    else:
        return redirect(url_for("index"))

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
            return redirect(url_for("compartilhar_tela", username=username))
    return redirect(url_for("index"))

# Rota para logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Rota para compartilhar tela
@app.route("/<username>/compartilhar-tela")
def compartilhar_tela(username):
    if "logged_in" in session and session.get("username") == username:
        return render_template("tela-compartilhada.html", username=username)
    return redirect(url_for("index"))

# Página inicial
@app.route("/")
def index():
    if "logged_in" in session:
        if session["is_admin"]:
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("compartilhar_tela", username=session["username"]))
    return render_template("login.html")

# Rota para o painel do administrador
@app.route("/admin_dashboard")
def admin_dashboard():
    if "logged_in" in session and session["is_admin"]:
        return render_template("admin.html")
    return redirect(url_for("index"))

# Rota de erro 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# Rota de erro 500
@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

# Criação do banco de dados ao iniciar
create_database()

# Iniciar o aplicativo com acesso externo
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
