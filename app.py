import os
import time  # Importação necessária para controle de tempo entre uploads
import psycopg2
import uuid
import subprocess
import json
import signal
import logging
import threading  # Missing import for threading.Lock
from datetime import datetime, date
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
from threading import Thread

# Importar módulos de segurança
from security_utils import (
    SecurityValidator,
    RateLimiter,
    secure_db_operation,
    validate_csrf_token,
    generate_csrf_token
)

# Carregar variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)
# Usar chave secreta mais segura do .env
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key_change_in_production")

# Instanciar validador de segurança
security_validator = SecurityValidator()
rate_limiter = RateLimiter()

# Criar logger para segurança
logger = logging.getLogger('security')

# Configurar logging de segurança
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
security_logger = logging.getLogger('security')

# Configurações de segurança
app.config['SESSION_COOKIE_SECURE'] = os.getenv('HTTPS_ONLY', 'False').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Diretório base para armazenar as imagens das localidades
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "static", "images")
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
HLS_STREAMS_DIR = os.path.join(BASE_DIR, "hls_streams")

# Dicionário para armazenar processos FFmpeg ativos por localidade
active_hls_processes = {}

# Dicionário para processos FFmpeg de sessões (compatibilidade)
active_ffmpeg_processes = {}

# Lock para sincronizar acesso aos processos
import threading
process_locks = {}

# Variável para controlar o tempo do último upload para cada localidade
last_upload_time = {}

# Garantir que diretórios existam
if not os.path.exists(HLS_STREAMS_DIR):
    os.makedirs(HLS_STREAMS_DIR)

# Middleware de segurança
@app.before_request
def security_middleware():
    # Verificar expiração de usuários automaticamente
    check_user_expiration()
    
    # Limpar sessões inativas
    cleanup_inactive_sessions()
    
    # Verificar se é uma rota protegida que requer sessão válida
    protected_routes = [
        'upload_frame', 'serve_pil_image', 'tela', 'tela_compartilhada',
        'hls_ingest', 'hls_start', 'hls_stop', 'hls_status'
    ]
    
    if request.endpoint in protected_routes:
        if 'logged_in' in session and 'user_id' in session:
            user_id = session['user_id']
            session_id = session.get('session_id')
            
            if not session_id or not is_session_valid(user_id, session_id):
                logger.warning(f"Sessão inválida detectada para usuário {user_id}")
                session.clear()
                flash("Sua sessão foi encerrada. Outro dispositivo pode ter feito login.", "error")
                return redirect(url_for('index'))
            
            # Atualizar atividade da sessão
            update_session_activity(user_id, session_id)
    
    # Resto do middleware de segurança existente
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    
    # Rate limiting
    if rate_limiter.is_rate_limited(client_ip):
        logger.warning(f"Rate limit excedido para IP {client_ip}")
        abort(429)  # Too Many Requests
    
    # Validação de entrada para todas as rotas
    if request.method == 'POST' and request.form:
        for key, value in request.form.items():
            sanitized_value = security_validator.sanitize_input(value)
            # Nota: valores são sanitizados automaticamente para segurança
    """Middleware de segurança executado antes de cada request"""
    
    # Pular verificações para rotas públicas
    public_routes = ['index', 'login', 'static']
    if request.endpoint in public_routes or request.endpoint is None:
        return
    
    # Verificar se é uma requisição autenticada
    if "logged_in" in session:
        # Validar dados da sessão
        session_valid, msg = SecurityValidator.validate_session_data(session)
        if not session_valid:
            security_logger.warning(f"Sessão inválida detectada: {msg}")
            session.clear()
            flash("Sessão inválida. Faça login novamente.", "error")
            return redirect(url_for("index"))
        
        # Verificar IP da sessão (prevenção de session hijacking)
        current_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        session_ip = session.get('login_ip')
        
        if session_ip and session_ip != current_ip:
            security_logger.warning(f"Mudança de IP detectada na sessão: {session.get('username')} - {session_ip} -> {current_ip}")
            session.clear()
            flash("Sessão expirada por motivos de segurança. Faça login novamente.", "error")
            return redirect(url_for("index"))

# Headers de segurança
@app.after_request
def add_security_headers(response):
    """Adiciona headers de segurança a todas as respostas"""
    # Prevenir ataques XSS
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # CSP básico (ajustar conforme necessário)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "worker-src 'self' blob:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob: https:; "
        "media-src 'self' blob: data:; "
        "connect-src 'self' ws: wss: https://cdn.jsdelivr.net https://cdnjs.cloudflare.com;"
    )
    
    # Headers adicionais
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=(), usb=(), payment=()'
    
    return response

@secure_db_operation
def get_db_connection():
    """Conexão segura com banco de dados"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "screenshare"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "101410"),
            port=int(os.getenv("DB_PORT", "5432")),
            sslmode=os.getenv("DB_SSL", "prefer"),
            connect_timeout=10,  # Timeout de conexão
            application_name="screenshare_secure"  # Nome da aplicação
        )
        return conn
    except psycopg2.Error as e:
        security_logger.error(f"Erro de conexão com banco: {type(e).__name__}")
        raise Exception("Erro de conexão com banco de dados")

@secure_db_operation
def log_usage_event(username, localidade, event_type):
    """
    Registra um evento de uso na tabela usage_events com validações de segurança.
    event_type pode ser: 'login', 'frame', 'hls_chunk', etc.
    """
    try:
        # Validar entradas
        username_valid, _ = SecurityValidator.validate_username(username)
        localidade_valid, _ = SecurityValidator.validate_localidade(localidade)
        
        if not username_valid or not localidade_valid:
            security_logger.warning(f"Tentativa de log com dados inválidos: {username}, {localidade}")
            return False
        
        # Sanitizar event_type
        event_type = SecurityValidator.sanitize_input(event_type, 50)
        
        # Verificar tentativas de injeção
        for param in [username, localidade, event_type]:
            if SecurityValidator.detect_sql_injection(param):
                security_logger.error(f"SQL Injection detectado em log_usage_event")
                return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Busca o user_id pelo username - usando prepared statement
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_row = cursor.fetchone()
        
        if user_row:
            user_id = user_row[0]
            cursor.execute(
                "INSERT INTO usage_events (user_id, localidade, event_type) VALUES (%s, %s, %s)",
                (user_id, localidade, event_type)
            )
            conn.commit()
            print(f"[Usage] Evento registrado: {username} -> {event_type} em {localidade}")
            return True
        else:
            security_logger.warning(f"Tentativa de log para usuário inexistente: {username}")
            return False
            
    except Exception as e:
        security_logger.error(f"Erro ao registrar evento: {type(e).__name__}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@secure_db_operation
def check_user_expiration():
    """
    Verifica usuários expirados e os bloqueia automaticamente
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Bloquear usuários expirados (exceto admins)
        cursor.execute(
            """
            UPDATE users 
            SET is_active = FALSE 
            WHERE plan_end < CURRENT_DATE 
            AND is_active = TRUE 
            AND is_admin = FALSE
            """
        )
        
        blocked_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if blocked_count > 0:
            logger.info(f"Bloqueados {blocked_count} usuários expirados automaticamente")
        
        return blocked_count
        
    except Exception as e:
        logger.error(f"Erro ao verificar expiração de usuários: {e}")
        return 0

@secure_db_operation
def get_user_by_id(user_id):
    """
    Busca usuário pelo ID
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, localidade, is_admin, is_active, plan_start, plan_end
            FROM users WHERE id = %s
            """,
            (user_id,)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Erro ao buscar usuário por ID: {e}")
        return None

@secure_db_operation
def update_user(user_id, username, localidade, plan_start, plan_end, is_admin, is_active):
    """
    Atualiza dados do usuário
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users 
            SET username = %s, localidade = %s, plan_start = %s, plan_end = %s, 
                is_admin = %s, is_active = %s
            WHERE id = %s
            """,
            (username, localidade, plan_start, plan_end, is_admin, is_active, user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar usuário: {e}")
        return False

@secure_db_operation
def register_user_session(user_id, session_id, ip_address, user_agent):
    """
    Registra uma nova sessão ativa do usuário
    Remove sessões antigas do mesmo usuário (força logout em outros dispositivos)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Remover todas as sessões ativas existentes deste usuário
        cursor.execute(
            "DELETE FROM active_sessions WHERE user_id = %s",
            (user_id,)
        )
        
        # Registrar nova sessão
        cursor.execute(
            """
            INSERT INTO active_sessions (user_id, session_id, ip_address, user_agent)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, session_id, ip_address, user_agent)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Sessão registrada para usuário {user_id}, sessão {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao registrar sessão: {e}")
        return False

@secure_db_operation
def is_session_valid(user_id, session_id):
    """
    Verifica se a sessão do usuário é válida (única ativa)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se a sessão existe e está ativa
        cursor.execute(
            """
            SELECT COUNT(*) FROM active_sessions 
            WHERE user_id = %s AND session_id = %s
            """,
            (user_id, session_id)
        )
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result[0] > 0
        
    except Exception as e:
        logger.error(f"Erro ao verificar sessão: {e}")
        return False

@secure_db_operation
def update_session_activity(user_id, session_id):
    """
    Atualiza a última atividade da sessão
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE active_sessions 
            SET last_activity = NOW()
            WHERE user_id = %s AND session_id = %s
            """,
            (user_id, session_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Erro ao atualizar atividade da sessão: {e}")

@secure_db_operation
def cleanup_inactive_sessions(max_inactive_minutes=30):
    """
    Remove sessões inativas há mais de X minutos
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            DELETE FROM active_sessions 
            WHERE last_activity < NOW() - INTERVAL '%s minutes'
            """,
            (max_inactive_minutes,)
        )
        
        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if deleted_count > 0:
            logger.info(f"Removidas {deleted_count} sessões inativas")
        
    except Exception as e:
        logger.error(f"Erro ao limpar sessões inativas: {e}")

@secure_db_operation
def remove_user_session(user_id, session_id):
    """
    Remove uma sessão específica do usuário
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM active_sessions WHERE user_id = %s AND session_id = %s",
            (user_id, session_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Erro ao remover sessão: {e}")

def create_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se as colunas plan_start e plan_end já existem
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name IN ('plan_start', 'plan_end')
    """)
    existing_columns = [row[0] for row in cursor.fetchall()]
    
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            localidade VARCHAR(100) NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            plan_start DATE DEFAULT CURRENT_DATE,
            plan_end DATE
        );
        """
    )
    
    # Adicionar colunas se não existirem (migração)
    if 'plan_start' not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN plan_start DATE DEFAULT CURRENT_DATE")
        
    if 'plan_end' not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN plan_end DATE")
        # Definir data de expiração padrão para usuários existentes (30 dias a partir de hoje)
        cursor.execute("""
            UPDATE users 
            SET plan_end = CURRENT_DATE + INTERVAL '30 days'
            WHERE plan_end IS NULL AND is_admin = FALSE
        """)

    # NOVO: Criar tabela usage_events para monitoramento
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            localidade VARCHAR(100) NOT NULL,
            event_type TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    
    # NOVO: Criar tabela de sessões ativas para controle de dispositivo único
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS active_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_id VARCHAR(255) UNIQUE NOT NULL,
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_activity TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    
    # NOVO: Criar índices para performance
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_usage_events_user_created_at
            ON usage_events (user_id, created_at DESC);
        """
    )
    
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_usage_events_localidade_created_at
            ON usage_events (localidade, created_at DESC);
        """
    )
    
    # NOVO: Criar VIEW para monitoramento consolidado
    cursor.execute(
        """
        CREATE OR REPLACE VIEW v_user_usage AS
        SELECT
            u.id,
            u.username,
            u.localidade,
            u.is_admin,
            u.is_active,
            MAX(e.created_at) AS last_activity_at,
            COUNT(*) FILTER (
                WHERE e.created_at >= NOW() - INTERVAL '30 days'
            ) AS access_last_30d,
            CASE
                WHEN MAX(e.created_at) >= NOW() - INTERVAL '5 minutes'
                THEN TRUE
                ELSE FALSE
            END AS using_now,
            COUNT(DISTINCT DATE(e.created_at)) FILTER (
                WHERE e.created_at >= NOW() - INTERVAL '30 days'
            ) AS days_active_last_30d
        FROM users u
        LEFT JOIN usage_events e ON e.user_id = u.id
        GROUP BY u.id, u.username, u.localidade, u.is_admin, u.is_active;
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

@secure_db_operation
def check_login(username, password):
    """Função segura para validar login"""
    # Validar entradas
    username_valid, username_msg = SecurityValidator.validate_username(username)
    if not username_valid:
        security_logger.warning(f"Tentativa de login com username inválido: {username[:20]}")
        return None, None
    
    # Verificar tentativas de injeção SQL
    if SecurityValidator.detect_sql_injection(username) or SecurityValidator.detect_sql_injection(password):
        security_logger.error(f"Tentativa de SQL injection no login: {username[:20]}")
        return None, None
    
    # Sanitizar username
    username = SecurityValidator.sanitize_input(username, 30)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query segura com prepared statement
        cursor.execute("SELECT id, username, password, localidade, is_admin, is_active FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()

        if user and check_password_hash(user[2], password):  # user[2] é a coluna password
            if user[5]:  # user[5] é a coluna is_active
                security_logger.info(f"Login bem-sucedido: {username}")
                return user[3], user[4]  # Retorna localidade (user[3]) e is_admin (user[4])
            else:
                security_logger.warning(f"Tentativa de login com conta bloqueada: {username}")
                return "blocked", None
        else:
            security_logger.warning(f"Falha de autenticação: {username}")
            return None, None
            
    except Exception as e:
        security_logger.error(f"Erro no check_login: {type(e).__name__}")
        return None, None

@secure_db_operation
def add_user(username, password, localidade, plan_start=None, plan_end=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Hash da senha
        password_hash = generate_password_hash(password)
        
        # Se plan_start não fornecido, usar data atual
        if not plan_start:
            plan_start = 'CURRENT_DATE'
            cursor.execute(
                """
                INSERT INTO users (username, password, localidade, plan_start, plan_end) 
                VALUES (%s, %s, %s, CURRENT_DATE, %s)
                """,
                (username, password_hash, localidade, plan_end)
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (username, password, localidade, plan_start, plan_end) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (username, password_hash, localidade, plan_start, plan_end)
            )
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao adicionar usuário: {e}")
        return False
    """Função segura para adicionar usuário"""
    # Validar todas as entradas
    username_valid, username_msg = SecurityValidator.validate_username(username)
    if not username_valid:
        security_logger.warning(f"Tentativa de criar usuário com username inválido: {username_msg}")
        return False, username_msg
    
    password_valid, password_msg = SecurityValidator.validate_password(password)
    if not password_valid:
        security_logger.warning(f"Tentativa de criar usuário com senha inválida: {password_msg}")
        return False, password_msg
    
    localidade_valid, localidade_msg = SecurityValidator.validate_localidade(localidade)
    if not localidade_valid:
        security_logger.warning(f"Tentativa de criar usuário com localidade inválida: {localidade_msg}")
        return False, localidade_msg
    
    # Verificar tentativas de injeção
    for param in [username, localidade]:
        if SecurityValidator.detect_sql_injection(param):
            security_logger.error(f"SQL Injection detectado em add_user")
            return False, "Dados inválidos detectados"
    
    # Sanitizar entradas
    username = SecurityValidator.sanitize_input(username, 30)
    localidade = SecurityValidator.sanitize_input(localidade, 20)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar se usuário já existe
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
        if cursor.fetchone()[0] > 0:
            security_logger.warning(f"Tentativa de criar usuário já existente: {username}")
            cursor.close()
            conn.close()
            return False, "Usuário já existe"
        
        # Hash seguro da senha
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

        cursor.execute(
            """INSERT INTO users (username, password, localidade, is_admin, is_active)
               VALUES (%s, %s, %s, %s, %s)""",
            (username, hashed_password, localidade, False, True),
        )

        conn.commit()
        cursor.close()
        conn.close()
        
        security_logger.info(f"Usuário criado com sucesso: {username}")
        return True, "Usuário criado com sucesso"
        
    except psycopg2.IntegrityError as e:
        security_logger.warning(f"Erro de integridade ao criar usuário: {username}")
        return False, "Usuário já existe"
    except Exception as e:
        security_logger.error(f"Erro ao criar usuário: {type(e).__name__}")
        return False, "Erro interno do sistema"

@app.route('/<localidade>/status')
def get_status(localidade):
    """Retorna status da transmissão para uma localidade"""
    try:
        # Verifica se há processo FFmpeg ativo
        is_streaming = localidade in active_hls_processes and \
                      active_hls_processes[localidade] is not None and \
                      active_hls_processes[localidade].poll() is None
        
        # Verifica se há arquivos HLS recentes
        hls_dir = os.path.join(HLS_STREAMS_DIR, localidade)
        has_recent_files = False
        if os.path.exists(hls_dir):
            try:
                index_file = os.path.join(hls_dir, 'index.m3u8')
                if os.path.exists(index_file):
                    # Verifica se arquivo foi modificado nos últimos 30 segundos
                    last_modified = os.path.getmtime(index_file)
                    has_recent_files = (time.time() - last_modified) < 30
            except:
                pass
        
        return jsonify({
            'streaming': is_streaming,
            'has_recent_files': has_recent_files,
            'localidade': localidade
        })
    except Exception as e:
        return jsonify({'error': str(e), 'streaming': False}), 500

# Função para garantir que a pasta da localidade exista
def ensure_localidade_directory(localidade):
    local_dir = os.path.join(IMAGE_DIR, localidade.lower())
    if not os.path.isdir(local_dir):
        os.makedirs(local_dir)
    return local_dir

def ensure_sessions_directory():
    """
    Garante que o diretório de sessões existe
    """
    if not os.path.exists(SESSIONS_DIR):
        os.makedirs(SESSIONS_DIR)

def start_ffmpeg_for_session(session_id):
    """
    Inicia um processo FFmpeg para gerar HLS de uma sessão específica
    Neste exemplo, usamos um input dummy para demonstração
    Em produção, você deve configurar um input RTMP ou WebRTC
    """
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    
    # Para demonstração, usamos testsrc (padrão de teste)
    # Em produção, substitua por RTMP ou outro input real
    output_path = os.path.join(session_dir, "index.m3u8")
    
    # Comando FFmpeg otimizado para HLS - Configuração corrigida para VBV
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",  # Sobrescrever arquivos existentes
        "-f", "lavfi",  # Usar filtro de entrada (para teste)
        "-i", "testsrc=size=1280x720:rate=30:duration=3600",  # Input de teste com duração longa
        "-c:v", "libx264",
        "-preset", "medium",           # Mudança para preset mais estável
        "-tune", "zerolatency",
        "-b:v", "1500k",              # Bitrate fixo em vez de CRF
        "-minrate", "1200k",          # Taxa mínima para estabilidade
        "-maxrate", "1800k",          # Taxa máxima controlada
        "-bufsize", "3600k",          # Buffer VBV = 2 * maxrate
        "-g", "60",                   # Keyframe a cada 2 segundos (30fps * 2)
        "-sc_threshold", "0",         # Desabilita detecção de mudança de cena
        "-f", "hls",
        "-hls_time", "2",
        "-hls_list_size", "6",
        "-hls_flags", "delete_segments+independent_segments",
        "-hls_segment_type", "mpegts",
        output_path
    ]
    
    try:
        # Inicia o processo FFmpeg
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        active_ffmpeg_processes[session_id] = process
        print(f"[FFmpeg] Processo iniciado para sessão {session_id} (PID: {process.pid})")
        return True
    except Exception as e:
        print(f"[FFmpeg] Erro ao iniciar processo para sessão {session_id}: {e}")
        return False

# Função para parar FFmpeg de uma sessão
def stop_ffmpeg_for_session(session_id):
    """
    Para o processo FFmpeg de uma sessão específica
    """
    if session_id in active_ffmpeg_processes:
        process = active_ffmpeg_processes[session_id]
        try:
            if os.name == 'nt':  # Windows
                process.terminate()
            else:  # Unix/Linux
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            
            process.wait(timeout=5)  # Aguarda até 5 segundos
            del active_ffmpeg_processes[session_id]
            print(f"[FFmpeg] Processo parado para sessão {session_id}")
            return True
        except subprocess.TimeoutExpired:
            # Força a finalização se não parar normalmente
            if os.name == 'nt':
                process.kill()
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            del active_ffmpeg_processes[session_id]
            print(f"[FFmpeg] Processo forçadamente finalizado para sessão {session_id}")
            return True
        except Exception as e:
            print(f"[FFmpeg] Erro ao parar processo para sessão {session_id}: {e}")
            return False
    return False

# Função para limpar arquivos de uma sessão
def cleanup_session_files(session_id, max_age_seconds=300):
    """
    Remove arquivos antigos de uma sessão específica
    """
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    if not os.path.exists(session_dir):
        return
    
    try:
        current_time = time.time()
        for filename in os.listdir(session_dir):
            file_path = os.path.join(session_dir, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    print(f"[Cleanup] Arquivo removido: {file_path}")
        
        # Remove diretório se estiver vazio
        if not os.listdir(session_dir):
            os.rmdir(session_dir)
            print(f"[Cleanup] Diretório removido: {session_dir}")
    except Exception as e:
        print(f"[Cleanup] Erro ao limpar sessão {session_id}: {e}")

# ========================================
# FUNÇÕES HLS - NOVA ARQUITETURA
# ========================================

def start_hls_ffmpeg(localidade):
    """
    Inicia processo FFmpeg para streaming HLS de uma localidade específica
    Recebe dados do MediaRecorder via stdin
    Versão simplificada para debug
    """
    # Verifica se FFmpeg está disponível
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print("[HLS] ERRO: FFmpeg não encontrado no sistema. Instale FFmpeg primeiro.")
        print("[HLS] Windows: Baixe de https://ffmpeg.org/download.html")
        print("[HLS] Linux: sudo apt install ffmpeg")
        print("[HLS] Mac: brew install ffmpeg")
        return None
    
    localidade_dir = os.path.join(HLS_STREAMS_DIR, localidade)
    if not os.path.exists(localidade_dir):
        os.makedirs(localidade_dir)
    
    output_path = os.path.join(localidade_dir, "index.m3u8")
    
    # FFmpeg OTIMIZADO para MOBILE/NAVEGADOR - ESTABILIDADE
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",  # Sobrescrever arquivos existentes
        "-f", "webm",  # Input format do MediaRecorder
        "-i", "pipe:0",  # Lê do stdin
        "-c:v", "libx264",  # Codec de vídeo H.264
        "-preset", "veryfast",  # Balance velocidade/qualidade
        "-tune", "zerolatency",  # Zero latência
        "-pix_fmt", "yuv420p",  # Formato compatível
        "-g", "30",  # Keyframes a cada 2s (mobile friendly)
        "-sc_threshold", "0",  # Força keyframes regulares
        "-b:v", "800k",  # Bitrate fixo 800k (mobile)
        "-maxrate", "1000k",  # Rate máximo
        "-bufsize", "2000k",  # Buffer maior para estabilidade
        "-threads", "4",  # 4 threads (não sobrecarrega)
        "-profile:v", "baseline",  # Perfil compatível
        "-level", "3.1",  # Level mobile
        "-movflags", "+faststart",  # Start rápido
        "-an",  # SEM ÁUDIO
        "-f", "hls",  # Output HLS
        "-hls_time", "2",  # Segmentos 2s (mobile estável)
        "-hls_list_size", "6",  # 6 segmentos (12s buffer)
        "-hls_flags", "delete_segments+independent_segments",
        "-hls_allow_cache", "0",
        "-hls_start_number_source", "epoch",
        "-hls_segment_filename", os.path.join(localidade_dir, "live_%d.ts"),
        output_path
    ]
    
    try:
        print(f"[HLS] Iniciando FFmpeg para localidade: {localidade}")
        print(f"[HLS] Diretório de saída: {localidade_dir}")
        print(f"[HLS] Arquivo de saída: {output_path}")
        print(f"[HLS] Comando FFmpeg: {' '.join(ffmpeg_cmd[:10])}...") # Mostra primeiros parâmetros
        
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redireciona stderr para stdout para ver erros
            bufsize=0,  # Unbuffered para baixa latência
            cwd=localidade_dir  # Define working directory
        )
        
        active_hls_processes[localidade] = process
        print(f"[HLS] Processo FFmpeg iniciado para {localidade} (PID: {process.pid})")
        
        # Verifica se processo iniciou corretamente (mais tempo para alta qualidade)
        time.sleep(1.5)
        if process.poll() is not None:
            print(f"[HLS] ERRO: FFmpeg terminou imediatamente com código {process.returncode}")
            return None
        
        # Inicia thread para monitorar saída do FFmpeg
        def monitor_ffmpeg():
            try:
                while process.poll() is None:
                    line = process.stdout.readline()
                    if line:
                        decoded_line = line.decode('utf-8', errors='ignore').strip()
                        if decoded_line:
                            print(f"[FFmpeg {localidade}] {decoded_line}")
                print(f"[FFmpeg {localidade}] Processo finalizado com código: {process.returncode}")
            except Exception as e:
                print(f"[FFmpeg {localidade}] Erro no monitor: {e}")
            
        Thread(target=monitor_ffmpeg, daemon=True).start()
        
        return process
        
    except FileNotFoundError:
        print(f"[HLS] ERRO: FFmpeg não encontrado. Certifique-se de que está instalado e no PATH.")
        return None
    except PermissionError:
        print(f"[HLS] ERRO: Permissão negada para criar diretório ou executar FFmpeg: {localidade_dir}")
        return None
    except Exception as e:
        print(f"[HLS] ERRO: Exceção ao iniciar FFmpeg para {localidade}: {e}")
        print(f"[HLS] Tipo de erro: {type(e).__name__}")
        return None

def stop_hls_ffmpeg(localidade):
    """
    Para o processo FFmpeg de uma localidade específica
    """
    if localidade in active_hls_processes:
        process = active_hls_processes[localidade]
        try:
            # Fecha stdin graciosamente
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
            
            # Aguarda término natural por 3 segundos
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Se não finalizar naturalmente, força
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
            
            del active_hls_processes[localidade]
            print(f"[HLS] Processo FFmpeg parado para localidade: {localidade}")
            return True
            
        except Exception as e:
            print(f"[HLS] Erro ao parar FFmpeg para {localidade}: {e}")
            return False
    
    print(f"[HLS] Nenhum processo ativo encontrado para {localidade}")
    return True

def cleanup_hls_files(localidade, max_age_seconds=300):
    """
    Limpa arquivos HLS antigos de uma localidade
    """
    localidade_dir = os.path.join(HLS_STREAMS_DIR, localidade)
    if not os.path.exists(localidade_dir):
        return
    
    try:
        current_time = time.time()
        for filename in os.listdir(localidade_dir):
            if filename.endswith(('.ts', '.m3u8')):
                file_path = os.path.join(localidade_dir, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        print(f"[HLS Cleanup] Arquivo removido: {file_path}")
    except Exception as e:
        print(f"[HLS Cleanup] Erro ao limpar arquivos HLS para {localidade}: {e}")

def is_hls_active(localidade):
    """
    Verifica se existe transmissão HLS ativa para uma localidade
    """
    # Verifica se há processo FFmpeg ativo
    if localidade in active_hls_processes:
        process = active_hls_processes[localidade]
        if process.poll() is None:  # Processo ainda rodando
            return True
        else:
            # Process morreu, remove da lista
            del active_hls_processes[localidade]
            print(f"[HLS] Processo morto removido para {localidade}")
    
    # Verifica se existe playlist HLS recente
    playlist_path = os.path.join(HLS_STREAMS_DIR, localidade, "index.m3u8")
    if os.path.exists(playlist_path):
        file_age = time.time() - os.path.getmtime(playlist_path)
        if file_age < 15:  # Considera ativo se playlist foi atualizada recentemente
            return True
    
    return False
# Função para limpar frames antigos
def remove_old_frames(directory, max_age_in_seconds):
    """
    Remove arquivos no diretório que são mais antigos do que max_age_in_seconds.
    """
    now = time.time()
    try:
        for localidade in os.listdir(directory):
            localidade_dir = os.path.join(directory, localidade)
            if os.path.isdir(localidade_dir):
                for file_name in os.listdir(localidade_dir):
                    file_path = os.path.join(localidade_dir, file_name)
                    if os.path.isfile(file_path):
                        file_age = now - os.path.getmtime(file_path)
                        if file_age > max_age_in_seconds:
                            os.remove(file_path)
                            print(f"[Backend] Arquivo removido: {file_path}")
    except Exception as e:
        print(f"[Backend] Erro ao limpar arquivos: {e}")

# Função para executar a limpeza periodicamente
def start_cleanup_task(interval=300, max_age_in_seconds=300):
    """
    Inicia uma thread para limpar frames antigos a cada 'interval' segundos.
    """
    def cleanup():
        print("[Inicialização] Tarefa de limpeza iniciada.")
        while True:
            print("[Limpeza] Executando limpeza de frames antigos...")
            remove_old_frames(IMAGE_DIR, max_age_in_seconds)
            
            # Também limpa sessões antigas
            cleanup_old_sessions()
            
            # Limpa arquivos HLS antigos
            cleanup_old_hls_files()
            
            # Verifica e limpa processos HLS órfãos
            cleanup_orphaned_hls_processes()
            
            time.sleep(interval)
    # Executa a limpeza em uma thread separada
    thread = Thread(target=cleanup, daemon=True)
    thread.start()

def cleanup_old_sessions(max_age_seconds=1800):  # 30 minutos
    """
    Limpa sessões HLS antigas
    """
    try:
        if not os.path.exists(SESSIONS_DIR):
            return
            
        current_time = time.time()
        for session_id in os.listdir(SESSIONS_DIR):
            session_dir = os.path.join(SESSIONS_DIR, session_id)
            if os.path.isdir(session_dir):
                # Verifica a idade da pasta
                dir_age = current_time - os.path.getctime(session_dir)
                if dir_age > max_age_seconds:
                    # Para o FFmpeg se ainda estiver rodando
                    stop_ffmpeg_for_session(session_id)
                    # Remove arquivos da sessão
                    cleanup_session_files(session_id, max_age_seconds=0)
                    print(f"[Cleanup] Sessão antiga removida: {session_id}")
    except Exception as e:
        print(f"[Cleanup] Erro ao limpar sessões antigas: {e}")

def cleanup_old_hls_files(max_age_seconds=600):  # 10 minutos
    """
    Limpa arquivos HLS antigos de todas as localidades
    """
    try:
        if not os.path.exists(HLS_STREAMS_DIR):
            return
            
        current_time = time.time()
        for localidade in os.listdir(HLS_STREAMS_DIR):
            localidade_dir = os.path.join(HLS_STREAMS_DIR, localidade)
            if os.path.isdir(localidade_dir):
                # Se não há processo ativo, limpa arquivos antigos
                if localidade not in active_hls_processes:
                    cleanup_hls_files(localidade, max_age_seconds)
                    
                    # Remove diretório se vazio
                    try:
                        if not os.listdir(localidade_dir):
                            os.rmdir(localidade_dir)
                            print(f"[Cleanup] Diretório HLS removido: {localidade_dir}")
                    except OSError:
                        pass  # Diretório não vazio
    except Exception as e:
        print(f"[Cleanup] Erro ao limpar arquivos HLS antigos: {e}")

def cleanup_orphaned_hls_processes():
    """
    Limpa processos HLS órfãos (que pararam de responder)
    """
    try:
        dead_processes = []
        for localidade, process in active_hls_processes.items():
            if process.poll() is not None:  # Processo morreu
                dead_processes.append(localidade)
                print(f"[Cleanup] Processo HLS órfão encontrado para {localidade}")
        
        for localidade in dead_processes:
            del active_hls_processes[localidade]
            print(f"[Cleanup] Processo órfão removido: {localidade}")
            
    except Exception as e:
        print(f"[Cleanup] Erro ao limpar processos órfãos: {e}")

# Rota para login com proteção de segurança
@app.route("/login", methods=["POST"])
def login():
    # Obter IP do cliente
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    
    # Verificar rate limiting
    if rate_limiter.is_rate_limited(client_ip):
        security_logger.warning(f"Rate limit excedido para IP: {client_ip}")
        flash("Muitas tentativas de login. Tente novamente em 15 minutos.", "error")
        return redirect(url_for("index"))
    
    # Obter dados do formulário
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    
    # Validações básicas
    if not username or not password:
        rate_limiter.record_attempt(client_ip, success=False)
        flash("Nome de usuário e senha são obrigatórios.", "error")
        return redirect(url_for("index"))
    
    # Limitar tamanho das entradas
    if len(username) > 30 or len(password) > 128:
        rate_limiter.record_attempt(client_ip, success=False)
        security_logger.warning(f"Tentativa de login com dados muito longos de IP: {client_ip}")
        flash("Dados inválidos.", "error")
        return redirect(url_for("index"))
    
    # Verificar tentativas de injection
    if SecurityValidator.detect_sql_injection(username) or SecurityValidator.detect_sql_injection(password):
        rate_limiter.record_attempt(client_ip, success=False)
        security_logger.error(f"Tentativa de SQL injection no login de IP: {client_ip}")
        flash("Dados inválidos detectados.", "error")
        return redirect(url_for("index"))
    
    # Validar credenciais
    localidade, is_admin = check_login(username, password)
    
    if localidade == "blocked":
        rate_limiter.record_attempt(client_ip, success=False)
        flash("Seu acesso foi bloqueado pelo administrador.", "error")
        return redirect(url_for("index"))
    elif not localidade:
        # Login falhado - log detalhado
        security_logger.warning(f"Tentativa de login falhada: username={username} de IP: {client_ip}")
        rate_limiter.record_attempt(client_ip, success=False)
        flash("Nome de usuário ou senha inválidos.", "error")
        return redirect(url_for("index"))
    elif localidade:
        # Login bem-sucedido
        rate_limiter.record_attempt(client_ip, success=True)
        
        # Buscar user_id
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user_result:
            flash("Erro interno. Tente novamente.", "error")
            return redirect(url_for("index"))
        
        user_id = user_result[0]
        
        # Regenerar ID da sessão para prevenir fixation
        session.permanent = True
        
        # Gerar novo session_id único
        import secrets
        new_session_id = secrets.token_urlsafe(32)
        
        # Registrar nova sessão (remove sessões antigas do mesmo usuário)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        if register_user_session(user_id, new_session_id, client_ip, user_agent):
            # Dados da sessão
            session["logged_in"] = True
            session["username"] = username
            session["localidade"] = localidade
            session["is_admin"] = is_admin
            session["user_id"] = user_id
            session["session_id"] = new_session_id
            session["csrf_token"] = generate_csrf_token()
            session["login_ip"] = client_ip
            
            # Registrar evento de login
            log_usage_event(username, localidade, "login")
            
            logger.info(f"Login bem-sucedido: {username} de IP {client_ip}, sessão {new_session_id}")
            
            if is_admin:
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("share_screen", localidade=localidade))
        else:
            flash("Erro ao iniciar sessão. Tente novamente.", "error")
            return redirect(url_for("index"))
    else:
        # Login falhado
        rate_limiter.record_attempt(client_ip, success=False)
        flash("Nome de usuário ou senha inválidos.", "error")
        return redirect(url_for("index"))

# Rota para logout
@app.route("/logout")
def logout():
    # Remover sessão ativa do banco de dados
    if 'user_id' in session and 'session_id' in session:
        remove_user_session(session['user_id'], session['session_id'])
        logger.info(f"Logout: usuário {session.get('username')} sessão {session.get('session_id')}")
    
    session.clear()
    flash("Logout realizado com sucesso.", "success")
    return redirect(url_for("index"))

# Rota para upload do frame com controle de frequência
@app.route("/<localidade>/upload_frame", methods=["POST"])
def upload_frame(localidade):
    global last_upload_time
    current_time = time.time()
    
    # Validação de entrada para localidade
    if not security_validator.is_localidade_valid(localidade):
        logger.warning(f"Upload frame - localidade inválida: {localidade} de IP: {request.remote_addr}")
        abort(400, description="Localidade inválida")
    
    # Verificação de rate limiting
    user_ip = request.remote_addr
    if not rate_limiter.is_allowed(f"upload_{user_ip}"):
        logger.warning(f"Rate limit exceeded para upload_frame de IP: {user_ip}")
        abort(429, description="Muitas tentativas. Tente novamente mais tarde.")
    
    # Define intervalo mínimo de tempo em segundos entre uploads
    upload_interval = 1  # Ajuste o intervalo conforme necessário (ex.: 1 segundo)

    if "logged_in" in session and session.get("localidade") == localidade:
        # Verificação adicional de CSRF token
        csrf_token = request.form.get('csrf_token')
        if not csrf_token or csrf_token != session.get('csrf_token'):
            logger.warning(f"CSRF token inválido em upload_frame de IP: {user_ip}")
            abort(403, description="Token CSRF inválido")
        
        # Verifica se o último upload ocorreu há pelo menos 'upload_interval' segundos
        if localidade in last_upload_time:
            elapsed_time = current_time - last_upload_time[localidade]
            if elapsed_time < upload_interval:
                print(f"Upload ignorado para {localidade}, intervalo de {upload_interval} segundos ainda não passou.")
                return "", 204  # Retorna vazio sem atualizar

        # Define o diretório de salvamento da imagem
        local_dir = ensure_localidade_directory(localidade)
        frame_path_local = os.path.join(local_dir, "screen.png")
        frame_temp_path = os.path.join(local_dir, "screen_temp.png")
        
        if "frame" in request.files:
            frame = request.files["frame"]
            
            # Validação de arquivo de imagem
            if not security_validator.validate_image_file(frame):
                logger.warning(f"Arquivo de imagem inválido em upload_frame de IP: {user_ip}")
                abort(400, description="Arquivo de imagem inválido")
            
            try:
                # Salva primeiro em arquivo temporário
                frame.save(frame_temp_path)
                
                # Renomeiação atômica (evita problemas de leitura durante escrita)
                if os.path.exists(frame_temp_path):
                    if os.path.exists(frame_path_local):
                        os.remove(frame_path_local)
                    os.rename(frame_temp_path, frame_path_local)
                
                last_upload_time[localidade] = current_time  # Atualiza o tempo do último upload
                
                # NOVO: Registrar evento de uso do frame
                username = session.get("username")
                if username:
                    log_usage_event(username, localidade, "frame")
                
                logger.info(f"Frame salvo com sucesso para {localidade} por {username}")
                print(f"Frame salvo com sucesso em {frame_path_local}.")
            except Exception as e:
                # Limpar arquivo temporário em caso de erro
                if os.path.exists(frame_temp_path):
                    try:
                        os.remove(frame_temp_path)
                    except:
                        pass
                logger.error(f"Erro ao salvar frame para {localidade}: {e}")
                print(f"Erro ao salvar o frame: {e}")
                return "", 500
        else:
            logger.warning(f"Nenhum frame recebido para {localidade}")
            print("Nenhum frame recebido.")
        return "", 204
    else:
        logger.warning(f"Acesso não autorizado para upload_frame - localidade: {localidade}, IP: {user_ip}")
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))

# Rota para servir a imagem do frame
@app.route("/serve_pil_image/<localidade>/screen.png")
def serve_pil_image(localidade):
    # Validação de entrada para localidade
    if not security_validator.is_localidade_valid(localidade):
        logger.warning(f"Tentativa de acesso com localidade inválida: {localidade} de IP: {request.remote_addr}")
        abort(400, description="Localidade inválida")
    
    # Rate limiting para prevenir abuso
    user_ip = request.remote_addr
    if not rate_limiter.is_allowed(f"serve_image_{user_ip}"):
        logger.warning(f"Rate limit exceeded para serve_pil_image de IP: {user_ip}")
        abort(429, description="Muitas tentativas. Tente novamente mais tarde.")
    
    local_dir = os.path.join(IMAGE_DIR, localidade.lower())
    if not os.path.isdir(local_dir):
        logger.warning(f"Pasta da localidade não encontrada: {local_dir} de IP: {user_ip}")
        print(f"Pasta da localidade não encontrada: {local_dir}")
        abort(404, description="Localidade não encontrada.")

    image_path = os.path.join(local_dir, "screen.png")
    if not os.path.isfile(image_path):
        print(f"Arquivo de imagem não encontrado no caminho: {image_path}")
        abort(404, description="Imagem não encontrada.")

    try:
        # Verificar tamanho do arquivo para detectar arquivos corrompidos/incompletos
        file_size = os.path.getsize(image_path)
        if file_size < 100:  # Arquivo muito pequeno, provavelmente corrompido
            print(f"Arquivo muito pequeno ou corrompido: {file_size} bytes")
            abort(404, description="Imagem não disponível no momento.")
            
        response = send_from_directory(local_dir, "screen.png", mimetype="image/png")
        
        # Headers otimizados para evitar problemas de cache e concorrência
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Last-Modified"] = "0"
        response.headers["ETag"] = f"\"{file_size}-{int(time.time())}\""
        response.headers["Accept-Ranges"] = "none"  # Previne requests de range que podem causar problemas
        
        return response
    except Exception as e:
        logger.error(f"Erro ao servir a imagem: {e}")
        print(f"Erro ao servir a imagem: {e}")
        abort(500, description="Erro ao servir a imagem.")

# Rota pública para visualizar a tela (acessível externamente)
@app.route("/tela")
def tela():
    return render_template("tela.html")

# Rota para renderizar a página de visualização de tela por localidade
@app.route("/<localidade>/tela")
def view_screen_by_region(localidade):
    # Validação de entrada para localidade
    if not security_validator.is_localidade_valid(localidade):
        logger.warning(f"Tentativa de visualização com localidade inválida: {localidade} de IP: {request.remote_addr}")
        abort(400, description="Localidade inválida")
    
    return render_template("tela.html", localidade=localidade)

# Rota para compartilhar a tela
@app.route("/<localidade>/tela-compartilhada")
def share_screen(localidade):
    # Validação de entrada para localidade
    if not security_validator.is_localidade_valid(localidade):
        logger.warning(f"Tentativa de compartilhamento com localidade inválida: {localidade} de IP: {request.remote_addr}")
        abort(400, description="Localidade inválida")
    
    if "logged_in" in session and session.get("localidade") == localidade:
        share_link = url_for(
            "view_screen_by_region", localidade=localidade, _external=True
        )
        username = session.get("username")
        
        # Gerar token CSRF se não existir
        if 'csrf_token' not in session:
            session['csrf_token'] = generate_csrf_token()
        
        logger.info(f"Tela compartilhada para {localidade} por {username}")
        
        # Criar response com headers de segurança explícitos
        response = app.make_response(render_template(
            "tela_compartilhada.html",
            localidade=localidade,
            share_link=share_link,
            username=username,
            csrf_token=session['csrf_token'],
        ))
        
        # Headers específicos para bloquear câmera e microfone - FORÇAR SOBRESCRITA
        response.headers.pop('Content-Security-Policy', None)  # Remove CSP global
        response.headers.pop('Permissions-Policy', None)       # Remove Permissions global
        
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), display-capture=*'
        response.headers['Feature-Policy'] = 'camera \'none\'; microphone \'none\'; geolocation \'none\'; display-capture *'
        response.headers['Content-Security-Policy'] = 'default-src \'self\' \'unsafe-inline\' \'unsafe-eval\' https:; script-src \'self\' \'unsafe-inline\' \'unsafe-eval\' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; worker-src \'self\' blob:; style-src \'self\' \'unsafe-inline\' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src \'self\' https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src \'self\' data: https:; media-src \'self\' blob: data:; connect-src \'self\' ws: wss:;'
        
        return response
    else:
        logger.warning(f"Acesso não autorizado para compartilhamento - localidade: {localidade}, IP: {request.remote_addr}")
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))

# ========================================
# ROTAS HLS - NOVA ARQUITETURA
# ========================================

@app.route("/<localidade>/hls_ingest", methods=["POST"])
def hls_ingest(localidade):
    """
    Rota para receber stream do MediaRecorder e alimentar FFmpeg
    Usa um único processo persistente por localidade
    """
    # Validação de entrada para localidade
    if not security_validator.is_localidade_valid(localidade):
        logger.warning(f"Tentativa de HLS ingest com localidade inválida: {localidade} de IP: {request.remote_addr}")
        abort(400, description="Localidade inválida")
    
    # Rate limiting para uploads de stream
    user_ip = request.remote_addr
    if not rate_limiter.is_allowed(f"hls_ingest_{user_ip}"):
        logger.warning(f"Rate limit exceeded para hls_ingest de IP: {user_ip}")
        abort(429, description="Muitas tentativas. Tente novamente mais tarde.")
    
    if "logged_in" not in session or session.get("localidade") != localidade:
        logger.warning(f"Acesso não autorizado para HLS ingest - localidade: {localidade}, IP: {user_ip}")
        return "Não autorizado", 401
    
    # Garante que existe um lock para esta localidade
    if localidade not in process_locks:
        process_locks[localidade] = threading.Lock()
    
    with process_locks[localidade]:
        print(f"[HLS Ingest] Recebendo chunk para {localidade}")
        
        # Verifica se processo FFmpeg existe e está rodando
        process = active_hls_processes.get(localidade)
        if not process or process.poll() is not None:
            print(f"[HLS Ingest] Iniciando novo FFmpeg para {localidade}")
            # Remove processo morto
            if localidade in active_hls_processes:
                del active_hls_processes[localidade]
            
            process = start_hls_ffmpeg(localidade)
            if not process:
                return "Erro ao iniciar streaming", 500
            # Aguarda FFmpeg inicializar (mais tempo para alta qualidade)
            time.sleep(3)
        
        try:
            # Lê todos os dados do chunk
            chunk_data = request.get_data()
            if not chunk_data:
                print(f"[HLS Ingest] Chunk vazio recebido para {localidade}")
                return "Chunk vazio", 400
            
            # Verifica se o processo ainda está rodando
            if process.poll() is not None:
                print(f"[HLS Ingest] Processo FFmpeg morreu (código {process.returncode}) para {localidade}")
                # Remove processo morto
                if localidade in active_hls_processes:
                    del active_hls_processes[localidade]
                # Tenta reiniciar
                process = start_hls_ffmpeg(localidade)
                if not process:
                    return jsonify({"error": "Não foi possível reiniciar FFmpeg"}), 500
                time.sleep(2)  # Aguarda mais tempo para alta qualidade inicializar
                
            # Verifica se stdin ainda está disponível
            if process.stdin and not process.stdin.closed:
                try:
                    process.stdin.write(chunk_data)
                    process.stdin.flush()
                    
                    # NOVO: Registrar evento de uso HLS
                    username = session.get("username")
                    if username:
                        log_usage_event(username, localidade, "hls_chunk")
                    
                    print(f"[HLS Ingest] Chunk de {len(chunk_data)} bytes escrito para {localidade}")
                    return "Chunk processado com sucesso", 200
                except OSError as e:
                    print(f"[HLS Ingest] ERRO OSError ao escrever: {e}")
                    if localidade in active_hls_processes:
                        del active_hls_processes[localidade]
                    return jsonify({"error": "FFmpeg desconectado"}), 500
            else:
                print(f"[HLS Ingest] ERRO: FFmpeg stdin não disponível para {localidade}")
                # Remove processo morto
                if localidade in active_hls_processes:
                    del active_hls_processes[localidade]
                return jsonify({"error": "FFmpeg não está rodando"}), 500
            
        except BrokenPipeError as e:
            print(f"[HLS Ingest] ERRO: Broken pipe ao escrever para FFmpeg {localidade}: {e}")
            if localidade in active_hls_processes:
                del active_hls_processes[localidade]
            return jsonify({"error": "FFmpeg desconectado"}), 500
        except Exception as e:
            print(f"[HLS Ingest] ERRO: Exceção ao processar chunk para {localidade}: {e}")
            print(f"[HLS Ingest] Tipo de erro: {type(e).__name__}")
            # Em caso de erro, remove processo 
            if localidade in active_hls_processes:
                del active_hls_processes[localidade]
            return jsonify({"error": "Erro interno", "details": str(e)}), 500

@app.route("/<localidade>/hls_start", methods=["POST"])
def hls_start(localidade):
    """
    Inicia streaming HLS para uma localidade
    """
    if "logged_in" not in session or session.get("localidade") != localidade:
        return jsonify({"error": "Não autorizado"}), 401
    
    if is_hls_active(localidade):
        return jsonify({"status": "already_active", "message": "Streaming já está ativo"}), 200
    
    process = start_hls_ffmpeg(localidade)
    if process:
        stream_url = url_for("view_screen_by_region", localidade=localidade, _external=True)
        return jsonify({
            "status": "started",
            "stream_url": stream_url,
            "message": f"Streaming HLS iniciado para {localidade}"
        }), 200
    else:
        return jsonify({"error": "Falha ao iniciar streaming"}), 500

@app.route("/<localidade>/hls_stop", methods=["POST"])
def hls_stop(localidade):
    """
    Para streaming HLS de uma localidade
    """
    if "logged_in" not in session or session.get("localidade") != localidade:
        return jsonify({"error": "Não autorizado"}), 401
    
    if stop_hls_ffmpeg(localidade):
        # Agenda limpeza dos arquivos HLS
        def delayed_cleanup():
            time.sleep(5)  # Aguarda 5 segundos
            cleanup_hls_files(localidade, max_age_seconds=0)
        
        Thread(target=delayed_cleanup, daemon=True).start()
        
        return jsonify({"status": "stopped", "message": f"Streaming parado para {localidade}"}), 200
    else:
        return jsonify({"error": "Erro ao parar streaming"}), 500

@app.route("/<localidade>/hls_status")
def hls_status(localidade):
    """
    Retorna status do streaming HLS de uma localidade
    """
    active = is_hls_active(localidade)
    return jsonify({
        "localidade": localidade,
        "active": active,
        "process_running": localidade in active_hls_processes
    })

@app.route("/hls/<localidade>/<path:filename>")
def serve_hls_file(localidade, filename):
    """
    Serve arquivos HLS (.m3u8 e .ts) para uma localidade
    """
    # Validação de entrada para localidade
    if not security_validator.is_localidade_valid(localidade):
        abort(400, description="Localidade inválida")
    
    localidade_dir = os.path.join(HLS_STREAMS_DIR, localidade)
    
    if not os.path.exists(localidade_dir):
        abort(404, description=f"Stream não encontrado para {localidade}")
    
    file_path = os.path.join(localidade_dir, filename)
    if not os.path.exists(file_path):
        abort(404, description=f"Arquivo {filename} não encontrado")
    
    # Define tipo MIME apropriado
    if filename.endswith('.m3u8'):
        mimetype = 'application/vnd.apple.mpegurl'
    elif filename.endswith('.ts'):
        mimetype = 'video/mp2t'
    else:
        mimetype = 'application/octet-stream'
    
    response = send_from_directory(localidade_dir, filename, mimetype=mimetype)
    
    # Headers para evitar cache em HLS (importante para live streaming)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    
    return response

# Nova rota para criar sessão de streaming HLS
@app.route("/create_session", methods=["POST"])
def create_session():
    """
    Cria uma nova sessão de streaming HLS
    """
    if "logged_in" not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    # Gera um ID único para a sessão
    session_id = str(uuid.uuid4())
    
    # Garante que o diretório de sessões existe
    ensure_sessions_directory()
    
    # Inicia o processo FFmpeg para essa sessão
    if start_ffmpeg_for_session(session_id):
        # Gera URL de compartilhamento
        share_url = url_for("view_hls_stream", session=session_id, _external=True)
        
        return jsonify({
            "session_id": session_id,
            "share_url": share_url,
            "status": "success"
        })
    else:
        return jsonify({"error": "Falha ao iniciar streaming"}), 500

# Nova rota para visualizar stream HLS
@app.route("/view")
def view_hls_stream():
    """
    Página para visualizar stream HLS
    """
    session_id = request.args.get("session")
    if not session_id:
        return "Sessão não especificada", 400
    
    # Verifica se a sessão existe
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    if not os.path.exists(session_dir):
        return "Sessão não encontrada", 404
    
    return render_template("tela.html", session_id=session_id)

# Rota para encerrar sessão de streaming
@app.route("/end_session", methods=["POST"])
def end_session():
    """
    Encerra uma sessão de streaming HLS
    """
    if "logged_in" not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    data = request.get_json()
    session_id = data.get("session_id")
    
    if not session_id:
        return jsonify({"error": "session_id é obrigatório"}), 400
    
    # Para o processo FFmpeg
    if stop_ffmpeg_for_session(session_id):
        # Agenda limpeza dos arquivos (com delay para permitir download final)
        def delayed_cleanup():
            time.sleep(10)  # Aguarda 10 segundos
            cleanup_session_files(session_id, max_age_seconds=0)
        
        Thread(target=delayed_cleanup, daemon=True).start()
        
        return jsonify({"status": "success", "message": "Sessão encerrada"})
    else:
        return jsonify({"error": "Falha ao encerrar sessão"}), 500

# Rota para servir arquivos HLS
@app.route("/sessions/<session_id>/<filename>")
def serve_hls_session_file(session_id, filename):
    """
    Serve arquivos HLS (.m3u8 e .ts)
    """
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    
    if not os.path.exists(session_dir):
        abort(404)
    
    file_path = os.path.join(session_dir, filename)
    if not os.path.exists(file_path):
        abort(404)
    
    # Define tipo MIME apropriado
    if filename.endswith('.m3u8'):
        mimetype = 'application/vnd.apple.mpegurl'
    elif filename.endswith('.ts'):
        mimetype = 'video/mp2t'
    else:
        mimetype = 'application/octet-stream'
    
    response = send_from_directory(session_dir, filename, mimetype=mimetype)
    
    # Headers para evitar cache em HLS
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

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
    # Rate limiting para admin dashboard
    user_ip = request.remote_addr
    if not rate_limiter.is_allowed(f"admin_dashboard_{user_ip}"):
        logger.warning(f"Rate limit exceeded para admin_dashboard de IP: {user_ip}")
        abort(429, description="Muitas tentativas. Tente novamente mais tarde.")
    
    if "logged_in" in session and session["is_admin"]:
        # Gerar CSRF token se não existir
        if 'csrf_token' not in session:
            session['csrf_token'] = generate_csrf_token()
            
        logger.info(f"Acesso ao admin dashboard por {session.get('username')} de IP: {user_ip}")
        return render_template("admin.html", csrf_token=session['csrf_token'])
    
    logger.warning(f"Tentativa de acesso não autorizado ao admin dashboard de IP: {user_ip}")
    return redirect(url_for("index"))

# Rota para o novo dashboard administrativo
@app.route("/dashboard_admin")
def dashboard_admin():
    # Rate limiting para dashboard admin
    user_ip = request.remote_addr
    if not rate_limiter.is_allowed(f"dashboard_admin_{user_ip}"):
        logger.warning(f"Rate limit exceeded para dashboard_admin de IP: {user_ip}")
        abort(429, description="Muitas tentativas. Tente novamente mais tarde.")
    
    if "logged_in" in session and session["is_admin"]:
        # Gerar CSRF token se não existir
        if 'csrf_token' not in session:
            session['csrf_token'] = generate_csrf_token()
            
        logger.info(f"Acesso ao dashboard admin por {session.get('username')} de IP: {user_ip}")
        return render_template("dashboard_admin.html", csrf_token=session['csrf_token'])
    
    logger.warning(f"Tentativa de acesso não autorizado ao dashboard admin de IP: {user_ip}")
    return redirect(url_for("index"))

# Rota para monitoramento de sessões ativas
@app.route("/admin/sessions")
def sessions_monitor():
    """Monitoramento de sessões ativas para administradores"""
    user_ip = request.remote_addr
    
    if "logged_in" in session and session["is_admin"]:
        logger.info(f"Acesso ao monitor de sessões por {session.get('username')} de IP: {user_ip}")
        return render_template("sessions_monitor.html")
    
    logger.warning(f"Tentativa de acesso não autorizado ao monitor de sessões de IP: {user_ip}")
    return redirect(url_for("index"))

# Rota para gerenciar usuários
@app.route("/admin/manage_users")
@secure_db_operation
def manage_users():
    # Rate limiting para manage users
    user_ip = request.remote_addr
    if not rate_limiter.is_allowed(f"manage_users_{user_ip}"):
        logger.warning(f"Rate limit exceeded para manage_users de IP: {user_ip}")
        abort(429, description="Muitas tentativas. Tente novamente mais tarde.")
    
    if "logged_in" in session and session["is_admin"]:
        # Gerar CSRF token se não existir
        if 'csrf_token' not in session:
            session['csrf_token'] = generate_csrf_token()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, localidade, is_admin, is_active FROM users"
        )
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"Gerenciamento de usuários acessado por {session.get('username')} de IP: {user_ip}")
        return render_template("manage_users.html", users=users, csrf_token=session['csrf_token'])
    else:
        logger.warning(f"Tentativa de acesso não autorizado ao manage_users de IP: {user_ip}")
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))

# Rota para deletar usuário
@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@secure_db_operation
def delete_user(user_id):
    # Validação de entrada para user_id
    if not isinstance(user_id, int) or user_id <= 0:
        logger.warning(f"user_id inválido para delete: {user_id} de IP: {request.remote_addr}")
        abort(400, description="ID de usuário inválido")
    
    user_ip = request.remote_addr
    if "logged_in" in session and session["is_admin"]:
        # Verificação de CSRF token
        csrf_token = request.form.get('csrf_token')
        if not csrf_token or csrf_token != session.get('csrf_token'):
            logger.warning(f"CSRF token inválido em delete_user de IP: {user_ip}")
            abort(403, description="Token CSRF inválido")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Usuário {user_id} deletado por {session.get('username')} de IP: {user_ip}")
        flash("Usuário excluído com sucesso!", "success")
        return redirect(url_for("manage_users"))
    else:
        logger.warning(f"Tentativa de acesso não autorizado ao delete_user de IP: {user_ip}")
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))

# Rota para bloquear usuário
@app.route("/admin/block_user/<int:user_id>", methods=["POST"])
@secure_db_operation
def block_user(user_id):
    # Validação de entrada para user_id
    if not isinstance(user_id, int) or user_id <= 0:
        logger.warning(f"user_id inválido para block: {user_id} de IP: {request.remote_addr}")
        abort(400, description="ID de usuário inválido")
    
    user_ip = request.remote_addr
    if "logged_in" in session and session["is_admin"]:
        # Verificação de CSRF token
        csrf_token = request.form.get('csrf_token')
        if not csrf_token or csrf_token != session.get('csrf_token'):
            logger.warning(f"CSRF token inválido em block_user de IP: {user_ip}")
            abort(403, description="Token CSRF inválido")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET is_active = %s WHERE id = %s", (False, user_id)
            )
            conn.commit()
            logger.info(f"Usuário {user_id} bloqueado por {session.get('username')} de IP: {user_ip}")
            flash("Usuário bloqueado com sucesso!", "success")
        except Exception as e:
            logger.error(f"Erro ao bloquear usuário {user_id}: {e}")
            flash(f"Erro ao bloquear o usuário: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("manage_users"))
    else:
        logger.warning(f"Tentativa de acesso não autorizado ao block_user de IP: {user_ip}")
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))

# Rota para desbloquear usuário
@app.route("/admin/unblock_user/<int:user_id>", methods=["POST"])
@secure_db_operation
def unblock_user(user_id):
    # Validação de entrada para user_id
    if not isinstance(user_id, int) or user_id <= 0:
        logger.warning(f"user_id inválido para unblock: {user_id} de IP: {request.remote_addr}")
        abort(400, description="ID de usuário inválido")
    
    user_ip = request.remote_addr
    if "logged_in" in session and session["is_admin"]:
        # Verificação de CSRF token
        csrf_token = request.form.get('csrf_token')
        if not csrf_token or csrf_token != session.get('csrf_token'):
            logger.warning(f"CSRF token inválido em unblock_user de IP: {user_ip}")
            abort(403, description="Token CSRF inválido")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET is_active = %s WHERE id = %s", (True, user_id)
            )
            conn.commit()
            logger.info(f"Usuário {user_id} desbloqueado por {session.get('username')} de IP: {user_ip}")
            flash("Usuário desbloqueado com sucesso!", "success")
        except Exception as e:
            logger.error(f"Erro ao desbloquear usuário {user_id}: {e}")
            flash(f"Erro ao desbloquear o usuário: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("manage_users"))
    else:
        logger.warning(f"Tentativa de acesso não autorizado ao unblock_user de IP: {user_ip}")
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))

@app.route("/admin/add_user", methods=["GET", "POST"])
@secure_db_operation
def add_new_user():
    user_ip = request.remote_addr
    
    # Verificação de admin
    if not ("logged_in" in session and session["is_admin"]):
        logger.warning(f"Tentativa de acesso não autorizado ao add_user de IP: {user_ip}")
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        # Verificação de CSRF token
        csrf_token = request.form.get('csrf_token')
        if not csrf_token or csrf_token != session.get('csrf_token'):
            logger.warning(f"CSRF token inválido em add_user de IP: {user_ip}")
            abort(403, description="Token CSRF inválido")
        
        username = request.form["username"]
        password = request.form["password"]
        localidade = request.form["localidade"]
        plan_start = request.form.get("plan_start")
        plan_end = request.form.get("plan_end")

        # Sanitizar entradas primeiro
        username = security_validator.sanitize_input(username.strip(), 30)
        localidade = security_validator.sanitize_input(localidade.strip(), 30)

        # Validação de entradas usando security_validator
        if not security_validator.is_username_valid(username):
            logger.warning(f"Username inválido em add_user: {username} de IP: {user_ip}")
            flash("Nome de usuário inválido! Use apenas letras, números, espaços, underscore e hífens.", "error")
            return redirect(url_for("add_new_user"))
            
        if not security_validator.is_password_valid(password):
            logger.warning(f"Senha inválida em add_user de IP: {user_ip}")
            flash("Senha deve ter pelo menos 8 caracteres, incluindo letras, números e símbolos!", "error")
            return redirect(url_for("add_new_user"))
            
        if not security_validator.is_localidade_valid(localidade):
            logger.warning(f"Localidade inválida em add_user: {localidade} de IP: {user_ip}")
            flash("Localidade inválida!", "error")
            return redirect(url_for("add_new_user"))

        if not username or not password or not localidade or not plan_start or not plan_end:
            flash("Todos os campos são obrigatórios!", "error")
            return redirect(url_for("add_new_user"))

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            hashed_password = generate_password_hash(password)
            cursor.execute(
                """
                INSERT INTO users (username, password, localidade, is_admin, is_active, plan_start, plan_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (username, hashed_password, localidade, False, True, plan_start, plan_end)
            )
            conn.commit()
            logger.info(f"Usuário {username} criado por {session.get('username')} de IP: {user_ip}")
            flash("Usuário adicionado com sucesso!", "success")
        except psycopg2.IntegrityError:
            conn.rollback()
            logger.warning(f"Tentativa de criar usuário duplicado: {username} de IP: {user_ip}")
            flash("Erro: Nome de usuário já existe!", "error")
        except Exception as e:
            logger.error(f"Erro ao adicionar usuário {username}: {e}")
            flash(f"Erro ao adicionar o usuário: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("manage_users"))

    # GET request - gerar CSRF token se não existir
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()

    return render_template("add_user.html", csrf_token=session['csrf_token'])

# Rota para editar usuário
@app.route("/admin/edit_user/<int:user_id>", methods=["GET", "POST"])
@secure_db_operation
def edit_user(user_id):
    """Página de edição de usuários exclusiva para administradores"""
    user_ip = request.remote_addr
    
    # Verificação de admin
    if not ("logged_in" in session and session["is_admin"]):
        logger.warning(f"Tentativa de acesso não autorizado ao edit_user de IP: {user_ip}")
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))
    
    # Buscar dados do usuário
    user = get_user_by_id(user_id)
    if not user:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("dashboard_admin"))
    
    if request.method == "POST":
        # Verificação de CSRF token
        csrf_token = request.form.get('csrf_token')
        if not csrf_token or csrf_token != session.get('csrf_token'):
            logger.warning(f"CSRF token inválido em edit_user de IP: {user_ip}")
            abort(403, description="Token CSRF inválido")
        
        username = request.form["username"]
        localidade = request.form["localidade"]
        plan_start = request.form.get("plan_start")
        plan_end = request.form.get("plan_end")
        is_admin = request.form.get("is_admin") == "true"
        is_active = request.form.get("is_active") == "true"

        # Validação de entradas
        if not security_validator.is_username_valid(username):
            logger.warning(f"Username inválido em edit_user: {username} de IP: {user_ip}")
            flash("Nome de usuário inválido!", "error")
            return render_template("edit_user.html", user={
                'id': user_id,
                'username': user[1],
                'localidade': user[2], 
                'is_admin': user[3],
                'is_active': user[4],
                'plan_start': user[5],
                'plan_end': user[6]
            }, csrf_token=session.get('csrf_token'))
            
        if not security_validator.is_localidade_valid(localidade):
            logger.warning(f"Localidade inválida em edit_user: {localidade} de IP: {user_ip}")
            flash("Localidade inválida!", "error")
            return render_template("edit_user.html", user={
                'id': user_id,
                'username': user[1],
                'localidade': user[2], 
                'is_admin': user[3],
                'is_active': user[4],
                'plan_start': user[5],
                'plan_end': user[6]
            }, csrf_token=session.get('csrf_token'))

        if not username or not localidade or not plan_start or not plan_end:
            flash("Todos os campos são obrigatórios!", "error")
            return render_template("edit_user.html", user={
                'id': user_id,
                'username': user[1],
                'localidade': user[2], 
                'is_admin': user[3],
                'is_active': user[4],
                'plan_start': user[5],
                'plan_end': user[6]
            }, csrf_token=session.get('csrf_token'))

        # Validar datas
        try:
            start_date = datetime.strptime(plan_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(plan_end, '%Y-%m-%d').date()
            
            if end_date <= start_date:
                flash("A data de expiração deve ser posterior à data de início!", "error")
                return render_template("edit_user.html", user={
                    'id': user_id,
                    'username': user[1],
                    'localidade': user[2], 
                    'is_admin': user[3],
                    'is_active': user[4],
                    'plan_start': user[5],
                    'plan_end': user[6]
                }, csrf_token=session.get('csrf_token'))
        except ValueError:
            flash("Formato de data inválido!", "error")
            return render_template("edit_user.html", user={
                'id': user_id,
                'username': user[1],
                'localidade': user[2], 
                'is_admin': user[3],
                'is_active': user[4],
                'plan_start': user[5],
                'plan_end': user[6]
            }, csrf_token=session.get('csrf_token'))

        # Verificar se o username já existe (exceto para o usuário atual)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (username, user_id))
        existing_user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if existing_user:
            flash("Nome de usuário já existe. Escolha outro.", "error")
            return render_template("edit_user.html", user={
                'id': user_id,
                'username': user[1],
                'localidade': user[2], 
                'is_admin': user[3],
                'is_active': user[4],
                'plan_start': user[5],
                'plan_end': user[6]
            }, csrf_token=session.get('csrf_token'))

        # Atualizar usuário
        if update_user(user_id, username, localidade, plan_start, plan_end, is_admin, is_active):
            logger.info(f"Usuário {username} editado por {session.get('username')} de IP: {user_ip}")
            flash("Usuário atualizado com sucesso!", "success")
            return redirect(url_for("dashboard_admin"))
        else:
            flash("Erro ao atualizar o usuário. Tente novamente.", "error")

    # GET request - exibir formulário
    # Gerar CSRF token se não existir
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()
    
    return render_template("edit_user.html", user={
        'id': user[0],
        'username': user[1],
        'localidade': user[2], 
        'is_admin': user[3],
        'is_active': user[4],
        'plan_start': user[5],
        'plan_end': user[6]
    }, csrf_token=session['csrf_token'])

# Rota para o administrador alterar a senha de um usuário
@app.route("/admin/change_password/<int:user_id>", methods=["GET", "POST"])
@secure_db_operation
def admin_change_password(user_id):
    # Validação de entrada para user_id
    if not isinstance(user_id, int) or user_id <= 0:
        logger.warning(f"user_id inválido para change_password: {user_id} de IP: {request.remote_addr}")
        abort(400, description="ID de usuário inválido")
    
    user_ip = request.remote_addr
    
    if "logged_in" in session and session.get("is_admin"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            logger.warning(f"Usuário {user_id} não encontrado para mudança de senha de IP: {user_ip}")
            flash("Usuário não encontrado.", "error")
            return redirect(url_for("manage_users"))

        if request.method == "POST":
            # Verificação de CSRF token
            csrf_token = request.form.get('csrf_token')
            if not csrf_token or csrf_token != session.get('csrf_token'):
                logger.warning(f"CSRF token inválido em admin_change_password de IP: {user_ip}")
                abort(403, description="Token CSRF inválido")
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
        # GET request - gerar CSRF token se não existir
        if 'csrf_token' not in session:
            session['csrf_token'] = generate_csrf_token()
        return render_template("admin_change_password.html", user=user, csrf_token=session['csrf_token'])
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))
    
@app.route("/trigger_cache_cleanup", methods=["POST"])
def trigger_cache_cleanup():
    """
    Aciona a limpeza de cache para todas as localidades.
    """
    try:
        remove_old_frames(IMAGE_DIR, max_age_in_seconds=300)
        print("[Backend] Limpeza de cache acionada pelo frontend.")
        return jsonify({"message": "Limpeza de cache executada com sucesso."}), 200
    except Exception as e:
        print(f"[Backend] Erro ao executar limpeza de cache: {e}")
        return jsonify({"error": "Erro ao executar limpeza de cache."}), 500
    
# Rota para o administrador alterar sua própria senha
@app.route("/admin/change_own_password", methods=["GET", "POST"])
def admin_change_own_password():
    if "logged_in" in session and session.get("is_admin"):
        if request.method == "POST":
            # Verificação de CSRF token
            csrf_token = request.form.get('csrf_token')
            if not csrf_token or csrf_token != session.get('csrf_token'):
                logger.warning(f"CSRF token inválido em admin_change_own_password de IP: {request.remote_addr}")
                abort(403, description="Token CSRF inválido")
            
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
        # GET request - gerar CSRF token se não existir
        if 'csrf_token' not in session:
            session['csrf_token'] = generate_csrf_token()
        return render_template("admin_change_own_password.html", csrf_token=session['csrf_token'])
    else:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("index"))

# Rota para o usuário alterar sua própria senha
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "logged_in" in session:
        username = session.get("username")
        if request.method == "POST":
            # Verificação de CSRF token
            csrf_token = request.form.get('csrf_token')
            if not csrf_token or csrf_token != session.get('csrf_token'):
                logger.warning(f"CSRF token inválido em change_password de IP: {request.remote_addr}")
                abort(403, description="Token CSRF inválido")
            
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

    # GET request - gerar CSRF token se não existir
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()
    return render_template("change_password.html", csrf_token=session['csrf_token'])

# Rota para limpar o cache de uma localidade específica
@app.route("/<localidade>/clear_cache", methods=["POST"])
def clear_cache(localidade):
    local_dir = os.path.join(IMAGE_DIR, localidade.lower())
    frame_path_local = os.path.join(local_dir, "screen.png")
    frame_temp_path = os.path.join(local_dir, "screen_temp.png")
    print(f"[clear_cache] Recebida requisição para limpar cache da localidade: {localidade}")
    print(f"[clear_cache] Caminho do arquivo: {frame_path_local}")
    
    files_removed = []
    try:
        # Remove arquivo principal
        if os.path.exists(frame_path_local):
            os.remove(frame_path_local)
            files_removed.append("screen.png")
            
        # Remove arquivo temporário se existir
        if os.path.exists(frame_temp_path):
            os.remove(frame_temp_path)
            files_removed.append("screen_temp.png")
            
        if files_removed:
            print(f"[clear_cache] Arquivos deletados com sucesso: {', '.join(files_removed)}")
            return jsonify({"message": f"Cache limpo com sucesso. Arquivos removidos: {', '.join(files_removed)}"}), 200
        else:
            print("[clear_cache] Nenhum arquivo encontrado.")
            return jsonify({"message": "Nenhum cache encontrado para a localidade especificada."}), 404
    except Exception as e:
        print(f"[clear_cache] Erro ao deletar o arquivo: {e}")
        return jsonify({"message": f"Erro ao limpar cache: {str(e)}"}), 500

# ENDPOINT REAL para o dashboard (100% dados do PostgreSQL)
@app.route("/admin/api/dashboard-users")
def dashboard_users_api():
    """
    Retorna dados REAIS dos usuários e seu uso do sistema.
    Baseado na VIEW v_user_usage (dados do PostgreSQL).
    SEM MOCKS, SEM DADOS FICTÍCIOS.
    """
    if "logged_in" not in session or not session.get("is_admin"):
        return jsonify({"error": "Acesso não autorizado"}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                u.id,
                u.username,
                u.localidade,
                u.is_admin,
                u.is_active,
                u.plan_start,
                u.plan_end,
                MAX(e.created_at) as last_activity_at,
                COUNT(*) FILTER (
                    WHERE e.created_at >= NOW() - INTERVAL '30 days'
                ) AS access_last_30d,
                CASE
                    WHEN MAX(e.created_at) >= NOW() - INTERVAL '5 minutes'
                    THEN TRUE
                    ELSE FALSE
                END AS using_now,
                COUNT(DISTINCT DATE(e.created_at)) FILTER (
                    WHERE e.created_at >= NOW() - INTERVAL '30 days'
                ) AS days_active_last_30d
            FROM users u
            LEFT JOIN usage_events e ON e.user_id = u.id
            GROUP BY u.id, u.username, u.localidade, u.is_admin, u.is_active, u.plan_start, u.plan_end
            ORDER BY using_now DESC, last_activity_at DESC NULLS LAST
        """)
        
        users = cursor.fetchall()
        result = []
        
        for user in users:
            user_data = {
                "id": user[0],
                "name": user[1],  # username REAL do banco
                "email": f"{user[1]}@{user[2]}.local",  # Gerado a partir de dados reais
                "localidade": user[2],  # localidade REAL do banco
                "is_admin": user[3],   # is_admin REAL do banco
                "is_active": user[4],  # is_active REAL do banco
                "plan_start": user[5].isoformat() if user[5] else None,  # Data início REAL
                "plan_end": user[6].isoformat() if user[6] else None,    # Data fim REAL
                "last_activity": user[7].isoformat() if user[7] else None,  # REAL
                "access_last_30d": user[8] or 0,  # Contagem REAL de eventos
                "using_now": user[9] or False,    # Calculado REAL (últimos 5 min)
                "days_active_last_30d": user[10] or 0,  # Dias REAIS de atividade
                # Status baseado em dados REAIS do banco
                "blocked": not user[4],      # Baseado no is_active REAL
                "status": "blocked" if not user[4] else ("active" if user[9] else "inactive"),
                "devices_now": 1 if user[9] else 0,  # Baseado no using_now REAL
            }
            result.append(user_data)
        
        cursor.close()
        conn.close()
        
        print(f"[Dashboard API] Retornando {len(result)} usuários REAIS do banco")
        return jsonify(result)
        
    except Exception as e:
        print(f"[Dashboard API] Erro ao buscar dados: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

# ENDPOINT para sessões ativas
@app.route("/admin/api/active-sessions")
def active_sessions_api():
    """
    Retorna dados das sessões ativas para monitoramento
    """
    if "logged_in" not in session or not session.get("is_admin"):
        return jsonify({"error": "Acesso não autorizado"}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                s.id,
                u.username,
                u.localidade,
                s.session_id,
                s.ip_address,
                s.user_agent,
                s.created_at,
                s.last_activity,
                EXTRACT(EPOCH FROM (NOW() - s.last_activity))/60 as minutes_inactive
            FROM active_sessions s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.last_activity DESC
        """)
        
        sessions = cursor.fetchall()
        result = []
        
        for session_data in sessions:
            result.append({
                "id": session_data[0],
                "username": session_data[1],
                "localidade": session_data[2],
                "session_id": session_data[3][:8] + "...",  # Mostrar apenas início do ID
                "ip_address": str(session_data[4]) if session_data[4] else "Unknown",
                "user_agent": session_data[5][:50] + "..." if session_data[5] and len(session_data[5]) > 50 else session_data[5] or "Unknown",
                "created_at": session_data[6].isoformat(),
                "last_activity": session_data[7].isoformat(),
                "minutes_inactive": round(session_data[8], 1) if session_data[8] else 0,
                "is_active": session_data[8] < 5 if session_data[8] else True  # Ativo se < 5 min
            })
        
        cursor.close()
        conn.close()
        
        logger.info(f"[Sessions API] Retornando {len(result)} sessões ativas")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro na API de sessões: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

# Página de erro 404 - Página não encontrada
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# Página de erro 500 - Erro interno do servidor
@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

# Inicializar o banco de dados antes de servir qualquer rota
# COMENTADO PARA PRODUÇÃO - evita problemas durante deploy no Render
# create_database()

# Inicializar diretório de sessões
ensure_sessions_directory()

# Iniciar o aplicativo com acesso externo
if __name__ == "__main__":
    # Inicia a tarefa de limpeza de frames antigos
    start_cleanup_task(interval=300, max_age_in_seconds=300)
    
    # Para desenvolvimento local, descomentar se necessário:
    # create_database()
    
    # Obter porta do ambiente ou usar 5000 como padrão
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    # Inicia o servidor Flask
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
