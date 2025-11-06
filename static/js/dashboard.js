// Dashboard JavaScript Functions

/**
 * Cria uma nova sala de compartilhamento
 */
async function createRoom() {
    const roomName = document.getElementById('roomName').value.trim();
    if (!roomName) {
        alert('Por favor, digite um nome para a sala');
        return;
    }

    try {
        const response = await fetch('/create_room', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ room_name: roomName })
        });

        const data = await response.json();
        
        if (response.ok) {
            alert('Sala criada com sucesso!');
            window.location.reload();
        } else {
            alert('Erro ao criar sala: ' + data.error);
        }
    } catch (error) {
        alert('Erro ao criar sala: ' + error.message);
    }
}

/**
 * Copia o link da sala para a área de transferência
 * @param {string} roomId - ID da sala
 */
function copyRoomLink(roomId) {
    const link = window.location.origin + '/join_room/' + roomId;
    navigator.clipboard.writeText(link).then(() => {
        alert('Link copiado para a área de transferência!');
    }).catch(err => {
        console.error('Erro ao copiar link:', err);
        // Fallback para navegadores mais antigos
        const textArea = document.createElement('textarea');
        textArea.value = link;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        alert('Link copiado para a área de transferência!');
    });
}

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Adicionar listeners para eventos de teclado
    const roomNameInput = document.getElementById('roomName');
    if (roomNameInput) {
        roomNameInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                createRoom();
            }
        });
    }
});