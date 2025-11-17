"""
JWT Handler para autenticação de publish/play
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from config.settings import Config

class JWTHandler:
    """Gerencia tokens JWT para publish e play"""
    
    def __init__(self):
        self.secret_key = Config.JWT_SECRET_KEY
        self.algorithm = Config.JWT_ALGORITHM
    
    def create_publish_token(self, session_id: str, state: str) -> str:
        """Cria token JWT para publish (transmissão)"""
        payload = {
            'session_id': session_id,
            'state': state,
            'type': 'publish',
            'exp': datetime.utcnow() + timedelta(hours=Config.JWT_PUBLISH_EXPIRE_HOURS),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_play_token(self, session_id: str, state: str) -> str:
        """Cria token JWT para play (reprodução)"""
        payload = {
            'session_id': session_id,
            'state': state,
            'type': 'play',
            'exp': datetime.utcnow() + timedelta(hours=Config.JWT_PLAY_EXPIRE_HOURS),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verifica e decodifica token JWT"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    # --- General access token methods (for user auth) ---
    def create_access_token(self, user_id: int, email: str, is_admin: bool) -> str:
        """Cria um token de acesso para uso geral (login)"""
        payload = {
            'user_id': user_id,
            'email': email,
            'is_admin': is_admin,
            'type': 'access',
            'exp': datetime.utcnow() + timedelta(hours=Config.JWT_ACCESS_EXPIRE_HOURS),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_access_token(self, token: str) -> Optional[Dict]:
        """Verifica e decodifica token de acesso e garante que é do tipo 'access'"""
        payload = self.verify_token(token)
        if not payload:
            return None
        if payload.get('type') != 'access':
            return None
        return payload

    def create_refresh_token(self, user_id: int, email: str, is_admin: bool, jti: str) -> str:
        """Cria refresh token JWT com um jti para armazenamento e rotação"""
        payload = {
            'user_id': user_id,
            'email': email,
            'is_admin': is_admin,
            'type': 'refresh',
            'jti': jti,
            'exp': datetime.utcnow() + timedelta(days=Config.JWT_REFRESH_EXPIRE_DAYS),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_refresh_token(self, token: str) -> Optional[Dict]:
        payload = self.verify_token(token)
        if not payload:
            return None
        if payload.get('type') != 'refresh':
            return None
        return payload
    
    def verify_publish_token(self, token: str, session_id: str, state: str) -> bool:
        """Verifica token de publish"""
        payload = self.verify_token(token)
        if not payload:
            return False
        
        return (
            payload.get('type') == 'publish' and
            payload.get('session_id') == session_id and
            payload.get('state') == state
        )
    
    def verify_play_token(self, token: str, session_id: str, state: str) -> bool:
        """Verifica token de play"""
        payload = self.verify_token(token)
        if not payload:
            return False
        
        return (
            payload.get('type') == 'play' and
            payload.get('session_id') == session_id and
            payload.get('state') == state
        )