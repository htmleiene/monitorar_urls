from flask import Flask, render_template, jsonify
from database import db  # se quiser manter o dashboard
# import outras libs só se precisar do front

app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    try:
        dashboard_data = db.get_dashboard_data()
        return jsonify(dashboard_data)
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    # apenas front rodando
    app.run(host='0.0.0.0', port=5000, debug=True)
