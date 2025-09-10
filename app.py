from flask import Flask, render_template, jsonify, send_file
from flask_socketio import SocketIO, emit
import threading
import time
from datetime import datetime
from database import db
from automation import executar_monitoramento, coletar_links_selenium, testar_link
import csv
from io import StringIO
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
socketio = SocketIO(app, cors_allowed_origins="*")

# Variável para controlar se o monitoramento está em execução
monitoring_active = False

def run_monitoring():
    """Executa o monitoramento em loop em segundo plano"""
    global monitoring_active
    monitoring_active = True
    
    while monitoring_active:
        executar_monitoramento()
        
        # Espera 5 minutos entre as verificações
        for _ in range(300):  # 300 segundos = 5 minutos
            if not monitoring_active:
                break
            time.sleep(1)
    
    socketio.emit('log', {'message': 'Monitoramento parado'}, namespace='/')

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    """Retorna dados para o dashboard"""
    try:
        dashboard_data = db.get_dashboard_data()
        
        # Calcula totais
        status_200 = dashboard_data['statusCounts'].get(200, 0)
        status_error = sum(count for status, count in dashboard_data['statusCounts'].items() 
                          if status != 200 and status != 'erro')
        
        # Obtém últimos resultados
        latest_results = db.get_latest_check_results(50)
        
        links_data = []
        for row in latest_results:
            links_data.append({
                'url': row['url'],
                'status': row['status_code'],
                'layoutOk': bool(row['layout_ok']),
                'padraoOk': bool(row['pattern_ok']),
                'timestamp': row['checked_at']
            })
        
        return jsonify({
            'totalLinks': dashboard_data['totalLinks'],
            'status200': status_200,
            'statusError': status_error,
            'lastCheck': dashboard_data['lastCheck'],
            'links': links_data
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/update')
def update_status():
    """Força uma atualização dos dados"""
    socketio.emit('log', {'message': 'Atualização manual iniciada'}, namespace='/')
    executar_monitoramento()
    return jsonify({'status': 'success', 'message': 'Dados atualizados'})

@app.route('/api/export')
def export_data():
    """Exporta os dados para CSV"""
    try:
        results = db.get_latest_check_results(1000)
        
        si = StringIO()
        cw = csv.writer(si)
        
        # Cabeçalho
        cw.writerow(['URL', 'Status', 'Layout OK', 'Padrão OK', 'Tempo Resposta', 'Verificado Em'])
        
        # Dados
        for row in results:
            cw.writerow([
                row['url'],
                row['status_code'],
                'Sim' if row['layout_ok'] else 'Não',
                'Sim' if row['pattern_ok'] else 'Não',
                f"{row['response_time']:.2f}s" if row['response_time'] else 'N/A',
                row['checked_at']
            ])
        
        output = si.getvalue()
        si.close()
        
        return send_file(
            StringIO(output),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'monitoramento_links_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/logs')
def get_logs():
    """Retorna os logs do sistema"""
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
            
            log_lines = []
            for log in logs:
                log_lines.append(f"[{log['created_at']}] {log['level']}: {log['message']}")
            
            return jsonify({'logs': log_lines})
    except Exception as e:
        return jsonify({'logs': [f"Erro ao ler logs: {str(e)}"]})

@socketio.on('connect', namespace='/')
def handle_connect():
    """Quando um cliente se conecta via WebSocket"""
    emit('log', {'message': 'Conectado ao monitoramento em tempo real'})

if __name__ == '__main__':
    # Executar o monitoramento em thread separada
    monitor_thread = threading.Thread(target=run_monitoring)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Inicia o servidor Flask com SocketIO
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)