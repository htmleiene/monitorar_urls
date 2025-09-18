from flask import Flask, render_template
from flask_socketio import SocketIO
import eventlet
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import time

eventlet.monkey_patch()  # importante para requests e sockets funcionarem de forma assíncrona

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# Lista de URLs para monitorar
urls = [
    "https://www.inspirali.com/",
    "https://www.inspirali.com/portfolio/"
]

@app.route('/')
def index():
    return render_template('dashboard.html')

def monitorar_links():
    """Função que monitora links e envia logs via Socket.IO"""
    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            status = response.status_code
        except Exception as e:
            status = f"Erro: {e}"

        # Formata data e hora
        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        # Envia log para o front-end
        socketio.emit('log', {'url': url, 'status': status, 'hora': now})

        # Espera 1s antes do próximo link para simular processo contínuo
        time.sleep(1)

# Rota para iniciar monitoramento manualmente
@app.route('/start')
def start_monitoramento():
    # roda em background para não travar o servidor
    socketio.start_background_task(monitorar_links)
    return "Monitoramento iniciado!"

if __name__ == '__main__':
    # Para rodar local sem Gunicorn
    socketio.run(app, host='0.0.0.0', port=5000)
