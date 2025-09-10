import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name='monitoring.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Inicializa o banco de dados com as tabelas necessárias"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela de links monitorados
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monitored_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # Tabela de resultados de verificação
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS check_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_id INTEGER NOT NULL,
                    status_code INTEGER,
                    layout_ok BOOLEAN,
                    pattern_ok BOOLEAN,
                    response_time REAL,
                    checked_at TEXT NOT NULL,
                    FOREIGN KEY (link_id) REFERENCES monitored_links (id)
                )
            ''')
            
            # Tabela de logs do sistema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
    
    def format_timestamp(self, dt=None):
        """Formata datetime para dd-mm-yyyy hh:mm"""
        if dt is None:
            dt = datetime.now()
        return dt.strftime("%d-%m-%Y %H:%M")
    
    def add_monitored_link(self, url):
        """Adiciona um link à lista de monitorados"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verifica se o link já existe
            cursor.execute('SELECT id FROM monitored_links WHERE url = ?', (url,))
            existing = cursor.fetchone()
            
            if existing:
                return existing['id']
            
            # Adiciona novo link
            created_at = self.format_timestamp()
            cursor.execute(
                'INSERT INTO monitored_links (url, created_at) VALUES (?, ?)',
                (url, created_at)
            )
            
            return cursor.lastrowid
    
    def add_check_result(self, link_id, status_code, layout_ok, pattern_ok, response_time):
        """Adiciona um resultado de verificação"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            checked_at = self.format_timestamp()
            cursor.execute('''
                INSERT INTO check_results 
                (link_id, status_code, layout_ok, pattern_ok, response_time, checked_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (link_id, status_code, layout_ok, pattern_ok, response_time, checked_at))
    
    def add_system_log(self, level, message):
        """Adiciona um log do sistema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            created_at = self.format_timestamp()
            cursor.execute(
                'INSERT INTO system_logs (level, message, created_at) VALUES (?, ?, ?)',
                (level, message, created_at)
            )
    
    def get_dashboard_data(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total de links únicos monitorados
            cursor.execute('SELECT COUNT(DISTINCT id) as count FROM monitored_links')
            total_links = cursor.fetchone()['count']
            
            # Contagem de status dos ÚLTIMOS resultados de cada link
            cursor.execute('''
                SELECT cr.status_code, COUNT(*) as count 
                FROM check_results cr
                INNER JOIN (
                    SELECT link_id, MAX(id) as max_id 
                    FROM check_results 
                    GROUP BY link_id
                ) latest ON cr.id = latest.max_id
                GROUP BY cr.status_code
            ''')
            status_counts = {}
            for row in cursor.fetchall():
                status_counts[row['status_code']] = row['count']
            
            # Última verificação
            cursor.execute('''
                SELECT checked_at 
                FROM check_results 
                ORDER BY id DESC 
                LIMIT 1
            ''')
            last_check_row = cursor.fetchone()
            last_check = last_check_row['checked_at'] if last_check_row else self.format_timestamp()
            
            return {
                'totalLinks': total_links,
                'statusCounts': status_counts,
                'lastCheck': last_check
            }
    
    def get_latest_check_results(self, limit=50):
        """Retorna os últimos resultados de verificação"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT ml.url, cr.status_code, cr.layout_ok, cr.pattern_ok, 
                       cr.response_time, cr.checked_at
                FROM check_results cr
                JOIN monitored_links ml ON cr.link_id = ml.id
                ORDER BY cr.id DESC
                LIMIT ?
            ''', (limit,))
            
            return cursor.fetchall()

# Instância global do banco de dados
db = Database()