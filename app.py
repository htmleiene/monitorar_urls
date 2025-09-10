from flask import Flask, render_template, jsonify, send_file
from flask_socketio import SocketIO, emit
import threading
import time
from datetime import datetime
from database import db
from automation import executar_monitoramento, coletar_links_selenium, testar_link
from io import BytesIO
import sqlite3
import eventlet

# Faz o monkey patch para compatibilidade com WebSockets
eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

monitoring_active = False

def format_timestamp(dt=None):
    """Formata datetime para dd-mm-yyyy hh:mm"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%d-%m-%Y %H:%M")

def run_monitoring():
    """Executa o monitoramento em loop em segundo plano"""
    global monitoring_active
    monitoring_active = True
    
    while monitoring_active:
        executar_monitoramento()
        for _ in range(300):  # 300 segundos = 5 minutos
            if not monitoring_active:
                break
            time.sleep(1)
    
    socketio.emit('log', {'message': 'Monitoramento parado', 'level': 'info'}, namespace='/')

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    try:
        dashboard_data = db.get_dashboard_data()
        status_200 = dashboard_data['statusCounts'].get(200, 0)
        status_error = sum(count for status, count in dashboard_data['statusCounts'].items() if status != 200)
        total_links = dashboard_data['totalLinks']

        success_percent = round((status_200 / total_links) * 100) if total_links > 0 else 0
        error_percent = round((status_error / total_links) * 100) if total_links > 0 else 0

        if status_200 + status_error != total_links:
            status_200 = min(status_200, total_links)
            status_error = total_links - status_200
            success_percent = round((status_200 / total_links) * 100) if total_links > 0 else 0
            error_percent = round((status_error / total_links) * 100) if total_links > 0 else 0

        latest_results = db.get_latest_check_results(50)
        links_data = [{
            'url': row['url'],
            'status': row['status_code'],
            'layoutOk': bool(row['layout_ok']),
            'padraoOk': bool(row['pattern_ok']),
            'timestamp': row['checked_at']
        } for row in latest_results]

        return jsonify({
            'totalLinks': total_links,
            'status200': status_200,
            'statusError': status_error,
            'status200Percent': success_percent,
            'statusErrorPercent': error_percent,
            'lastCheck': dashboard_data['lastCheck'],
            'links': links_data
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/update')
def update_status():
    socketio.emit('log', {'message': 'Atualização manual iniciada', 'level': 'info'}, namespace='/')
    executar_monitoramento()
    return jsonify({'status': 'success', 'message': 'Dados atualizados'})

@app.route('/api/export')
def export_data():
    try:
        results = db.get_latest_check_results(1000)
        output = BytesIO()
        output.write('URL,Status,Layout OK,Padrão OK,Tempo Resposta,Verificado Em\n'.encode('utf-8'))

        for row in results:
            response_time = f"{row['response_time']:.2f}s" if row['response_time'] else "N/A"
            csv_line = f'"{row["url"]}",{row["status_code"]},{"Sim" if row["layout_ok"] else "Não"},{"Sim" if row["pattern_ok"] else "Não"},"{response_time}","{row["checked_at"]}"\n'
            output.write(csv_line.encode('utf-8'))

        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'monitoramento_links_{datetime.now().strftime("%d-%m-%Y_%H-%M-%S")}.csv'
        )
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/logs')
def get_logs():
    try:
        with sqlite3.connect('monitoring.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT level, message, created_at 
                FROM system_logs 
                ORDER BY created_at DESC 
                LIMIT 100
            ''')
            logs = cursor.fetchall()
            log_lines = [f"[{log['created_at']}] {log['level']}: {log['message']}" for log in logs]
            return jsonify({'logs': log_lines})
    except Exception as e:
        return jsonify({'logs': [f"Erro ao ler logs: {str(e)}"]})

@app.route('/api/realtime-logs')
def get_realtime_logs():
    try:
        with sqlite3.connect('monitoring.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT level, message, created_at 
                FROM system_logs 
                ORDER BY created_at ASC
            ''')
            logs = cursor.fetchall()
            log_list = [{'level': log['level'], 'message': log['message'], 'timestamp': log['created_at']} for log in logs]
            return jsonify({'logs': log_list})
    except Exception as e:
        return jsonify({'logs': [{'level': 'error', 'message': f"Erro ao ler logs: {str(e)}", 'timestamp': format_timestamp()}]})

@socketio.on('connect', namespace='/')
def handle_connect():
    emit('log', {'message': 'Conectado ao monitoramento em tempo real', 'level': 'info', 'timestamp': format_timestamp()})

if __name__ == '__main__':
    monitor_thread = threading.Thread(target=run_monitoring)
    monitor_thread.daemon = True
    monitor_thread.start()

    # Usa eventlet para produção
    socketio.run(app, host='0.0.0.0', port=5000)
