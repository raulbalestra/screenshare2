"""
ScreenShare MediaMTX/HLS - Aplicação Principal
Sistema de compartilhamento de tela usando MediaMTX com WHIP ingest e HLS output
"""
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import uuid
import sqlite3
import qrcode
import io
import base64
from datetime import datetime, timedelta

from src.auth.jwt_handler import JWTHandler
from src.models.session import SessionManager
from config.settings import Config

# Inicializar FastAPI
app = FastAPI(title="ScreenShare HLS", version="1.0.0")

# Templates e arquivos estáticos
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Inicializar gerenciadores
jwt_handler = JWTHandler()
session_manager = SessionManager()

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
        session_manager.init_db()
        print("🚀 ScreenShare HLS iniciado com sucesso!")
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Página inicial"""
    return templates.TemplateResponse("base_simple.html", {"request": request})

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
        
        # URLs - MediaMTX WebRTC endpoint
        stream_path = f"{request.state}/{session_id}"
        publish_url = f"http://{Config.MEDIAMTX_HOST}:8889/{stream_path}/whip"
        play_url = f"http://{Config.MEDIAMTX_HOST}:{Config.MEDIAMTX_HLS_PORT}/{stream_path}/index.m3u8"
        
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
    play_url = f"http://{Config.MEDIAMTX_HOST}:{Config.MEDIAMTX_HLS_PORT}/{session['state']}/{session_id}/index.m3u8"
    
    return {
        "session_id": session_id,
        "state": session['state'],
        "play_token": play_token,
        "play_url": play_url,
        "publisher_name": session['publisher_name']
    }

@app.get("/publish", response_class=HTMLResponse)
async def publish_page(request: Request):
    """Página de transmissão"""
    return templates.TemplateResponse("publish.html", {"request": request})

@app.get("/play/{session_id}", response_class=HTMLResponse)
async def play_page(request: Request, session_id: str):
    """Página de reprodução"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    return templates.TemplateResponse("play.html", {
        "request": request,
        "session_id": session_id,
        "state": session['state'],
        "publisher_name": session['publisher_name']
    })

@app.get("/api/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "timestamp": datetime.now()}

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
