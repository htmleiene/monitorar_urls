from flask import Flask, render_template, jsonify, send_file
import threading
import time
import json
from datetime import datetime
from automation import coletar_links_selenium, testar_link, LOG_FILE

app = Flask(__name__)

# Dados em memória (em produção, use um banco de dados)
monitoring_data = {
    'totalLinks': 0,
    'status200': 0,
    'statusError': 0,
    'lastCheck': '--:--:--',
    'links': []
}

def run_monitoring():
    """Executa o monitoramento em loop"""
    global monitoring_data
    
    while True:
        print("🔍 Coletando links com Selenium (headless)...")
        links = coletar_links_selenium()
        print(f"✅ {len(links)} links encontrados.\n")
        
        links_data = []
        status_200 = 0
        status_error = 0
        
        for link in links:
            url, status, layout_ok, padrao_ok, ts = testar_link(link)
            links_data.append({
                'url': url,
                'status': status,
                'layoutOk': layout_ok,
                'padraoOk': padrao_ok,
                'timestamp': ts
            })
            
            if status == 200:
                status_200 += 1
            else:
                status_error += 1
        
        monitoring_data = {
            'totalLinks': len(links),
            'status200': status_200,
            'statusError': status_error,
            'lastCheck': datetime.now().strftime("%H:%M:%S"),
            'links': links_data
        }
        
        print("⏳ Aguardando 5 minutos antes da próxima checagem...\n")
        time.sleep(300)  # espera 5 min

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    return jsonify(monitoring_data)

@app.route('/api/export')
def export_data():
    """Exporta os dados para CSV"""
    import csv
    from io import StringIO
    
    si = StringIO()
    cw = csv.writer(si)
    
    # Cabeçalho
    cw.writerow(['URL', 'Status', 'Layout OK', 'Padrão OK', 'Última Verificação'])
    
    # Dados
    for link in monitoring_data['links']:
        cw.writerow([
            link['url'],
            link['status'],
            'Sim' if link['layoutOk'] else 'Não',
            'Sim' if link['padraoOk'] else 'Não',
            link['timestamp']
        ])
    
    output = si.getvalue()
    si.close()
    
    return send_file(
        StringIO(output),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'monitoramento_links_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/api/logs')
def get_logs():
    """Retorna o conteúdo do arquivo de log"""
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = f.readlines()
        return jsonify({'logs': logs[-100:]})  # Últimas 100 linhas
    except FileNotFoundError:
        return jsonify({'logs': []})

if __name__ == '__main__':
    # Executar o monitoramento em thread separada
    monitor_thread = threading.Thread(target=run_monitoring)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
