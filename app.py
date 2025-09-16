from flask import Flask, render_template
import csv

app = Flask(__name__)

def ler_log_links():
    links = []
    try:
        with open("log_links.txt", "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="|")
            next(reader)  # pular cabeçalho se tiver
            for row in reader:
                if len(row) < 5:
                    continue
                link = {
                    "url": row[0].strip(),
                    "timestamp": row[1].strip(),
                    "status": row[2].strip(),
                    "layout_ok": row[3].strip().lower() in ["true", "sim"],
                    "pattern_ok": row[4].strip().lower() in ["true", "sim"]
                }
                links.append(link)
    except Exception as e:
        print("Erro ao ler log_links.txt:", e)
    return links

@app.route("/")
def dashboard():
    links = ler_log_links()
    return render_template("dashboard.html", links=links)

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
