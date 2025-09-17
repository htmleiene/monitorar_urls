import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
from database import db

BASE_URL = "https://www.inspirali.com/portfolio/"

def coletar_links_requests():
    """Coleta todos os links das páginas do portfolio usando Requests + BS4"""
    todos_links = set()
    page = 1
    max_pages = 20  # limite de páginas para evitar loop infinito

    while page <= max_pages:
        url = f"{BASE_URL}?page={page}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                break

            soup = BeautifulSoup(r.text, "html.parser")
            botoes = soup.select("a.elementor-button-link")

            if not botoes:
                break  # sem mais links, encerra

            for botao in botoes:
                href = botao.get("href")
                if href:
                    full_url = urljoin(BASE_URL, href.strip())
                    todos_links.add(full_url)

            # verifica se há botão "Próximo" (ou link de paginação)
            next_page = soup.select_one(".next, .pagination-next, [aria-label='Próximo']")
            if not next_page:
                break

            page += 1

        except requests.RequestException as e:
            db.add_system_log('ERROR', f"Erro ao coletar links na página {page}: {str(e)}")
            break

    return todos_links


def testar_link(url):
    """Testa um link e retorna status, layout e padrão"""
    start_time = time.time()
    try:
        r = requests.get(url, timeout=10)
        response_time = time.time() - start_time
        status = r.status_code
        layout_ok = bool(r.status_code == 200 and "<html" in r.text.lower())
        padrao_ok = "inspirali.com" in urlparse(url).netloc
    except requests.RequestException:
        response_time = time.time() - start_time
        status = "erro"
        layout_ok = False
        padrao_ok = False

    return url, status, layout_ok, padrao_ok, response_time


def executar_monitoramento():
    """Executa uma rodada de monitoramento e salva no banco"""
    try:
        db.add_system_log('INFO', "Iniciando coleta de links")
        links = coletar_links_requests()
        db.add_system_log('INFO', f"Encontrados {len(links)} links")

        for link in links:
            try:
                # Adiciona link ao banco se não existir
                link_id = db.add_monitored_link(link)

                # Testa o link
                url, status, layout_ok, padrao_ok, response_time = testar_link(link)

                # Salva resultado
                db.add_check_result(link_id, status, layout_ok, padrao_ok, response_time)

            except Exception as e:
                db.add_system_log('ERROR', f"Erro ao testar link {link}: {str(e)}")

        db.add_system_log('INFO', "Monitoramento concluído")

    except Exception as e:
        db.add_system_log('ERROR', f"Erro durante monitoramento: {str(e)}")
