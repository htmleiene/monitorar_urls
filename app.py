from flask import Flask, render_template, jsonify
import csv
from datetime import datetime

app = Flask(__name__)
LOG_FILE = "log_links.txt"

def ler_log_links():
    links = []
    status200 = 0
    statusErro = 0
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="|")
            for row in reader:
                if len(row) < 5:
                    continue
                url = row[0].strip()
                timestamp = row[1].strip()
                status = row[2].strip()
                layoutOk = row[3].strip().lower() in ["true", "sim"]
                padraoOk = row[4].strip().lower() in ["true", "sim"]
                if status == "200":
                    status200 += 1
                else:
                    statusErro += 1
                links.append({
                    "url": url,
                    "timestamp": timestamp,
                    "status": int(status) if status.isdigit() else "erro",
                    "layoutOk": layoutOk,
                    "padraoOk": padraoOk
                })
    except Exception as e:
        print("Erro ao ler log_links.txt:", e)
    
    total = len(links)
    return {
        "totalLinks": total,
        "status200": status200,
        "statusError": statusErro,
        "status200Percent": round((status200 / total * 100) if total else 0),
        "statusErrorPercent": round((statusErro / total * 100) if total else 0),
        "lastCheck": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "links": links
    }

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/status")
def api_status():
    data = ler_log_links()
    return jsonify(data)

@app.route("/api/realtime-logs")
def api_realtime_logs():
    logs = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="|")
            for row in reader:
                if len(row) < 5:
                    continue
                logs.append({
                    "timestamp": row[1].strip(),
                    "message": f"{row[0].strip()} | Status: {row[2].strip()} | Layout OK: {row[3].strip()} | Padrão OK: {row[4].strip()}",
                    "level": "info" if row[2].strip() == "200" else "error"
                })
    except Exception as e:
        logs.append({"timestamp": datetime.now().strftime("%d-%m-%Y %H:%M"), "message": str(e), "level": "error"})
    return jsonify({"logs": logs})

if __name__ == "__main__":
    app.run(debug=True)
