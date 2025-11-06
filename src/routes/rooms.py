"""
Rotas relacionadas a salas WebRTC
"""
from flask import Blueprint, render_template, request, redirect, session, url_for, flash, jsonify
from src.database.models import UserManager, RoomManager
from src.config.settings import Config
import json

rooms_bp = Blueprint('rooms', __name__)


@rooms_bp.route("/dashboard")
def dashboard():
    """Dashboard do usuário com suas salas"""
    if "logged_in" not in session:
        return redirect(url_for("auth.index"))
    
    user_id = UserManager.get_user_id(session["username"])
    user_rooms = RoomManager.get_user_rooms(user_id)
    
    return render_template("dashboard.html", 
                         username=session["username"],
                         rooms=user_rooms,
                         is_admin=session.get("is_admin", False))


@rooms_bp.route("/get_turn_config")
def get_turn_config():
    """Retorna configuração do servidor TURN"""
    if "logged_in" in session:
        return jsonify(Config.get_turn_config())
    else:
        return jsonify({"error": "Não autorizado"}), 401


@rooms_bp.route("/create_room", methods=["POST"])
def create_room():
    """Cria uma nova sala de compartilhamento"""
    if "logged_in" not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    data = request.json
    room_name = data.get("room_name", f"Sala de {session['username']}")
    user_id = UserManager.get_user_id(session["username"])
    
    room_id = RoomManager.create_room(user_id, room_name)
    if room_id:
        return jsonify({"room_id": room_id, "message": "Sala criada com sucesso"})
    else:
        return jsonify({"error": "Erro ao criar sala"}), 500


@rooms_bp.route("/join_room/<room_id>")
def join_room_route(room_id):
    """Página para participar de uma sala"""
    room_info = RoomManager.get_room_info(room_id)
    if not room_info:
        flash("Sala não encontrada ou inativa.", "error")
        return redirect(url_for("auth.index"))
    
    return render_template("screen.html", 
                         room_id=room_id, 
                         room_name=room_info[1],
                         owner=room_info[3],
                         turn_config=json.dumps(Config.get_turn_config()))