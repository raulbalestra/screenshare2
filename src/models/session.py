"""
Gerenciador de sessões usando SQLite
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List
from config.settings import Config

class SessionManager:
    """Gerencia sessões de compartilhamento no SQLite"""
    
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
    
    def init_db(self):
        """Inicializa o banco de dados"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    publisher_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    viewer_count INTEGER DEFAULT 0,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def create_session(self, session_data: Dict) -> bool:
        """Cria uma nova sessão"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO sessions 
                    (session_id, state, publisher_name, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    session_data['session_id'],
                    session_data['state'],
                    session_data['publisher_name'],
                    session_data['created_at'],
                    session_data['is_active']
                ))
                conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Obtém uma sessão pelo ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    'SELECT * FROM sessions WHERE session_id = ? AND is_active = TRUE',
                    (session_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error:
            return None
    
    def get_sessions_by_state(self, state: str) -> List[Dict]:
        """Obtém todas as sessões ativas de um estado"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    'SELECT * FROM sessions WHERE state = ? AND is_active = TRUE ORDER BY created_at DESC',
                    (state,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []
    
    def update_session_activity(self, session_id: str):
        """Atualiza última atividade da sessão"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = ?',
                    (session_id,)
                )
                conn.commit()
        except sqlite3.Error:
            pass
    
    def increment_viewer_count(self, session_id: str):
        """Incrementa contador de viewers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'UPDATE sessions SET viewer_count = viewer_count + 1 WHERE session_id = ?',
                    (session_id,)
                )
                conn.commit()
        except sqlite3.Error:
            pass
    
    def decrement_viewer_count(self, session_id: str):
        """Decrementa contador de viewers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'UPDATE sessions SET viewer_count = MAX(0, viewer_count - 1) WHERE session_id = ?',
                    (session_id,)
                )
                conn.commit()
        except sqlite3.Error:
            pass
    
    def deactivate_session(self, session_id: str):
        """Desativa uma sessão"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'UPDATE sessions SET is_active = FALSE WHERE session_id = ?',
                    (session_id,)
                )
                conn.commit()
        except sqlite3.Error:
            pass
    
    def cleanup_old_sessions(self, hours_old: int = 24):
        """Remove sessões antigas"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE sessions SET is_active = FALSE 
                    WHERE datetime(created_at) < datetime('now', '-{} hours')
                '''.format(hours_old))
                conn.commit()
        except sqlite3.Error:
            pass