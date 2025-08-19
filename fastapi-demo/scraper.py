import os
import re
import time
import zipfile
from urllib.parse import urljoin

import requests
from lxml import html

# Selenium (undetected-chromedriver)
import undetected_chromedriver as uc
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ==========================
# Config base
# ==========================

BASE = "https://www.encuentra24.com"
PROFILE_URL_TMPL = BASE + "/costa-rica-es/user/profile/id/{user_id}?page={page}"

CSV_HEADERS = [
    "id", "titulo", "ubicacion", "descripcion", "link",
    "precio", "moneda", "area", "habitaciones", "banos",
    "operacion", "propiedad"
]

# User-Agent normal (evita "HeadlessChrome")
NORMAL_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Lee proxy de entorno si está definido (formato Decodo: host:port:user:pass)
ENV_PROXY = os.getenv("PROXY_URL")  # ejemplo: "pa.decodo.com:20001:USER:PASS"


# ==========================
# Helpers de limpieza/parseo
# ==========================

def norm_space(s):
    return re.sub(r"\s+", " ", s or "").strip()

def detect_moneda(precio_text):
    t = (precio_text or "").lower()
    if "$" in t or "usd" in t or "us$" in t:
        return "USD"
    if "₡" in t or "crc" in t or "colones" in t:
        return "CRC"
    if "€" in t or "eur" in t:
        return "EUR"
    return ""

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


# ==========================
# Selenium + Proxy Decodo
# ==========================

def _build_proxy_extension_for_auth(host, port, user, password, pluginfile="proxy_auth_plugin.zip"):
    """Crea extensión de Chrome para configurar proxy con AUTH (http) y evitar prompt de login."""
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": { "scripts": ["background.js"] }
    }"""

    background_js = f"""
    var config = {{
        mode: "fixed_servers",
        rules: {{
            singleProxy: {{
                scheme: "http",
                host: "{host}",
                port: parseInt({port})
            }},
            bypassList: ["localhost"]
        }}
    }};
    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function(){{}});
    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{user}",
                password: "{password}"
            }}
        }};
    }}
    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {{urls: ["<all_urls>"]}},
        ["blocking"]
    );
    """

    with zipfile.ZipFile(pluginfile, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return pluginfile


def make_driver(headless=True, user_agent=NORMAL_UA, proxy_str=ENV_PROXY):
    """
    Arranca Chrome stealth (undetected-chromedriver).
    - proxy_str (opcional): "host:port:user:pass" (formato Decodo)
    """
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=es-ES,es;q=0.9,en;q=0.8")
    options.add_argument("--disable-blink-features=AutomationControlled")
    if user_agent:
        options.add_argument(f"--user-agent={user_agent}")

    # Proxy con auth:
    if proxy_str:
        try:
            host, port, user, password = proxy_str.split(":")
            # Importante: no usamos --proxy-server con user:pass porque Chrome pediría prompt.
            # En su lugar, cargamos una extensión que configura el proxy y envía auth.
            pluginfile = _build_proxy_extension_for_auth(host, port, user, password)
            options.add_extension(pluginfile)
        except Exception as e:
            print(f"[Proxy] formato inválido '{proxy_str}': {e}. Continuando sin proxy.")
            proxy_str = None

    driver = uc.Chrome(options=options, headless=headless)
    driver.set_page_load_timeout(60)
    return driver


# ==========================
# Utilidades Selenium/Red
# ==========================

def wait_ready(driver, timeout=40):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

def try_accept_cookies(driver):
    # Fallback genérico por texto (no CSS :contains)
    try:
        driver.execute_script("""
            const btns = [...document.querySelectorAll('button,a')];
            const b = btns.find(x => x.textContent.trim().toLowerCase().includes('acept'));
            if (b) b.click();
        """)
    except:
        pass

def smart_scroll(driver, steps=3, pause=0.7):
    for _ in range(steps):
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight/2);")
        time.sleep(pause)

def dump_debug(driver, page):
    try:
        with open(f"/app/debug_p{page}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"🧪 Dump guardado: /app/debug_p{page}.html")
    except Exception as e:
        print("No pude guardar dump:", e)

def _proxy_url_http_from_decodo(proxy_str):
    """Convierte 'host:port:user:pass' → 'http://user:pass@host:port' para requests."""
    host, port, user, password = proxy_str.split(":")
    return f"http://{user}:{password}@{host}:{port}"

def requests_with_driver_cookies_get(driver, full_url, proxy_str=ENV_PROXY):
    """GET con cookies del navegador + (opcional) proxy HTTP en requests."""
    sess = requests.Session()
    for c in driver.get_cookies():
        sess.cookies.set(c["name"], c["value"], domain=c.get("domain"))
    sess.headers.update({
        "User-Agent": NORMAL_UA,
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    })
    if proxy_str:
        try:
            proxy_http = _proxy_url_http_from_decodo(proxy_str)
            sess.proxies.update({"http": proxy_http, "https": proxy_http})
        except:
            pass
    r = sess.get(full_url, timeout=40)
    return r.text if r.status_code == 200 else ""

def get_ajax_url_or_guess(driver, user_id, page):
    """Primero intenta leer data-urlAjax; si no existe, hace guess a /user/ajax/..."""
    try:
        el = driver.find_element(By.CSS_SELECTOR, "#currentlistings")
        path = el.get_attribute("data-urlAjax")
        if path:
            return urljoin(BASE, path.replace("{page}", str(page)))
    except:
        pass
    guess = f"/costa-rica-es/user/ajax/id/{user_id}/page/{page}"
    return urljoin(BASE, guess)


# ==========================
# SCRAPE PRINCIPAL
# ==========================

def scrape_profile(user_id, delay=1.2, max_pages=200, headless=True, proxy_str=ENV_PROXY):
    """
    Scrapea el perfil (paginado) de Encuentra24:
    - Usa undetected-chromedriver (stealth)
    - Acepta cookies, scroll, esperas
    - Fallback AJAX con cookies si no hay #currentlistings
    - Dump de HTML si hay bloqueo (Cloudflare)

    Retorna: lista de dicts con anuncios
    """
    driver = make_driver(headless=headless, proxy_str=proxy_str)
    all_rows, counter, page = [], 1, 1

    try:
        while page <= max_pages:
            url = PROFILE_URL_TMPL.format(user_id=user_id, page=page)
            print(f"➡️ Página {page}: {url}")

            # Navegación con reintentos suaves
            ok = False
            for i in range(1, 4):
                try:
                    driver.get(url)
                    ok = True
                    break
                except Exception as e:
                    wait = 1.0 * i
                    print(f"Intento {i}/3 falló al cargar {url}: {e}. Reintentando en {wait:.1f}s")
                    time.sleep(wait)
            if not ok:
                dump_debug(driver, page)
                print("⚠️ No se pudo cargar la página. Detengo.")
                break

            wait_ready(driver, 40)
            try_accept_cookies(driver)
            smart_scroll(driver, steps=3, pause=0.7)

            # 1) Intento DOM renderizado
            doc = html.fromstring(driver.page_source)
            container = doc.xpath('//*[@id="currentlistings"]')
            if container:
                tiles = container[0].xpath('.//div[@data-tracklisting and contains(@class,"d3-ad-tile")]')
            else:
                tiles = []

            # 2) Fallback AJAX si no hay tiles en DOM
            if not tiles:
                ajax_url = get_ajax_url_or_guess(driver, user_id, page)
                html_ajax = requests_with_driver_cookies_get(driver, ajax_url, proxy_str=proxy_str)
                if not html_ajax:
                    dump_debug(driver, page)
                    print("⚠️ No se encontró #currentlistings ni AJAX válido. Detengo.")
                    break
                doc = html.fromstring(html_ajax)
                tiles = doc.xpath('.//div[@data-tracklisting and contains(@class,"d3-ad-tile")]')

            if not tiles:
                dump_debug(driver, page)
                print("✔️ Sin más anuncios o markup distinto. Fin.")
                break

            for tile in tiles:
                row = parse_tile(tile)
                row["id"] = counter
                all_rows.append(row)
                counter += 1

            # Heurística de última página
            if len(tiles) < 20:
                print(f"✔️ Página {page} con {len(tiles)} anuncios (<20). Fin.")
                break

            page += 1
            time.sleep(delay)

    finally:
        try:
            driver.quit()
        except:
            pass

    return all_rows
