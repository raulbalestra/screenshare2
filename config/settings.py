"""
Configurações da aplicação ScreenShare HLS
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configurações principais da aplicação"""
    
    # Aplicação
    APP_HOST = os.getenv('APP_HOST', 'localhost')
    APP_PORT = int(os.getenv('APP_PORT', '8000'))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'sua_chave_jwt_super_secreta_aqui_mude_em_producao')
    JWT_ALGORITHM = 'HS256'
    JWT_PUBLISH_EXPIRE_HOURS = 24
    JWT_PLAY_EXPIRE_HOURS = 24
    # Access token (login) expiration (hours)
    JWT_ACCESS_EXPIRE_HOURS = int(os.getenv('JWT_ACCESS_EXPIRE_HOURS', '1'))
    # Refresh token lifetime (days)
    JWT_REFRESH_EXPIRE_DAYS = int(os.getenv('JWT_REFRESH_EXPIRE_DAYS', '7'))
    REFRESH_COOKIE_NAME = os.getenv('REFRESH_COOKIE_NAME', 'refresh_token')
    
    # MediaMTX
    MEDIAMTX_HOST = os.getenv('MEDIAMTX_HOST', 'localhost')
    MEDIAMTX_WHIP_PORT = int(os.getenv('MEDIAMTX_WHIP_PORT', '8889'))
    MEDIAMTX_HLS_PORT = int(os.getenv('MEDIAMTX_HLS_PORT', '8888'))
    MEDIAMTX_RTMP_PORT = int(os.getenv('MEDIAMTX_RTMP_PORT', '1935'))
    
    # Banco de dados (SQLite para simplicidade)
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'sessions.db')
    
    # Estados permitidos (pode ser configurado via env)
    ALLOWED_STATES = os.getenv('ALLOWED_STATES', 'SP,RJ,MG,PR,SC,RS,BA,PE,CE,GO').split(',')
    # Frontend origin(s) allowed for CORS (comma-separated)
    FRONTEND_ORIGINS = os.getenv('FRONTEND_ORIGINS', 'http://localhost:5173').split(',')