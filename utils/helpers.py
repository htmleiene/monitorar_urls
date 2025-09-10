import csv
import json
from datetime import datetime
from io import StringIO

def export_to_csv(links_data):
    """
    Exporta os dados dos links para formato CSV
    
    Args:
        links_data (list): Lista de dicionários com dados dos links
        
    Returns:
        str: Dados em formato CSV
    """
    si = StringIO()
    cw = csv.writer(si)
    
    # Cabeçalho
    cw.writerow(['URL', 'Status', 'Layout OK', 'Padrão OK', 'Última Verificação'])
    
    # Dados
    for link in links_data:
        cw.writerow([
            link['url'],
            link['status'],
            'Sim' if link['layoutOk'] else 'Não',
            'Sim' if link['padraoOk'] else 'Não',
            link['timestamp']
        ])
    
    output = si.getvalue()
    si.close()
    
    return output

def read_log_file(log_file_path, lines=100):
    """
    Lê as últimas linhas de um arquivo de log
    
    Args:
        log_file_path (str): Caminho para o arquivo de log
        lines (int): Número de linhas a serem lidas (padrão: 100)
        
    Returns:
        list: Lista com as últimas linhas do log
    """
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            logs = f.readlines()
        return logs[-lines:] if len(logs) > lines else logs
    except FileNotFoundError:
        return ["Arquivo de log não encontrado"]
    except Exception as e:
        return [f"Erro ao ler arquivo de log: {str(e)}"]

def format_timestamp():
    """
    Retorna o timestamp atual formatado
    
    Returns:
        str: Timestamp no formato DD-MM-YYYY HH:MM
    """
    return datetime.now().strftime("%d-%m-%Y %H:%M")

def is_valid_url(url):
    """
    Verifica se uma URL é válida
    
    Args:
        url (str): URL a ser validada
        
    Returns:
        bool: True se a URL for válida, False caso contrário
    """
    from urllib.parse import urlparse
    
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def calculate_uptime_percentage(log_entries):
    """
    Calcula a porcentagem de uptime com base nas entradas de log
    
    Args:
        log_entries (list): Lista de entradas de log
        
    Returns:
        float: Porcentagem de uptime
    """
    if not log_entries:
        return 100.0
    
    success_count = sum(1 for entry in log_entries if '200' in entry or 'sucesso' in entry.lower())
    total_count = len(log_entries)
    
    return (success_count / total_count) * 100 if total_count > 0 else 100.0

def format_bytes(size):
    """
    Formata um tamanho em bytes para uma string legível
    
    Args:
        size (int): Tamanho em bytes
        
    Returns:
        str: Tamanho formatado (ex: "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"