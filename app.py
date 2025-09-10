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

def format_timestamp(dt):
    """Formata datetime para dd-mm-yyyy hh:mm"""
    return dt.strftime("%d-%m-%Y %H:%M")

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
    
    socketio.emit('log', {'message': 'Monitoramento parado', 'level': 'info'}, namespace='/')

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
            # Converter timestamp para o formato dd-mm-yyyy hh:mm
            timestamp = datetime.strptime(row['checked_at'], "%Y-%m-%d %H:%M:%S")
            formatted_timestamp = format_timestamp(timestamp)
            
            links_data.append({
                'url': row['url'],
                'status': row['status_code'],
                'layoutOk': bool(row['layout_ok']),
                'padraoOk': bool(row['pattern_ok']),
                'timestamp': formatted_timestamp
            })
        
        # Formatar lastCheck
        last_check = datetime.strptime(dashboard_data['lastCheck'], "%Y-%m-%d %H:%M:%S")
        formatted_last_check = format_timestamp(last_check)
        
        return jsonify({
            'totalLinks': dashboard_data['totalLinks'],
            'status200': status_200,
            'statusError': status_error,
            'lastCheck': formatted_last_check,
            'links': links_data
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/update')
def update_status():
    """Força uma atualização dos dados"""
    socketio.emit('log', {'message': 'Atualização manual iniciada', 'level': 'info'}, namespace='/')
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
            # Converter timestamp para o formato dd-mm-yyyy hh:mm
            timestamp = datetime.strptime(row['checked_at'], "%Y-%m-%d %H:%M:%S")
            formatted_timestamp = format_timestamp(timestamp)
            
            cw.writerow([
                row['url'],
                row['status_code'],
                'Sim' if row['layout_ok'] else 'Não',
                'Sim' if row['pattern_ok'] else 'Não',
                f"{row['response_time']:.2f}s" if row['response_time'] else 'N/A',
                formatted_timestamp
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
                # Converter timestamp para o formato dd-mm-yyyy hh:mm
                timestamp = datetime.strptime(log['created_at'], "%Y-%m-%d %H:%M:%S")
                formatted_timestamp = format_timestamp(timestamp)
                
                log_lines.append(f"[{formatted_timestamp}] {log['level']}: {log['message']}")
            
            return jsonify({'logs': log_lines})
    except Exception as e:
        return jsonify({'logs': [f"Erro ao ler logs: {str(e)}"]})

@app.route('/api/realtime-logs')
def get_realtime_logs():
    """Retorna TODOS os logs em tempo real"""
    try:
        with sqlite3.connect('monitoring.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT level, message, created_at 
                FROM system_logs 
                ORDER BY created_at ASC  -- Ordenar do mais antigo para o mais recente
            ''')
            logs = cursor.fetchall()
            
            log_list = []
            for log in logs:
                # Converter timestamp para o formato dd-mm-yyyy hh:mm
                timestamp = datetime.strptime(log['created_at'], "%Y-%m-%d %H:%M:%S")
                formatted_timestamp = format_timestamp(timestamp)
                
                log_list.append({
                    'level': log['level'],
                    'message': log['message'],
                    'timestamp': formatted_timestamp
                })
            
            return jsonify({'logs': log_list})
    except Exception as e:
        current_time = format_timestamp(datetime.now())
        return jsonify({'logs': [{'level': 'error', 'message': f"Erro ao ler logs: {str(e)}", 'timestamp': current_time}]})

@socketio.on('connect', namespace='/')
def handle_connect():
    """Quando um cliente se conecta via WebSocket"""
    current_time = format_timestamp(datetime.now())
    emit('log', {'message': 'Conectado ao monitoramento em tempo real', 'level': 'info', 'timestamp': current_time})

if __name__ == '__main__':
    # Executar o monitoramento em thread separada
    monitor_thread = threading.Thread(target=run_monitoring)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Inicia o servidor Flask com SocketIO
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)