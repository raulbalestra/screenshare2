"""
Módulo de conexão e operações do banco de dados
"""
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from src.config.settings import Config


class DatabaseManager:
    """Gerenciador de conexões e operações do banco de dados"""
    
    @staticmethod
    def get_connection():
        """Cria uma nova conexão com o banco de dados"""
        try:
            conn = psycopg2.connect(
                host=Config.DB_HOST,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                port=Config.DB_PORT,
            )
            return conn
        except psycopg2.Error as e:
            print(f"Erro ao conectar com o banco de dados: {e}")
            raise
    
    @staticmethod
    def create_tables():
        """Cria as tabelas necessárias no banco de dados"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Tabela de usuários
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    localidade VARCHAR(100) NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Tabela de salas WebRTC
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rooms (
                    id SERIAL PRIMARY KEY,
                    room_id TEXT UNIQUE NOT NULL,
                    room_name TEXT NOT NULL,
                    owner_id INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    max_participants INTEGER DEFAULT 10
                );
            """)
            
            # Tabela de participantes das salas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS room_participants (
                    id SERIAL PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    user_id INTEGER REFERENCES users(id),
                    socket_id TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_presenter BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (room_id) REFERENCES rooms(room_id)
                );
            """)

            # Tabela de refresh tokens para gerenciamento e revogação
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    jti TEXT PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Inserir usuários padrão se a tabela estiver vazia
            # Ensure migrations for older DBs (add email column if missing)
            DatabaseManager.migrate_add_email_column(conn, cursor)

            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                default_users = [
                    ("curitiba_user", "curitiba_user@example.com", "senha_curitiba", "curitiba", False, True),
                    ("sp_user", "sp_user@example.com", "senha_sp", "sp", False, True),
                    ("admin", "admin@example.com", "admin", "admin", True, True),
                ]

                for username, email, password, localidade, is_admin, is_active in default_users:
                    hashed_password = generate_password_hash(password)
                    cursor.execute("""
                        INSERT INTO users (username, email, password, localidade, is_admin, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (username, email, hashed_password, localidade, is_admin, is_active))
            
            conn.commit()
            print("Tabelas criadas com sucesso!")
            
        except psycopg2.Error as e:
            print(f"Erro ao criar tabelas: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def migrate_add_email_column(conn=None, cursor=None):
        """Migration helper: add 'email' column to users table for existing databases.

        If called with no connection/cursor, a new connection is opened.
        This will:
        - add the email column if missing
        - populate email from username when username looks like an email
        - for remaining NULL emails, populate a placeholder (username@local)
        - create a unique index on email and set NOT NULL
        """
        close_conn = False
        if conn is None or cursor is None:
            conn = DatabaseManager.get_connection()
            cursor = conn.cursor()
            close_conn = True

        try:
            # Check if column exists
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='email'")
            exists = cursor.fetchone()
            if exists:
                return

            print("Applying migration: adding 'email' column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")

            # Populate email where username already looks like an email
            cursor.execute("UPDATE users SET email = username WHERE username LIKE %s", ("%@%",))

            # For remaining rows, set a placeholder using username
            cursor.execute("UPDATE users SET email = username || %s WHERE email IS NULL", ('@local',))

            # Try to create unique index on email
            try:
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique_idx ON users (email)")
            except Exception as e:
                print(f"Warning: could not create unique index on users.email: {e}")

            # Set NOT NULL constraint
            try:
                cursor.execute("ALTER TABLE users ALTER COLUMN email SET NOT NULL")
            except Exception as e:
                print(f"Warning: could not set users.email NOT NULL: {e}")

            conn.commit()
            print("Migration applied: email column added/updated.")
        except Exception as e:
            print(f"Erro na migração add email: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if close_conn:
                cursor.close()
                conn.close()


class UserManager:
    """Gerenciador de operações relacionadas a usuários"""
    
    @staticmethod
    def authenticate_user(username, password):
        """Autentica um usuário"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            # The parameter may be an email or username. Try to find by email first then username.
            cursor.execute("SELECT id, username, email, password, localidade, is_admin, is_active FROM users WHERE email = %s OR username = %s", (username, username))
            user = cursor.fetchone()

            if user and check_password_hash(user[3], password):  # password at index 3
                if user[6]:  # is_active at index 6
                    # return a tuple with useful fields: id, username, email, localidade, is_admin
                    return (user[0], user[1], user[2], user[4], user[5])
                else:
                    return "blocked"
            return None
            
        except psycopg2.Error as e:
            print(f"Erro ao autenticar usuário: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_user_id(username):
        """Busca ID do usuário pelo username"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            # username may be either username or email
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, username))
            result = cursor.fetchone()
            return result[0] if result else None
        except psycopg2.Error as e:
            print(f"Erro ao buscar ID do usuário: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_all_users():
        """Busca todos os usuários"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id, username, email, localidade, is_admin, is_active, created_at FROM users ORDER BY id")
            rows = cursor.fetchall()
            # return as list of dicts for easier JSON serialization
            users = []
            for r in rows:
                users.append({
                    'id': r[0],
                    'username': r[1],
                    'email': r[2],
                    'localidade': r[3],
                    'is_admin': r[4],
                    'is_active': r[5],
                    'created_at': r[6].isoformat() if r[6] else None
                })
            return users
        except psycopg2.Error as e:
            print(f"Erro ao buscar usuários: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def create_user(username, email, password, localidade, is_admin=False):
        """Cria um novo usuário (email required)"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            hashed_password = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (username, email, password, localidade, is_admin, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (username, email, hashed_password, localidade, is_admin, True))
            
            conn.commit()
            return True
        except psycopg2.IntegrityError:
            conn.rollback()
            return False
        except psycopg2.Error as e:
            print(f"Erro ao criar usuário: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def update_user_password(user_id, new_password):
        """Atualiza a senha de um usuário"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            hashed_password = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_id))
            conn.commit()
            return True
        except psycopg2.Error as e:
            print(f"Erro ao atualizar senha: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def delete_user(user_id):
        """Remove um usuário"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            return True
        except psycopg2.Error as e:
            print(f"Erro ao deletar usuário: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def update_user_status(user_id, is_active):
        """Atualiza o status ativo/inativo de um usuário"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE users SET is_active = %s WHERE id = %s", (is_active, user_id))
            conn.commit()
            return True
        except psycopg2.Error as e:
            print(f"Erro ao atualizar status do usuário: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    # --- Refresh token management ---
    @staticmethod
    def save_refresh_token(jti: str, user_id: int, expires_at):
        conn = DatabaseManager.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO refresh_tokens (jti, user_id, expires_at) VALUES (%s, %s, %s)", (jti, user_id, expires_at))
            conn.commit()
            return True
        except psycopg2.IntegrityError:
            conn.rollback()
            return False
        except psycopg2.Error as e:
            print(f"Erro ao salvar refresh token: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def revoke_refresh_token(jti: str):
        conn = DatabaseManager.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM refresh_tokens WHERE jti = %s", (jti,))
            conn.commit()
            return True
        except psycopg2.Error as e:
            print(f"Erro ao revogar refresh token: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def is_refresh_token_valid(jti: str, user_id: int):
        conn = DatabaseManager.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT expires_at FROM refresh_tokens WHERE jti = %s AND user_id = %s", (jti, user_id))
            row = cur.fetchone()
            if not row:
                return False
            expires_at = row[0]
            from datetime import datetime
            if expires_at and expires_at < datetime.utcnow():
                # expired — remove it
                cur.execute("DELETE FROM refresh_tokens WHERE jti = %s", (jti,))
                conn.commit()
                return False
            return True
        except psycopg2.Error as e:
            print(f"Erro ao validar refresh token: {e}")
            return False
        finally:
            cur.close()
            conn.close()


class RoomManager:
    """Gerenciador de operações relacionadas a salas WebRTC"""
    
    @staticmethod
    def create_room(owner_id, room_name):
        """Cria uma nova sala WebRTC"""
        import uuid
        
        room_id = str(uuid.uuid4())
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO rooms (room_id, room_name, owner_id, is_active)
                VALUES (%s, %s, %s, %s)
            """, (room_id, room_name, owner_id, True))
            
            conn.commit()
            return room_id
        except psycopg2.Error as e:
            print(f"Erro ao criar sala: {e}")
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_user_rooms(user_id):
        """Busca salas do usuário"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT room_id, room_name, created_at, is_active
                FROM rooms 
                WHERE owner_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
            return cursor.fetchall()
        except psycopg2.Error as e:
            print(f"Erro ao buscar salas do usuário: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_room_info(room_id):
        """Busca informações da sala"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT r.room_id, r.room_name, r.owner_id, u.username
                FROM rooms r
                JOIN users u ON r.owner_id = u.id
                WHERE r.room_id = %s AND r.is_active = TRUE
            """, (room_id,))
            return cursor.fetchone()
        except psycopg2.Error as e:
            print(f"Erro ao buscar informações da sala: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def add_participant(room_id, user_id, socket_id, is_presenter=False):
        """Adiciona participante à sala"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO room_participants (room_id, user_id, socket_id, is_presenter)
                VALUES (%s, %s, %s, %s)
            """, (room_id, user_id, socket_id, is_presenter))
            
            conn.commit()
            return True
        except psycopg2.Error as e:
            print(f"Erro ao adicionar participante: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def remove_participant(socket_id):
        """Remove participante da sala"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM room_participants WHERE socket_id = %s", (socket_id,))
            conn.commit()
            return True
        except psycopg2.Error as e:
            print(f"Erro ao remover participante: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()