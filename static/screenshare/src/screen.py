import pyscreenshot
from flask import Flask, send_file
from io import BytesIO

app = Flask(__name__)

@app.route('/screen.png')
def serve_pil_image():
    # Captura a tela e salva em um buffer de memória
    img_buffer = BytesIO()
    pyscreenshot.grab().save(img_buffer, 'PNG', quality=50)
    img_buffer.seek(0)
    return send_file(img_buffer, mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
