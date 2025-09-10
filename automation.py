import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

LOG_FILE = "logs/logs_links.txt"
BASE_URL = "https://www.inspirali.com/portfolio/"

def coletar_links_selenium():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # modo headless
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(BASE_URL)
    time.sleep(3)  # espera inicial

    todos_links = set()

    while True:
        botoes = driver.find_elements(By.CSS_SELECTOR, "a.elementor-button-link")
        for botao in botoes:
            href = botao.get_attribute("href")
            if href:
                todos_links.add(href.strip())

        try:
            botao_next = driver.find_element(By.CSS_SELECTOR, ".jet-filters-pagination__item.next")
            driver.execute_script("arguments[0].click();", botao_next)
            time.sleep(3)
        except Exception:
            break

    driver.quit()
    return todos_links

def testar_link(url):
    try:
        r = requests.get(url, timeout=10)
        status = r.status_code
        if status == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            layout_ok = bool(soup.find("head") and soup.find("body"))
        else:
            layout_ok = False
        padrao_ok = "inspirali.com" in urlparse(url).netloc
    except requests.RequestException:
        status = "erro"
        layout_ok = False
        padrao_ok = False

    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M")
    return url, status, layout_ok, padrao_ok, timestamp
