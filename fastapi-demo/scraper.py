import csv
import re
import time
from urllib.parse import urljoin

from lxml import html

# --- Selenium ---
import os
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE = "https://www.encuentra24.com"
PROFILE_URL_TMPL = BASE + "/costa-rica-es/user/profile/id/{user_id}?page={page}"

CSV_HEADERS = [
    "id", "titulo", "ubicacion", "descripcion", "link",
    "precio", "moneda", "area", "habitaciones", "banos",
    "operacion", "propiedad"
]

# --------------------------------------------------------------------------------------
# Utilidades de limpieza / normalización (idénticas a tu script original)
# --------------------------------------------------------------------------------------

def detect_moneda(precio_text):
    t = (precio_text or "").lower()
    if "$" in t or "usd" in t or "us$" in t:
        return "USD"
    if "₡" in t or "crc" in t or "colones" in t:
        return "CRC"
    if "€" in t or "eur" in t:
        return "EUR"
    return ""

def norm_space(s):
    return re.sub(r"\s+", " ", s or "").strip()

def clean_precio(precio_text):
    match = re.search(r'[\d\.,]+', precio_text or "")
    return match.group(0) if match else ""

def clean_area(area_text):
    match = re.search(r'\d+', (area_text or "").replace(",", ""))
    return match.group(0) if match else ""

def extract_operacion_propiedad(href_path):
    operacion = ""
    propiedad = ""
    if not href_path:
        return operacion, propiedad

    parts = href_path.strip("/").split("/")
    if len(parts) >= 2 and parts[1].startswith("bienes-raices-"):
        segment = parts[1]

        if "alquiler" in segment:
            operacion = "alquiler"
        elif "venta" in segment:
            operacion = "venta"

        seg2 = segment.replace("bienes-raices-", "")
        seg2 = seg2.replace("alquiler-", "").replace("venta-", "")

        ignorar = {
            "de", "propiedades", "amueblados", "amueblado",
            "lujo", "linea", "blanca", "moderno", "nuevo",
            "nueva", "remodelado", "remodelada"
        }

        palabras = [p for p in seg2.split("-") if p not in ignorar and p != ""]
        base = palabras[0] if palabras else ""

        mapping = {
            "apartamentos": "apartamento",
            "apartamento": "apartamento",
            "casas": "casa",
            "casa": "casa",
            "cuartos": "cuarto",
            "cuarto": "cuarto",
            "oficinas": "oficina",
            "oficina": "oficina",
            "locales": "local",
            "local": "local",
            "lotes": "lote",
            "lote": "lote",
        }
        propiedad = mapping.get(base, base)

    return operacion, propiedad

def get_details_list_texts(tile):
    # Usamos lxml como antes (page_source -> lxml.html)
    lis = tile.xpath('.//ul[contains(@class,"d3-ad-tile__details")]/li')
    texts = [norm_space(li.xpath('string(.)')) for li in lis]
    return texts

def parse_tile(tile):
    titulo = norm_space("".join(tile.xpath('.//span[contains(@class,"d3-ad-tile__title")]/text()')))
    ubicacion = norm_space(tile.xpath('normalize-space(.//div[contains(@class,"d3-ad-tile__location")]/span)'))
    descripcion = norm_space(tile.xpath('normalize-space(.//div[contains(@class,"d3-ad-tile__short-description")])'))

    hrefs = tile.xpath('.//a[contains(@class,"d3-ad-tile__description")]/@href')
    if not hrefs:
        hrefs = tile.xpath('.//div[contains(@class,"d3-ad-tile__cover")]//a/@href')
    href = hrefs[0] if hrefs else ""
    full_link = urljoin(BASE, href) if href else ""

    precio_raw = norm_space(tile.xpath('normalize-space(.//div[contains(@class,"d3-ad-tile__price")])'))
    moneda = detect_moneda(precio_raw)
    precio = clean_precio(precio_raw)

    details = get_details_list_texts(tile)
    area = clean_area(details[0]) if len(details) >= 1 else ""
    habitaciones = details[1] if len(details) >= 2 else ""
    banos = details[-1] if len(details) >= 1 else ""

    operacion, propiedad = extract_operacion_propiedad(href)

    return {
        "titulo": titulo,
        "ubicacion": ubicacion,
        "descripcion": descripcion,
        "link": full_link,
        "precio": precio,
        "moneda": moneda,
        "area": area,
        "habitaciones": habitaciones,
        "banos": banos,
        "operacion": operacion,
        "propiedad": propiedad,
    }

# --------------------------------------------------------------------------------------
# Selenium setup
# --------------------------------------------------------------------------------------

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

def make_driver(headless=True, user_agent=DEFAULT_UA, proxy=None):
    """
    Crea y devuelve un Chrome headless (o visible) con opciones razonables.
    - Si pasas proxy="http://user:pass@host:port" lo aplica.
    """
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument(f"--user-agent={user_agent}")
    opts.add_argument("--lang=es-ES,es;q=0.9,en;q=0.8")
    if proxy:
        opts.add_argument(f"--proxy-server={proxy}")

    # Importante para algunos hostings/containers con poca memoria compartida
    # y para evitar bloqueos por automation flags
    opts.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(40)
    return driver

def wait_for_listings(driver, timeout=30):
    """
    Espera a que cargue el contenedor #currentlistings y al menos un tile.
    """
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#currentlistings"))
    )
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#currentlistings .d3-ad-tile"))
    )

def smart_scroll(driver, steps=4, pause=0.8):
    """
    Scrollea para disparar lazyloads si fuera necesario.
    """
    for _ in range(steps):
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight/2);")
        time.sleep(pause)

def make_driver(headless=True, user_agent=None, proxy=None):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=es-ES,es;q=0.9,en;q=0.8")

    if user_agent:
        opts.add_argument(f"--user-agent={user_agent}")
    if proxy:
        opts.add_argument(f"--proxy-server={proxy}")

    # 1) Si estamos en Docker Linux con chromedriver del sistema, úsalo
    chromedriver_bin = os.getenv("CHROMEDRIVER_BIN", "/usr/bin/chromedriver")
    if os.path.isfile(chromedriver_bin):
        service = Service(chromedriver_bin)
        driver = webdriver.Chrome(service=service, options=opts)
        driver.set_page_load_timeout(40)
        return driver

    # 2) Intento estándar (Selenium Manager) – en macOS suele bastar
    try:
        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(40)
        return driver
    except Exception as e1:
        print("Selenium Manager falló:", e1)

    # 3) Fallback con webdriver-manager (descarga el driver compatible)
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        driver.set_page_load_timeout(40)
        return driver
    except Exception as e2:
        raise RuntimeError(
            f"No se pudo inicializar ChromeDriver ni con Selenium Manager ni con webdriver-manager. "
            f"Detalles:\n- Selenium Manager: {e1}\n- webdriver-manager: {e2}"
        )
# --------------------------------------------------------------------------------------
# Scraper con Selenium
# --------------------------------------------------------------------------------------

def scrape_profile(user_id, delay=1.0, max_pages=200):
    all_rows = []
    counter = 1
    page = 1

    driver = make_driver(headless=True)

    while page <= max_pages:
        url = PROFILE_URL_TMPL.format(user_id=user_id, page=page)
        print(f"➡️ Página {page}: {url}")

        try:
            driver.get(url)
            time.sleep(2)  # deja que la página cargue JS
            doc = html.fromstring(driver.page_source)
        except Exception as e:
            print(f"⚠️ Error cargando {url}: {e}")
            break

        container = doc.xpath('//*[@id="currentlistings"]')
        if not container:
            print("⚠️ No se encontró #currentlistings. Detengo.")
            break
        container = container[0]

        tiles = container.xpath('.//div[@data-tracklisting and contains(@class,"d3-ad-tile")]')
        if not tiles:
            print("✔️ Sin más anuncios en esta página. Fin.")
            break

        for tile in tiles:
            row = parse_tile(tile)
            row["id"] = counter
            all_rows.append(row)
            counter += 1

        if len(tiles) < 20:
            print(f"✔️ Página {page} con {len(tiles)} anuncios (<20). Fin.")
            break

        page += 1
        time.sleep(delay)

    driver.quit()
    return all_rows

def save_csv(rows, filename="encuentra24_perfil.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "id": r.get("id",""),
                "titulo": r.get("titulo",""),
                "ubicacion": r.get("ubicacion",""),
                "descripcion": r.get("descripcion",""),
                "link": r.get("link",""),
                "precio": r.get("precio",""),
                "moneda": r.get("moneda",""),
                "area": r.get("area",""),
                "habitaciones": r.get("habitaciones",""),
                "banos": r.get("banos",""),
                "operacion": r.get("operacion",""),
                "propiedad": r.get("propiedad",""),
            })
    print(f"✅ CSV guardado: {filename}")

if __name__ == "__main__":
    USER_ID = 465250
    rows = scrape_profile(USER_ID)
    save_csv(rows, filename=f"enc24_{USER_ID}.csv")
