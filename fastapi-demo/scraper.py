import csv
import re
import time
from urllib.parse import urljoin
import requests
from lxml import html

BASE = "https://www.encuentra24.com"
PROFILE_URL_TMPL = BASE + "/costa-rica-es/user/profile/id/{user_id}?page={page}"

import random
HEADERS
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
]

CSV_HEADERS = [
    "id", "titulo", "ubicacion", "descripcion", "link",
    "precio", "moneda", "area", "habitaciones", "banos",
    "operacion", "propiedad"
]

def detect_moneda(precio_text):
    t = precio_text.lower()
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
    match = re.search(r'[\d\.,]+', precio_text)
    return match.group(0) if match else ""

def clean_area(area_text):
    match = re.search(r'\d+', area_text.replace(",", ""))
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

        # Palabras que ignoraremos
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

def scrape_profile(user_id, delay=1.0, max_pages=200, headers=None):
    if headers is None:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),  # Usa el User-Agent rotativo
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Referer": "https://www.encuentra24.com/",
        }
    
    all_rows = []
    counter = 1
    page = 1

    while page <= max_pages:
        url = PROFILE_URL_TMPL.format(user_id=user_id, page=page)
        print(f"➡️ Página {page}: {url}")
        
        # ¡CORRECCIÓN CLAVE! Usa el parámetro `headers` (no la variable global HEADERS)
        r = requests.get(url, headers=headers, timeout=20)  # <<-- Cambia HEADERS por headers
        
        if r.status_code != 200:
            print(f"⚠️ HTTP {r.status_code} en {url}. Detengo.")
            break
        # ... (resto del código)

        doc = html.fromstring(r.content)
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
    USER_ID = 465250  # <-- cambia aquí el ID del usuario
    rows = scrape_profile(USER_ID)
    save_csv(rows, filename=f"enc24_{USER_ID}.csv")

