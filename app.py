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
    frame_data = redis_client.get('screen_frame')  # Recupera o frame do Redis
    if not frame_data:
        frame_data = capture_screen()  # Captura a tela se não houver no cache
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

# Rota para visualizar a tela capturada (acesso público, sem login)
@app.route('/tela')
def view_screen():
    return render_template("tela.html")

# Página inicial
@app.route("/")
def index():
    return render_template("login.html")

# Rota para logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Rota de erro 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# Rota de erro 500
@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

# Iniciar o aplicativo com acesso externo
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
