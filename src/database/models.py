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
                    username TEXT UNIQUE NOT NULL,
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

            # Inserir usuários padrão se a tabela estiver vazia
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                default_users = [
                    ("curitiba_user", "senha_curitiba", "curitiba", False, True),
                    ("sp_user", "senha_sp", "sp", False, True),
                    ("admin", "admin", "admin", True, True),
                ]
                
                for username, password, localidade, is_admin, is_active in default_users:
                    hashed_password = generate_password_hash(password)
                    cursor.execute("""
                        INSERT INTO users (username, password, localidade, is_admin, is_active)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (username, hashed_password, localidade, is_admin, is_active))
            
            conn.commit()
            print("Tabelas criadas com sucesso!")
            
        except psycopg2.Error as e:
            print(f"Erro ao criar tabelas: {e}")
            conn.rollback()
            raise
        finally:
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
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user[2], password):  # user[2] é a coluna password
                if user[5]:  # user[5] é a coluna is_active
                    return user[3], user[4]  # Retorna localidade (user[3]) e is_admin (user[4])
                else:
                    return "blocked", None
            return None, None
            
        except psycopg2.Error as e:
            print(f"Erro ao autenticar usuário: {e}")
            return None, None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_user_id(username):
        """Busca ID do usuário pelo username"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
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
            cursor.execute("SELECT id, username, localidade, is_admin, is_active FROM users")
            return cursor.fetchall()
        except psycopg2.Error as e:
            print(f"Erro ao buscar usuários: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def create_user(username, password, localidade):
        """Cria um novo usuário"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        
        try:
            hashed_password = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (username, password, localidade, is_admin, is_active)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, hashed_password, localidade, False, True))
            
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