"""
Eventos WebSocket para WebRTC
"""
from flask_socketio import emit, join_room, leave_room, rooms
from flask import session, request
from src.database.models import UserManager, RoomManager
from src.config.settings import Config


def init_websocket_events(socketio):
    """Inicializa os eventos WebSocket"""
    
    @socketio.on('join_room')
    def on_join_room(data):
        """Usuário entra em uma sala"""
        room_id = data['room_id']
        username = session.get('username')
        
        if not username:
            emit('error', {'message': 'Usuário não autenticado'})
            return
        
        user_id = UserManager.get_user_id(username)
        if not user_id:
            emit('error', {'message': 'Usuário não encontrado'})
            return
        
        # Verificar se a sala existe
        room_info = RoomManager.get_room_info(room_id)
        if not room_info:
            emit('error', {'message': 'Sala não encontrada'})
            return
        
        # Entrar na sala
        join_room(room_id)
        
        # Adicionar participante ao banco
        is_presenter = (user_id == room_info[2])  # Se é o dono da sala
        RoomManager.add_participant(room_id, user_id, request.sid, is_presenter)
        
        # Notificar outros participantes
        emit('user_joined', {
            'username': username,
            'is_presenter': is_presenter,
            'socket_id': request.sid
        }, room=room_id, include_self=False)
        
        # Confirmar entrada na sala
        emit('joined_room', {
            'room_id': room_id,
            'is_presenter': is_presenter,
            'turn_config': Config.get_turn_config()
        })

    @socketio.on('leave_room')
    def on_leave_room(data):
        """Usuário sai de uma sala"""
        room_id = data['room_id']
        username = session.get('username')
        
        leave_room(room_id)
        RoomManager.remove_participant(request.sid)
        
        # Notificar outros participantes
        emit('user_left', {
            'username': username,
            'socket_id': request.sid
        }, room=room_id, include_self=False)

    @socketio.on('offer')
    def on_offer(data):
        """Manipula ofertas WebRTC"""
        room_id = data['room_id']
        target_socket = data['target_socket']
        offer = data['offer']
        
        emit('offer', {
            'offer': offer,
            'sender_socket': request.sid
        }, room=target_socket)

    @socketio.on('answer')
    def on_answer(data):
        """Manipula respostas WebRTC"""
        room_id = data['room_id']
        target_socket = data['target_socket']
        answer = data['answer']
        
        emit('answer', {
            'answer': answer,
            'sender_socket': request.sid
        }, room=target_socket)

    @socketio.on('ice_candidate')
    def on_ice_candidate(data):
        """Manipula candidatos ICE"""
        room_id = data['room_id']
        target_socket = data['target_socket']
        candidate = data['candidate']
        
        emit('ice_candidate', {
            'candidate': candidate,
            'sender_socket': request.sid
        }, room=target_socket)

    @socketio.on('disconnect')
    def on_disconnect():
        """Usuário desconecta"""
        # Remover participante de todas as salas
        RoomManager.remove_participant(request.sid)
        
        # Notificar salas sobre a desconexão
        for room in rooms():
            if room != request.sid:  # Não notificar a própria sala do socket
                emit('user_left', {
                    'socket_id': request.sid
                }, room=room)