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
    """Retorna dados para o dashboard - CORRIGIDO"""
    try:
        dashboard_data = db.get_dashboard_data()
        
        # Calcula totais CORRETAMENTE
        status_200 = dashboard_data['statusCounts'].get(200, 0)
        status_error = sum(count for status, count in dashboard_data['statusCounts'].items() 
                          if status != 200)  # Todos que não são 200 são erros
        
        total_links = dashboard_data['totalLinks']
        
        # Percentuais CORRETOS (evitando divisão por zero) - CORRIGIDO: uso de if/else em Python
        success_percent = round((status_200 / total_links) * 100) if total_links > 0 else 0
        error_percent = round((status_error / total_links) * 100) if total_links > 0 else 0
        
        # Verifica consistência dos dados
        if status_200 + status_error != total_links:
            # Se houver inconsistência, ajusta para não mostrar percentuais errados
            status_200 = min(status_200, total_links)
            status_error = total_links - status_200
            # Recalcula os percentuais após o ajuste
            success_percent = round((status_200 / total_links) * 100) if total_links > 0 else 0
            error_percent = round((status_error / total_links) * 100) if total_links > 0 else 0
        
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
        
        # Dados - JÁ ESTÃO NO FORMATO CORRETO
        for row in results:
            cw.writerow([
                row['url'],
                row['status_code'],
                'Sim' if row['layout_ok'] else 'Não',
                'Sim' if row['pattern_ok'] else 'Não',
                f"{row['response_time']:.2f}s" if row['response_time'] else 'N/A',
                row['checked_at']  # Já está no formato dd-mm-yyyy hh:mm
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
                # Os logs já estão no formato dd-mm-yyyy hh:mm, não precisa converter
                log_lines.append(f"[{log['created_at']}] {log['level']}: {log['message']}")
            
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
                ORDER BY created_at ASC
            ''')
            logs = cursor.fetchall()
            
            log_list = []
            for log in logs:
                # Os logs já estão no formato dd-mm-yyyy hh:mm, não precisa converter
                log_list.append({
                    'level': log['level'],
                    'message': log['message'],
                    'timestamp': log['created_at']  # Já está no formato correto
                })
            
            return jsonify({'logs': log_list})
    except Exception as e:
        current_time = format_timestamp()
        return jsonify({'logs': [{'level': 'error', 'message': f"Erro ao ler logs: {str(e)}", 'timestamp': current_time}]})

@socketio.on('connect', namespace='/')
def handle_connect():
    """Quando um cliente se conecta via WebSocket"""
    current_time = format_timestamp()
    emit('log', {'message': 'Conectado ao monitoramento em tempo real', 'level': 'info', 'timestamp': current_time})

if __name__ == '__main__':
    # Executar o monitoramento em thread separada
    monitor_thread = threading.Thread(target=run_monitoring)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Inicia o servidor Flask com SocketIO
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)