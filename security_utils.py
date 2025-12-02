"""
MÓDULO DE SEGURANÇA E VALIDAÇÃO
Contém funções para validação de entrada e proteção contra ataques comuns
"""

import os
import re
import html
import bleach
import hmac
import hashlib
import logging
import functools

# Configurar logging de segurança
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.WARNING)
handler = logging.FileHandler('security.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
security_logger.addHandler(handler)

class SecurityValidator:
    """Classe para validações de segurança"""
    
    # Padrões perigosos para detectar tentativas de SQL injection
    SQL_INJECTION_PATTERNS = [
        r"('|(\\'))(|(.*?))('|(\\'))",  # Single quotes
        r"\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b",
        r"(--|#|/\*|\*/)",  # SQL comments
        r"(\bor\b.*?=.*?=|\band\b.*?=.*?=)",  # OR/AND with equals
        r"(;|\+|%|\|)",  # Common SQL injection chars
        r"(\bscript\b|\bjavascript\b|\bvbscript\b)",  # Script injection
    ]
    
    # Padrões para XSS
    XSS_PATTERNS = [
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # Event handlers
        r"<iframe.*?>",
        r"<object.*?>",
        r"<embed.*?>",
    ]
    
    @staticmethod
    def validate_username(username):
        """
        Valida nome de usuário
        - Permite letras, números, underscore e espaços (para nomes reais)
        - Tamanho entre 3 e 30 caracteres
        - Não pode começar ou terminar com espaço
        """
        if not username or not isinstance(username, str):
            return False, "Nome de usuário é obrigatório"
        
        # Remover espaços extras no início e fim
        username_cleaned = username.strip()
        
        if len(username_cleaned) < 3 or len(username_cleaned) > 30:
            return False, "Nome de usuário deve ter entre 3 e 30 caracteres"
        
        # Permitir letras, números, underscore, espaços e alguns caracteres especiais comuns em nomes
        if not re.match(r'^[a-zA-ZÀ-ÿ0-9_\s\-\.]+$', username_cleaned):
            return False, "Nome de usuário pode conter apenas letras, números, underscore, espaços e hífens"
        
        # Não permitir múltiplos espaços consecutivos
        if re.search(r'\s{2,}', username_cleaned):
            return False, "Nome de usuário não pode ter espaços consecutivos"
        
        # Verificar se não é uma palavra reservada
        reserved_words = ['root', 'system', 'null', 'undefined', 'select', 'insert', 'update', 'delete']
        if username_cleaned.lower() in reserved_words:
            return False, "Nome de usuário não permitido"
        
        return True, "Válido"
    
    @staticmethod
    def validate_password(password):
        """
        Valida senha
        - Mínimo 8 caracteres
        - Ao menos 1 letra maiúscula, 1 minúscula, 1 número
        """
        if not password or not isinstance(password, str):
            return False, "Senha é obrigatória"
        
        if len(password) < 8:
            return False, "Senha deve ter pelo menos 8 caracteres"
        
        if len(password) > 128:
            return False, "Senha muito longa (máximo 128 caracteres)"
        
        if not re.search(r'[a-z]', password):
            return False, "Senha deve conter pelo menos uma letra minúscula"
        
        if not re.search(r'[A-Z]', password):
            return False, "Senha deve conter pelo menos uma letra maiúscula"
        
        if not re.search(r'\d', password):
            return False, "Senha deve conter pelo menos um número"
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\?]', password):
            return False, "Senha deve conter pelo menos um caractere especial"
        
        return True, "Válido"
    
    @staticmethod
    def validate_localidade(localidade):
        """
        Valida localidade
        - Permite letras, números, underscore, hífen e espaços (para nomes compostos)
        - Tamanho entre 2 e 30 caracteres
        - Permite qualquer nome de cidade/região válido
        """
        if not localidade or not isinstance(localidade, str):
            return False, "Localidade é obrigatória"
        
        # Remover espaços extras no início e fim
        localidade_cleaned = localidade.strip()
        
        if len(localidade_cleaned) < 2 or len(localidade_cleaned) > 30:
            return False, "Localidade deve ter entre 2 e 30 caracteres"
        
        # Permite letras (incluindo acentos), números, underscore, hífen e espaços
        if not re.match(r'^[a-zA-ZÀ-ÿ0-9_\-\s]+$', localidade_cleaned):
            return False, "Localidade pode conter apenas letras, números, underscore, hífen e espaços"
        
        # Não permitir múltiplos espaços consecutivos
        if re.search(r'\s{2,}', localidade_cleaned):
            return False, "Localidade não pode ter espaços consecutivos"
        
        # Não permitir apenas números ou caracteres especiais
        if re.match(r'^[0-9_\-\s]+$', localidade_cleaned):
            return False, "Localidade deve conter pelo menos uma letra"
        
        # Bloquear palavras que podem ser problemáticas para URLs (exceto admin que é válido)
        blocked_words = ['api', 'root', 'system', 'null', 'undefined', 'script', 'javascript']
        if localidade_cleaned.lower() in blocked_words:
            return False, "Nome de localidade não permitido"
        
        return True, "Válido"
    
    @staticmethod
    def detect_sql_injection(input_string):
        """
        Detecta tentativas de SQL injection
        """
        if not input_string or not isinstance(input_string, str):
            return False
        
        input_lower = input_string.lower()
        
        for pattern in SecurityValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_lower, re.IGNORECASE):
                security_logger.warning(f"SQL Injection detectado: {input_string[:100]}")
                return True
        
        return False
    
    @staticmethod
    def detect_xss(input_string):
        """
        Detecta tentativas de XSS
        """
        if not input_string or not isinstance(input_string, str):
            return False
        
        for pattern in SecurityValidator.XSS_PATTERNS:
            if re.search(pattern, input_string, re.IGNORECASE):
                security_logger.warning(f"XSS detectado: {input_string[:100]}")
                return True
        
        return False
    
    @staticmethod
    def sanitize_input(input_string, max_length=255):
        """
        Sanitiza entrada de usuário
        """
        if not input_string:
            return ""
        
        # Converter para string se não for
        input_string = str(input_string)
        
        # Limitar tamanho
        input_string = input_string[:max_length]
        
        # Trim espaços extras
        input_string = input_string.strip()
        
        # Normalizar espaços múltiplos para um só
        input_string = re.sub(r'\s+', ' ', input_string)
        
        # Escapar HTML
        input_string = html.escape(input_string)
        
        # Usar bleach para limpeza adicional (preservando espaços)
        input_string = bleach.clean(input_string, tags=[], attributes={}, strip=True)
        
        return input_string.strip()
    
    @staticmethod
    def validate_file_upload(filename, max_size_mb=10):
        """
        Valida uploads de arquivo
        """
        if not filename:
            return False, "Nome do arquivo é obrigatório"
        
        # Extensões permitidas para imagens
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.webp']
        file_extension = os.path.splitext(filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            return False, "Tipo de arquivo não permitido"
        
        # Verificar caracteres perigosos no nome do arquivo
        if re.search(r'[<>:"/\\|?*]', filename):
            return False, "Nome do arquivo contém caracteres inválidos"
        
        return True, "Válido"
    
    @staticmethod
    def validate_session_data(session_data):
        """
        Valida dados de sessão para prevenir session hijacking
        """
        required_fields = ['username', 'logged_in']
        
        for field in required_fields:
            if field not in session_data:
                return False, f"Campo obrigatório missing: {field}"
        
        # Validar username
        username_valid, _ = SecurityValidator.validate_username(session_data.get('username', ''))
        if not username_valid:
            return False, "Username de sessão inválido"
        
        # Para usuários admin, localidade pode ser opcional
        is_admin = session_data.get('is_admin', False)
        if not is_admin and 'localidade' in session_data:
            # Só validar localidade se não for admin e se localidade estiver presente
            localidade_valid, _ = SecurityValidator.validate_localidade(session_data.get('localidade', ''))
            if not localidade_valid:
                return False, "Localidade de sessão inválida"
        elif not is_admin and 'localidade' not in session_data:
            # Usuários não-admin devem ter localidade
            return False, "Localidade obrigatória para usuários não-admin"
        
        return True, "Válido"

    # Métodos de conveniência que retornam apenas boolean
    def is_username_valid(self, username):
        """Retorna apenas True/False para validação de username"""
        valid, _ = self.validate_username(username)
        return valid
    
    def is_password_valid(self, password):
        """Retorna apenas True/False para validação de password"""
        valid, _ = self.validate_password(password)
        return valid
    
    def is_localidade_valid(self, localidade):
        """Retorna apenas True/False para validação de localidade"""
        valid, _ = self.validate_localidade(localidade)
        return valid

    def validate_image_file(self, file):
        """Valida arquivo de imagem para upload"""
        if not file or not file.filename:
            return False
        
        # Verificar tamanho do arquivo (10MB max)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if hasattr(file, 'content_length') and file.content_length > MAX_FILE_SIZE:
            return False
        
        # Verificar extensão
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            return False
        
        return True

class RateLimiter:
    """Implementa rate limiting para prevenir ataques de força bruta"""
    
    def __init__(self):
        self.attempts = {}  # {ip: {'count': int, 'last_attempt': timestamp}}
        self.max_attempts = 5
        self.window_minutes = 15
    
    def is_rate_limited(self, ip_address):
        """
        Verifica se IP está limitado por rate limiting
        """
        import time
        
        current_time = time.time()
        
        if ip_address not in self.attempts:
            return False
        
        attempt_data = self.attempts[ip_address]
        
        # Se passou da janela de tempo, resetar contador
        if current_time - attempt_data['last_attempt'] > (self.window_minutes * 60):
            del self.attempts[ip_address]
            return False
        
        # Verificar se excedeu máximo de tentativas
        return attempt_data['count'] >= self.max_attempts
    
    def record_attempt(self, ip_address, success=False):
        """
        Registra tentativa de login
        """
        import time
        
        current_time = time.time()
        
        if success:
            # Se login foi bem-sucedido, limpar contador
            if ip_address in self.attempts:
                del self.attempts[ip_address]
            return
        
        # Registrar tentativa falhada
        if ip_address not in self.attempts:
            self.attempts[ip_address] = {'count': 0, 'last_attempt': current_time}
        
        self.attempts[ip_address]['count'] += 1
        self.attempts[ip_address]['last_attempt'] = current_time
        
        security_logger.warning(f"Tentativa de login falhada de IP: {ip_address}")

    def is_allowed(self, identifier):
        """
        Verifica se uma operação é permitida baseada no rate limiting
        Wrapper para is_rate_limited com lógica invertida
        """
        return not self.is_rate_limited(identifier)

# Instância global do rate limiter
rate_limiter = RateLimiter()

def secure_db_operation(func):
    """
    Decorator para operações de banco de dados seguras
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Log da operação
            security_logger.info(f"Operação DB: {func.__name__}")
            return func(*args, **kwargs)
        except Exception as e:
            # Log do erro sem expor detalhes sensíveis
            security_logger.error(f"Erro em operação DB: {func.__name__} - {type(e).__name__}: {str(e)[:100]}")
            # Re-raise Flask abort exceptions (como 403, 400) para que sejam tratadas corretamente
            from werkzeug.exceptions import HTTPException
            if isinstance(e, HTTPException):
                raise e
            # Para outros erros, usar mensagem genérica
            raise Exception("Erro interno do sistema")
    
    return wrapper

def validate_csrf_token(request, session):
    """
    Valida token CSRF
    """
    token_from_form = request.form.get('csrf_token')
    token_from_session = session.get('csrf_token')
    
    if not token_from_form or not token_from_session:
        return False
    
    # Secure string comparison using hmac.compare_digest
    return hmac.compare_digest(str(token_from_form), str(token_from_session))

def generate_csrf_token():
    """
    Gera token CSRF
    """
    import secrets
    return secrets.token_hex(16)