"""
Configurações da aplicação ScreenShare WebRTC
"""
import os
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

class Config:
    """Configurações principais da aplicação"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'sua_chave_secreta_super_segura_aqui')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Banco de Dados PostgreSQL
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'screenshare')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '101410')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    
    # Servidor TURN/Coturn
    TURN_SERVER_URL = os.getenv('TURN_SERVER_URL', '192.168.100.107')
    TURN_SERVER_PORT = int(os.getenv('TURN_SERVER_PORT', '3478'))
    TURN_SERVER_USERNAME = os.getenv('TURN_SERVER_USERNAME', 'raizen')
    TURN_SERVER_PASSWORD = os.getenv('TURN_SERVER_PASSWORD', 'raizen123')
    
    @classmethod
    def get_turn_config(cls):
        """Retorna configuração do servidor TURN"""
        return {
            'iceServers': [
                {
                    'urls': [
                        f'turn:{cls.TURN_SERVER_URL}:{cls.TURN_SERVER_PORT}',
                        f'turns:{cls.TURN_SERVER_URL}:5349'
                    ],
                    'username': cls.TURN_SERVER_USERNAME,
                    'credential': cls.TURN_SERVER_PASSWORD
                },
                {
                    'urls': f'stun:{cls.TURN_SERVER_URL}:{cls.TURN_SERVER_PORT}'
                }
            ]
        }
    
    @classmethod
    def get_db_connection_string(cls):
        """Retorna string de conexão do banco de dados"""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"