# Imagen base ligera con Python 3.11
FROM python:3.11-slim

# Instalar dependencias del sistema necesarias para lxml
RUN apt-get update && apt-get install -y \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de la app
WORKDIR /app

# Copiar archivos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000


# Comando para correr FastAPI con Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]



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

