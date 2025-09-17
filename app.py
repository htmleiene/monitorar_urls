import os
import time
import threading
import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify, send_file
from flask_socketio import SocketIO, emit
from io import BytesIO

from database import db
from automation import executar_monitoramento

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

    socketio.emit(
        "log",
        {"message": "Monitoramento parado", "level": "info"},
        namespace="/",
    )


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/status")
def get_status():
    """Retorna dados para o dashboard"""
    try:
        dashboard_data = db.get_dashboard_data()

        # Calcula totais
        status_200 = dashboard_data["statusCounts"].get(200, 0)
        status_error = sum(
            count for status, count in dashboard_data["statusCounts"].items() if status != 200
        )

        total_links = dashboard_data["totalLinks"]

        # Percentuais (evitando divisão por zero)
        success_percent = round((status_200 / total_links) * 100) if total_links > 0 else 0
        error_percent = round((status_error / total_links) * 100) if total_links > 0 else 0

        # Ajuste em caso de inconsistência
        if status_200 + status_error != total_links:
            status_200 = min(status_200, total_links)
            status_error = total_links - status_200
            success_percent = round((status_200 / total_links) * 100) if total_links > 0 else 0
            error_percent = round((status_error / total_links) * 100) if total_links > 0 else 0

        # Últimos resultados
        latest_results = db.get_latest_check_results(50)

        links_data = []
        for row in latest_results:
            links_data.append(
                {
                    "url": row["url"],
                    "status": row["status_code"],
                    "layoutOk": bool(row["layout_ok"]),
                    "padraoOk": bool(row["pattern_ok"]),
                    "timestamp": row["checked_at"],
                }
            )

        return jsonify(
            {
                "totalLinks": total_links,
                "status200": status_200,
                "statusError": status_error,
                "status200Percent": success_percent,
                "statusErrorPercent": error_percent,
                "lastCheck": dashboard_data["lastCheck"],
                "links": links_data,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/update")
def update_status():
    """Força uma atualização dos dados"""
    socketio.emit(
        "log",
        {"message": "Atualização manual iniciada", "level": "info"},
        namespace="/",
    )
    executar_monitoramento()
    return jsonify({"status": "success", "message": "Dados atualizados"})


@app.route("/api/export")
def export_data():
    """Exporta os dados para CSV"""
    try:
        results = db.get_latest_check_results(1000)

        output = BytesIO()
        output.write("URL,Status,Layout OK,Padrão OK,Tempo Resposta,Verificado Em\n".encode("utf-8"))

        for row in results:
            response_time = f"{row['response_time']:.2f}s" if row["response_time"] else "N/A"
            csv_line = (
                f"\"{row['url']}\",{row['status_code']},"
                f"{'Sim' if row['layout_ok'] else 'Não'},"
                f"{'Sim' if row['pattern_ok'] else 'Não'},"
                f"{response_time},\"{row['checked_at']}\"\n"
            )
            output.write(csv_line.encode("utf-8"))

        output.seek(0)

        return send_file(
            output,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"monitoramento_links_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.csv",
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/api/logs")
def get_logs():
    """Retorna os últimos logs"""
    try:
        with sqlite3.connect("monitoring.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT level, message, created_at 
                FROM system_logs 
                ORDER BY created_at DESC 
                LIMIT 100
            """
            )
            logs = cursor.fetchall()

            log_lines = [
                f"[{log['created_at']}] {log['level']}: {log['message']}" for log in logs
            ]
            return jsonify({"logs": log_lines})
    except Exception as e:
        return jsonify({"logs": [f"Erro ao ler logs: {str(e)}"]})


@app.route("/api/realtime-logs")
def get_realtime_logs():
    """Retorna todos os logs em tempo real"""
    try:
        with sqlite3.connect("monitoring.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT level, message, created_at 
                FROM system_logs 
                ORDER BY created_at ASC
            """
            )
            logs = cursor.fetchall()

            log_list = [
                {"level": log["level"], "message": log["message"], "timestamp": log["created_at"]}
                for log in logs
            ]
            return jsonify({"logs": log_list})
    except Exception as e:
        current_time = format_timestamp()
        return jsonify(
            {
                "logs": [
                    {
                        "level": "error",
                        "message": f"Erro ao ler logs: {str(e)}",
                        "timestamp": current_time,
                    }
                ]
            }
        )


@socketio.on("connect", namespace="/")
def handle_connect():
    """Cliente conectado via WebSocket"""
    current_time = format_timestamp()
    emit(
        "log",
        {"message": "Conectado ao monitoramento em tempo real", "level": "info", "timestamp": current_time},
    )


if __name__ == "__main__":
    # Inicia monitoramento em thread separada
    monitor_thread = threading.Thread(target=run_monitoring)
    monitor_thread.daemon = True
    monitor_thread.start()

    # Porta dinâmica para Render
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"

    print(f"✅ Iniciando servidor na porta {port}")

    socketio.run(app, host=host, port=port, debug=False, use_reloader=False)
