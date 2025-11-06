// WebRTC Screen Share JavaScript

/**
 * Classe para gerenciar o WebRTC e compartilhamento de tela
 */
class ScreenShareManager {
    constructor(roomId, turnConfig) {
        this.roomId = roomId;
        this.turnConfig = turnConfig;
        this.socket = io();
        this.localStream = null;
        this.peerConnection = null;
        this.isPresenter = false;
        this.isScreenSharing = false;
        this.isMuted = false;
        
        // Elementos DOM
        this.localVideo = document.getElementById('localVideo');
        this.remoteVideo = document.getElementById('remoteVideo');
        this.videoPlaceholder = document.getElementById('videoPlaceholder');
        this.shareScreenBtn = document.getElementById('shareScreenBtn');
        this.muteBtn = document.getElementById('muteBtn');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.participantsList = document.getElementById('participantsList');
        this.participantCount = document.getElementById('participantCount');

        // Configuração WebRTC
        this.pcConfiguration = {
            iceServers: this.turnConfig.iceServers
        };

        this.initializeSocketEvents();
        this.joinRoom();
    }

    /**
     * Inicializa os eventos do Socket.IO
     */
    initializeSocketEvents() {
        this.socket.on('connect', () => {
            this.updateStatus('Conectado', 'connected');
            this.showToast('Conectado ao servidor');
        });

        this.socket.on('disconnect', () => {
            this.updateStatus('Desconectado', 'disconnected');
            this.showToast('Desconectado do servidor');
        });

        this.socket.on('joined_room', (data) => {
            this.isPresenter = data.is_presenter;
            this.updateUI();
            this.showToast(this.isPresenter ? 'Você é o apresentador' : 'Entrou na sala como espectador');
        });

        this.socket.on('user_joined', (data) => {
            this.showToast(`${data.username} entrou na sala`);
            this.updateParticipantsList();
        });

        this.socket.on('user_left', (data) => {
            this.showToast(`Usuário saiu da sala`);
            this.updateParticipantsList();
        });

        this.socket.on('offer', async (data) => {
            if (!this.isPresenter) {
                await this.handleOffer(data.offer, data.sender_socket);
            }
        });

        this.socket.on('answer', async (data) => {
            if (this.peerConnection) {
                await this.peerConnection.setRemoteDescription(data.answer);
            }
        });

        this.socket.on('ice_candidate', async (data) => {
            if (this.peerConnection && data.candidate) {
                await this.peerConnection.addIceCandidate(data.candidate);
            }
        });

        this.socket.on('error', (data) => {
            this.showToast('Erro: ' + data.message);
        });
    }

    /**
     * Entra na sala
     */
    joinRoom() {
        this.socket.emit('join_room', { room_id: this.roomId });
    }

    /**
     * Sai da sala
     */
    leaveRoom() {
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
        }
        if (this.peerConnection) {
            this.peerConnection.close();
        }
        this.socket.emit('leave_room', { room_id: this.roomId });
        window.location.href = '/dashboard';
    }

    /**
     * Alterna o compartilhamento de tela
     */
    async toggleScreenShare() {
        if (!this.isScreenSharing) {
            await this.startScreenShare();
        } else {
            this.stopScreenShare();
        }
    }

    /**
     * Inicia o compartilhamento de tela
     */
    async startScreenShare() {
        if (!this.isPresenter) {
            this.showToast('Apenas o apresentador pode compartilhar tela');
            return;
        }

        try {
            this.localStream = await navigator.mediaDevices.getDisplayMedia({
                video: true,
                audio: true
            });

            this.localVideo.srcObject = this.localStream;
            this.localVideo.style.display = 'block';
            this.videoPlaceholder.style.display = 'none';

            this.localStream.getVideoTracks()[0].addEventListener('ended', () => {
                this.stopScreenShare();
            });

            this.isScreenSharing = true;
            this.shareScreenBtn.innerHTML = '<i class="fas fa-stop"></i> Parar Compartilhamento';
            this.shareScreenBtn.className = 'btn btn-danger';
            this.muteBtn.style.display = 'inline-flex';

            // Iniciar conexões WebRTC com os espectadores
            await this.createPeerConnections();

            this.showToast('Compartilhamento de tela iniciado');
        } catch (error) {
            console.error('Erro ao compartilhar tela:', error);
            this.showToast('Erro ao compartilhar tela');
        }
    }

    /**
     * Para o compartilhamento de tela
     */
    stopScreenShare() {
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }

        this.localVideo.style.display = 'none';
        this.videoPlaceholder.style.display = 'flex';
        
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }

        this.isScreenSharing = false;
        this.shareScreenBtn.innerHTML = '<i class="fas fa-desktop"></i> Compartilhar Tela';
        this.shareScreenBtn.className = 'btn btn-success';
        this.muteBtn.style.display = 'none';

        this.showToast('Compartilhamento de tela parado');
    }

    /**
     * Cria conexões peer-to-peer
     */
    async createPeerConnections() {
        // Esta função seria expandida para gerenciar múltiplas conexões
        // Para simplicidade, vamos focar na conexão principal
    }

    /**
     * Manipula ofertas WebRTC
     */
    async handleOffer(offer, senderSocket) {
        this.peerConnection = new RTCPeerConnection(this.pcConfiguration);

        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.socket.emit('ice_candidate', {
                    room_id: this.roomId,
                    target_socket: senderSocket,
                    candidate: event.candidate
                });
            }
        };

        this.peerConnection.ontrack = (event) => {
            this.remoteVideo.srcObject = event.streams[0];
            this.remoteVideo.style.display = 'block';
            this.videoPlaceholder.style.display = 'none';
        };

        await this.peerConnection.setRemoteDescription(offer);
        const answer = await this.peerConnection.createAnswer();
        await this.peerConnection.setLocalDescription(answer);

        this.socket.emit('answer', {
            room_id: this.roomId,
            target_socket: senderSocket,
            answer: answer
        });
    }

    /**
     * Alterna o mute do áudio
     */
    toggleMute() {
        if (this.localStream && this.localStream.getAudioTracks().length > 0) {
            const audioTrack = this.localStream.getAudioTracks()[0];
            audioTrack.enabled = !audioTrack.enabled;
            this.isMuted = !audioTrack.enabled;
            
            this.muteBtn.innerHTML = this.isMuted ? 
                '<i class="fas fa-microphone-slash"></i> Ativar Som' : 
                '<i class="fas fa-microphone"></i> Silenciar';
            this.muteBtn.className = this.isMuted ? 'btn btn-danger' : 'btn btn-secondary';
        }
    }

    /**
     * Atualiza a interface do usuário
     */
    updateUI() {
        if (this.isPresenter) {
            this.shareScreenBtn.style.display = 'inline-flex';
        } else {
            this.shareScreenBtn.style.display = 'none';
        }
    }

    /**
     * Atualiza o status da conectividade
     */
    updateStatus(message, type) {
        this.statusIndicator.innerHTML = `<i class="fas fa-circle"></i> ${message}`;
        this.statusIndicator.className = `status-indicator status-${type}`;
    }

    /**
     * Atualiza a lista de participantes
     */
    updateParticipantsList() {
        // Implementar lista de participantes
        // Por simplicidade, vamos mostrar um contador fixo por agora
        this.participantCount.textContent = '1';
    }

    /**
     * Mostra notificação toast
     */
    showToast(message) {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toastMessage');
        
        toastMessage.textContent = message;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    /**
     * Copia o link da sala
     */
    copyRoomLink() {
        const link = window.location.href;
        navigator.clipboard.writeText(link).then(() => {
            this.showToast('Link da sala copiado!');
        }).catch(err => {
            console.error('Erro ao copiar link:', err);
            this.showToast('Erro ao copiar link');
        });
    }

    /**
     * Cleanup ao sair da página
     */
    cleanup() {
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
        }
        if (this.peerConnection) {
            this.peerConnection.close();
        }
    }
}

// Funções globais para compatibilidade com os templates
let screenShareManager;

function toggleScreenShare() {
    if (screenShareManager) {
        screenShareManager.toggleScreenShare();
    }
}

function toggleMute() {
    if (screenShareManager) {
        screenShareManager.toggleMute();
    }
}

function copyRoomLink() {
    if (screenShareManager) {
        screenShareManager.copyRoomLink();
    }
}

function leaveRoom() {
    if (screenShareManager) {
        screenShareManager.leaveRoom();
    }
}

// Cleanup ao sair da página
window.addEventListener('beforeunload', () => {
    if (screenShareManager) {
        screenShareManager.cleanup();
    }
});