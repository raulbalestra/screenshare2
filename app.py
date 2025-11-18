"""
ScreenShare MediaMTX/HLS - Aplicação Principal
Sistema de compartilhamento de tela usando MediaMTX com WHIP ingest e HLS output
"""
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import uuid
import sqlite3
import os
import qrcode
import io
import base64
from datetime import datetime, timedelta

from src.auth.jwt_handler import JWTHandler
from src.models.session import SessionManager
from config.settings import Config
from src.database.models import UserManager, DatabaseManager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Header, Depends, Request, Response

# Inicializar FastAPI
app = FastAPI(title="ScreenShare HLS", version="1.0.0")

# This backend provides API endpoints only. Frontend (React) lives in the
# frontend/beautiful-backend-booster folder and will consume these APIs.
# We intentionally do NOT mount template/static folders here.

# Inicializar gerenciadores
jwt_handler = JWTHandler()
session_manager = SessionManager()
# User manager (Postgres)
user_manager = UserManager()

# CORS - permitir o frontend React
# IMPORTANT: Cannot use allow_origins=["*"] with allow_credentials=True
# Must specify exact origins when using credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Modelos Pydantic
class CreateSessionRequest(BaseModel):
    state: str
    publisher_name: str

class SessionResponse(BaseModel):
    session_id: str
    state: str
    publish_token: str
    publish_url: str
    play_url: str
    qr_code: str

@app.on_event("startup")
async def startup_event():
    """Inicializa a aplicação"""
    try:
        # Ensure SQLite sessions DB is initialized
        session_manager.init_db()
        # Ensure Postgres users table and migrations run
        try:
            DatabaseManager.create_tables()
        except Exception as e:
            print(f"Aviso: não foi possível criar/migrar tabelas do Postgres: {e}")
        print("🚀 ScreenShare HLS iniciado com sucesso!")
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")

# Diagnostic endpoint to check cookies
@app.get("/api/debug/cookies")
async def debug_cookies(request: Request):
    """Debug endpoint to check received cookies"""
    cookies = dict(request.cookies)
    headers = dict(request.headers)
    return {
        "cookies": cookies,
        "cookie_header": headers.get("cookie", "No cookie header"),
        "access_token_present": "access_token" in cookies,
        "refresh_token_present": Config.REFRESH_COOKIE_NAME in cookies
    }

# NOTE: The web frontend serves UI pages. Root template rendering removed.

@app.post("/api/session/create")
async def create_session(request: CreateSessionRequest):
    """Cria uma nova sessão de compartilhamento"""
    try:
        session_id = str(uuid.uuid4())
        
        # Criar sessão no banco
        session_data = {
            'session_id': session_id,
            'state': request.state,
            'publisher_name': request.publisher_name,
            'created_at': datetime.now(),
            'is_active': True
        }
        
        session_manager.create_session(session_data)
        
        # Gerar tokens JWT
        publish_token = jwt_handler.create_publish_token(session_id, request.state)
        
        # URLs - Use public domain with Nginx proxy paths
        stream_path = session_id
        base_url = os.getenv('PUBLIC_URL', 'https://screenshare.fun')
        publish_url = f"{base_url}/webrtc/{stream_path}/whip"
        play_url = f"{base_url}/hls/{stream_path}/index.m3u8"
        
        # Gerar QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f"http://{Config.APP_HOST}:{Config.APP_PORT}/play/{session_id}")
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, 'PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "session_id": session_id,
            "state": request.state,
            "publish_token": publish_token,
            "publish_url": publish_url,
            "play_url": play_url,
            "qr_code": f"data:image/png;base64,{qr_code_base64}"
        }
        
    except Exception as e:
        print(f"Erro ao criar sessão: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/api/session/{session_id}/play")
async def get_play_info(session_id: str):
    """Obtem informações para reprodução de uma sessão"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    play_token = jwt_handler.create_play_token(session_id, session['state'])
    # Use public domain with Nginx proxy path for HLS
    # The Nginx reverse proxy at /hls/ forwards to MediaMTX at port 8888
    base_url = os.getenv('PUBLIC_URL', 'https://screenshare.fun')
    play_url = f"{base_url}/hls/{session_id}/index.m3u8"
    
    return {
        "session_id": session_id,
        "state": session['state'],
        "play_token": play_token,
        "play_url": play_url,
        "publisher_name": session['publisher_name']
    }

# Template-based UI endpoints removed: frontend will handle UI routes.

@app.get("/api/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "timestamp": datetime.now()}


# --- Authentication endpoints (JWT access tokens) ---
def _get_bearer_token(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None

async def get_current_user(request: Request, token: Optional[str] = Depends(_get_bearer_token)):
    # Try header first (Authorization: Bearer ...), then cookie 'access_token'
    if not token:
        token = request.cookies.get('access_token')

    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    payload = jwt_handler.verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

async def require_admin(payload: dict = Depends(get_current_user)):
    if not payload.get('is_admin'):
        raise HTTPException(status_code=403, detail="Administrator privileges required")
    return payload


@app.post("/api/auth/login")
async def api_login(credentials: dict):
    """Login com email/username + password. Retorna access token."""
    email = credentials.get('email') or credentials.get('username')
    password = credentials.get('password')
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email/username and password required")

    try:
        auth = UserManager.authenticate_user(email, password)
        if not auth:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if auth == "blocked":
            raise HTTPException(status_code=403, detail="User is blocked")

        # auth is tuple: (id, username, email, localidade, is_admin)
        user_id, username, user_email, localidade, is_admin = auth
        # Create access and refresh tokens. Refresh token contains a jti stored in DB
        refresh_jti = str(uuid.uuid4())
        access_token = jwt_handler.create_access_token(user_id, user_email, is_admin)
        refresh_token = jwt_handler.create_refresh_token(user_id, user_email, is_admin, refresh_jti)

        # Save refresh jti in DB with expiry
        from datetime import datetime, timedelta
        expires_at = datetime.utcnow() + timedelta(days=Config.JWT_REFRESH_EXPIRE_DAYS)
        DatabaseManager.migrate_add_email_column()  # ensure tables exist
        DatabaseManager.save_refresh_token = getattr(DatabaseManager, 'save_refresh_token', None)
        try:
            # Use UserManager helper to save refresh token if present
            DatabaseManager.get_connection()
        except Exception:
            pass
        # Save using UserManager wrapper
        try:
            # Save via UserManager method
            UserManager.save_refresh_token = getattr(UserManager, 'save_refresh_token', None)
        except Exception:
            pass

        # Save refresh token via DatabaseManager static method we added
        try:
            # Note: the method lives on UserManager in our file; call DatabaseManager to get conn
            # We'll call UserManager.save_refresh_token if exists, otherwise DatabaseManager.save_refresh_token
            if hasattr(UserManager, 'save_refresh_token'):
                UserManager.save_refresh_token(refresh_jti, user_id, expires_at)
            else:
                DatabaseManager.save_refresh_token(refresh_jti, user_id, expires_at)
        except Exception as e:
            print('Warning: could not save refresh token in DB:', e)

        # Build response with tokens in body (for cross-domain compatibility)
        # Also set cookies for same-domain scenarios
        resp = {
            'user': {'id': user_id, 'username': username, 'email': user_email, 'localidade': localidade, 'is_admin': is_admin},
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        response = JSONResponse(content=resp)
        # Use secure=True and samesite='none' for cross-origin requests (Vercel -> VPS)
        secure_flag = True  # Always use secure in production
        # Set access token cookie (short-lived) - for same-domain compatibility
        # NOTE: Do NOT set domain parameter - let browser handle it
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=secure_flag,
            samesite='none',
            path='/',
            max_age=Config.JWT_ACCESS_EXPIRE_HOURS * 3600
        )
        # Set refresh token cookie (long-lived)
        response.set_cookie(
            key=Config.REFRESH_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            secure=secure_flag,
            samesite='none',
            path='/',
            max_age=Config.JWT_REFRESH_EXPIRE_DAYS * 24 * 3600
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Admin user management APIs (protected)
@app.get("/api/users")
async def api_get_users(admin: dict = Depends(require_admin)):
    users = UserManager.get_all_users()
    return {'users': users}


@app.post("/api/users")
async def api_create_user(payload: dict, admin: dict = Depends(require_admin)):
    username = payload.get('username')
    email = payload.get('email') or username
    password = payload.get('password')
    localidade = payload.get('localidade', 'unknown')
    is_admin = bool(payload.get('is_admin', False))

    if not email or not password:
        raise HTTPException(status_code=400, detail='email and password are required')

    # create_user signature expects username, password, localidade
    # we will call the lower-level function and then update is_admin if necessary
    try:
        # If username omitted, set to email localpart
        if not username:
            username = email.split('@')[0]

        success = UserManager.create_user(username, email, password, localidade, is_admin=is_admin)
        if not success:
            raise HTTPException(status_code=409, detail='User creation failed (exists?)')

        return {'ok': True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/users/{user_id}")
async def api_update_user(user_id: int, payload: dict, admin: dict = Depends(require_admin)):
    # allow updating username, email, localidade, is_active, is_admin
    fields = {}
    for f in ('username', 'email', 'localidade', 'is_active', 'is_admin'):
        if f in payload:
            fields[f] = payload[f]

    if not fields:
        raise HTTPException(status_code=400, detail='No fields to update')

    try:
        conn = DatabaseManager.get_connection()
        cur = conn.cursor()
        sets = []
        vals = []
        for k, v in fields.items():
            sets.append(f"{k} = %s")
            vals.append(v)
        vals.append(user_id)
        cur.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = %s", tuple(vals))
        conn.commit()
        cur.close()
        conn.close()
        return {'ok': True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/users/{user_id}/password")
async def api_change_user_password(user_id: int, payload: dict, admin: dict = Depends(require_admin)):
    new_password = payload.get('new_password')
    if not new_password:
        raise HTTPException(status_code=400, detail='new_password required')
    try:
        if UserManager.update_user_password(user_id, new_password):
            return {'ok': True}
        raise HTTPException(status_code=500, detail='Failed to update password')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/users/{user_id}/block")
async def api_block_user(user_id: int, admin: dict = Depends(require_admin)):
    try:
        if UserManager.update_user_status(user_id, False):
            return {'ok': True}
        raise HTTPException(status_code=500, detail='Failed to block user')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/users/{user_id}/unblock")
async def api_unblock_user(user_id: int, admin: dict = Depends(require_admin)):
    try:
        if UserManager.update_user_status(user_id, True):
            return {'ok': True}
        raise HTTPException(status_code=500, detail='Failed to unblock user')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/users/{user_id}")
async def api_delete_user(user_id: int, admin: dict = Depends(require_admin)):
    """Delete a user permanently"""
    try:
        if UserManager.delete_user(user_id):
            return {'ok': True}
        raise HTTPException(status_code=500, detail='Failed to delete user')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/migrate")
async def api_migrate(admin: dict = Depends(require_admin)):
    """Admin-only endpoint to run DB migrations (safe to run multiple times)."""
    try:
        DatabaseManager.migrate_add_email_column()
        return {"ok": True, "message": "Migration executed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/me")
async def api_me(user: dict = Depends(get_current_user)):
    """Return current user information based on cookie or Authorization header."""
    return {'user': {
        'user_id': user.get('user_id') or user.get('user_id'),
        'email': user.get('email'),
        'is_admin': user.get('is_admin')
    }}


@app.post("/api/auth/logout")
async def api_logout(request: Request):
    """Logout by clearing the httpOnly access_token cookie and revoking refresh token server-side"""
    # Read refresh token from cookie and revoke it in DB
    refresh_token = request.cookies.get(Config.REFRESH_COOKIE_NAME)
    if refresh_token:
        payload = jwt_handler.verify_refresh_token(refresh_token)
        if payload:
            jti = payload.get('jti')
            try:
                UserManager.revoke_refresh_token(jti)
            except Exception:
                pass

    resp = JSONResponse(content={'ok': True})
    resp.delete_cookie('access_token', path='/')
    resp.delete_cookie(Config.REFRESH_COOKIE_NAME, path='/')
    return resp


@app.post('/api/auth/refresh')
async def api_refresh(request: Request):
    """Refresh access token. Accepts refresh token from cookie OR Authorization header. Rotates refresh token on success."""
    # Try to read refresh token from cookie first, then from body
    refresh_token = request.cookies.get(Config.REFRESH_COOKIE_NAME)
    
    # If no cookie, try to read from request body
    if not refresh_token:
        try:
            body = await request.json()
            refresh_token = body.get('refresh_token')
        except:
            pass
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail='Missing refresh token')

    payload = jwt_handler.verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail='Invalid or expired refresh token')

    user_id = payload.get('user_id')
    jti = payload.get('jti')
    # Validate against DB
    if not UserManager.is_refresh_token_valid(jti, user_id):
        raise HTTPException(status_code=401, detail='Refresh token revoked or invalid')

    # Rotate tokens: revoke old jti and create new one
    try:
        UserManager.revoke_refresh_token(jti)
    except Exception:
        pass

    new_jti = str(uuid.uuid4())
    access_token = jwt_handler.create_access_token(user_id, payload.get('email'), payload.get('is_admin'))
    refresh_token_new = jwt_handler.create_refresh_token(user_id, payload.get('email'), payload.get('is_admin'), new_jti)

    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(days=Config.JWT_REFRESH_EXPIRE_DAYS)
    UserManager.save_refresh_token(new_jti, user_id, expires_at)

    # Return tokens in body AND set cookies for compatibility
    secure_flag = True  # Always secure in production
    response = JSONResponse(content={
        'ok': True,
        'access_token': access_token,
        'refresh_token': refresh_token_new
    })
    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=secure_flag,
        samesite='none',
        path='/',
        max_age=Config.JWT_ACCESS_EXPIRE_HOURS * 3600
    )
    response.set_cookie(
        key=Config.REFRESH_COOKIE_NAME,
        value=refresh_token_new,
        httponly=True,
        secure=secure_flag,
        samesite='none',
        path='/',
        max_age=Config.JWT_REFRESH_EXPIRE_DAYS * 24 * 3600
    )
    return response

@app.get("/api/districts/{uf}")
async def get_districts(uf: str):
    """Obter municípios de um UF via API IBGE"""
    import urllib.request
    import json as json_lib
    import gzip
    
    try:
        # Converter UF para código numérico
        uf_code = str(uf).upper()
        
        # Se passar o nome do estado, converter para código
        states_map = {
            "AC": "12", "AL": "27", "AP": "16", "AM": "13", "BA": "29", "CE": "23",
            "DF": "26", "ES": "32", "GO": "52", "MA": "11", "MT": "28", "MS": "10",
            "MG": "31", "PA": "15", "PB": "25", "PR": "41", "PE": "26", "PI": "22",
            "RJ": "33", "RN": "24", "RS": "43", "RO": "11", "RR": "14", "SC": "42",
            "SP": "35", "SE": "28", "TO": "17"
        }
        
        # Se passou 2 letras, converter para código
        if len(uf_code) == 2 and uf_code in states_map:
            uf_code = states_map[uf_code]
        
        # API IBGE para municípios de um estado
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf_code}/municipios?orderBy=nome"
        
        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read()
            
            # Verificar se está comprimido com gzip
            if content[:2] == b'\x1f\x8b':  # Magic number for gzip
                content = gzip.decompress(content)
            
            data = json_lib.loads(content.decode('utf-8'))
        
        # Retornar em formato padronizado
        districts = []
        for item in data:
            districts.append({
                "id": item.get("id"),
                "nome": item.get("nome")
            })
        
        return {"districts": districts}
    except Exception as e:
        print(f"Erro ao buscar municípios do IBGE: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar municípios: {str(e)}")


@app.get("/api/debug")
async def debug_info():
    """Debug info"""
    try:
        # Testar conexão com banco
        session_manager.init_db()
        return {
            "database": "OK",
            "jwt_handler": "OK" if jwt_handler else "ERROR",
            "config": {
                "app_host": Config.APP_HOST,
                "app_port": Config.APP_PORT,
                "mediamtx_host": Config.MEDIAMTX_HOST
            }
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=Config.APP_PORT,
        reload=Config.DEBUG
    )
