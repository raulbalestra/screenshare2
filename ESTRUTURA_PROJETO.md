# Estrutura do Projeto ScreenShare

```
screenshare2/
├── app.py                      # Aplicação FastAPI principal
├── requirements.txt           # Dependências Python
├── config/
│   ├── mediamtx.yml          # Configuração MediaMTX
│   └── settings.py           # Configurações da aplicação
├── src/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── jwt_handler.py    # Geração e validação JWT
│   ├── models/
│   │   ├── __init__.py
│   │   └── session.py        # Modelos de sessão
│   └── utils/
│       ├── __init__.py
│       └── qrcode_gen.py     # Geração de QR codes
├── static/
│   ├── css/
│   │   └── style.css         # Estilos customizados
│   └── js/
│       ├── publisher.js      # JS para captura e transmissão
│       └── player.js         # JS para reprodução HLS
├── templates/
│   ├── base.html            # Template base
│   ├── publish.html         # Página de transmissão
│   └── play.html            # Página de reprodução
├── scripts/
│   ├── install.sh           # Script de instalação VPS
│   └── start.sh             # Script de inicialização
└── README.md                # Instruções
```