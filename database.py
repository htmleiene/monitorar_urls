# database.py
import sqlite3
import json
from datetime import datetime
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path="monitoring.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Inicializa o banco de dados com as tabelas necessárias"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela de configurações
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Tabela de links monitorados
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monitored_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de resultados de verificação
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS check_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_id INTEGER,
                    status_code INTEGER,
                    layout_ok BOOLEAN,
                    pattern_ok BOOLEAN,
                    response_time REAL,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (link_id) REFERENCES monitored_links (id)
                )
            ''')
            
            # Tabela de logs do sistema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def add_monitored_link(self, url):
        """Adiciona um novo link para monitoramento"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO monitored_links (url) VALUES (?)",
                    (url,)
                )
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # URL já existe
                cursor.execute(
                    "SELECT id FROM monitored_links WHERE url = ?",
                    (url,)
                )
                return cursor.fetchone()[0] if cursor.fetchone() else None
    
    def add_check_result(self, link_id, status_code, layout_ok, pattern_ok, response_time=None):
        """Adiciona um resultado de verificação"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO check_results 
                (link_id, status_code, layout_ok, pattern_ok, response_time) 
                VALUES (?, ?, ?, ?, ?)''',
                (link_id, status_code, layout_ok, pattern_ok, response_time)
            )
            conn.commit()
            return cursor.lastrowid
    
    def add_system_log(self, level, message):
        """Adiciona um log do sistema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO system_logs (level, message) VALUES (?, ?)",
                (level, message)
            )
            conn.commit()
    
    def get_latest_check_results(self, limit=100):
        """Obtém os últimos resultados de verificação"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    ml.url,
                    cr.status_code,
                    cr.layout_ok,
                    cr.pattern_ok,
                    cr.checked_at,
                    cr.response_time
                FROM check_results cr
                JOIN monitored_links ml ON cr.link_id = ml.id
                ORDER BY cr.checked_at DESC
                LIMIT ?
            ''', (limit,))
            return cursor.fetchall()
    
    def get_link_stats(self, hours=24):
        """Obtém estatísticas dos links para as últimas X horas"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    ml.url,
                    COUNT(cr.id) as total_checks,
                    SUM(CASE WHEN cr.status_code = 200 THEN 1 ELSE 0 END) as success_checks,
                    AVG(cr.response_time) as avg_response_time,
                    MIN(cr.checked_at) as first_check,
                    MAX(cr.checked_at) as last_check
                FROM monitored_links ml
                LEFT JOIN check_results cr ON ml.id = cr.link_id 
                    AND cr.checked_at >= datetime('now', ?)
                GROUP BY ml.id
            ''', (f'-{hours} hours',))
            return cursor.fetchall()
    
    def get_dashboard_data(self):
        """Obtém dados para o dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Total de links monitorados
            cursor.execute("SELECT COUNT(*) as count FROM monitored_links")
            total_links = cursor.fetchone()['count']
            
            # Última verificação
            cursor.execute('''
                SELECT MAX(checked_at) as last_check 
                FROM check_results
            ''')
            last_check = cursor.fetchone()['last_check']
            
            # Status dos links na última verificação
            cursor.execute('''
                SELECT 
                    cr.status_code,
                    COUNT(*) as count
                FROM check_results cr
                WHERE cr.checked_at = (
                    SELECT MAX(checked_at) FROM check_results
                )
                GROUP BY cr.status_code
            ''')
            status_counts = cursor.fetchall()
            
            return {
                'totalLinks': total_links,
                'lastCheck': last_check,
                'statusCounts': {row['status_code']: row['count'] for row in status_counts}
            }

# Instância global do banco de dados
db = DatabaseManager()