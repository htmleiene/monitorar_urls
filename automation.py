# automation.py (atualizado)
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from database import db

BASE_URL = "https://www.inspirali.com/portfolio/"

def coletar_links_selenium():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(BASE_URL)
    
    wait = WebDriverWait(driver, 10)
    todos_links = set()

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.elementor-button-link")))
        
        page = 1
        max_pages = 20
        
        while page <= max_pages:
            print(f"Coletando links da página {page}...")
            
            try:
                botoes = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.elementor-button-link")))
                
                for botao in botoes:
                    try:
                        href = botao.get_attribute("href")
                        if href:
                            todos_links.add(href.strip())
                    except StaleElementReferenceException:
                        continue
                
            except (TimeoutException, NoSuchElementException):
                break
            
            # Tenta ir para a próxima página
            try:
                next_selectors = [
                    ".jet-filters-pagination__item.next",
                    ".elementor-pagination .next",
                    "a.next",
                    ".next.page-numbers",
                    ".pagination-next",
                    "[aria-label='Next']",
                    "[aria-label='Próximo']"
                ]
                
                next_button = None
                for selector in next_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements and elements[0].is_displayed() and elements[0].is_enabled():
                            next_button = elements[0]
                            break
                    except:
                        continue
                
                if next_button:
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(3)
                    page += 1
                else:
                    break
                    
            except Exception:
                break
                
    except Exception as e:
        db.add_system_log('ERROR', f"Erro durante coleta de links: {str(e)}")
    finally:
        driver.quit()
    
    return todos_links

def testar_link(url):
    start_time = time.time()
    try:
        r = requests.get(url, timeout=10)
        response_time = time.time() - start_time
        status = r.status_code
        if status == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            layout_ok = bool(soup.find("head") and soup.find("body"))
        else:
            layout_ok = False
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
        links = coletar_links_selenium()
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