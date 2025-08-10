from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = FastAPI()

FIRECRAWL_URL = "http://n8n-restaurante-firecrawl.k6ptvf.easypanel.host/scrape?url="  # Ajusta host interno

@app.get("/scrape-encuentra24")
def scrape_encuentra24(user_id: str, page: int = 1):
    url = f"https://www.encuentra24.com/costa-rica-es/user/profile/id/{user_id}?page={page}"
    firecrawl_resp = requests.get(FIRECRAWL_URL + url)
    html = firecrawl_resp.text

    soup = BeautifulSoup(html, "html.parser")
    results = []

    for ann in soup.select(".ann-box-details"):
        link_tag = ann.select_one("a")
        nombre_tag = ann.select_one(".ann-title")
        desc_tag = ann.select_one(".ann-description")
        precio_tag = ann.select_one(".ann-price")
        ubic_tag = ann.select_one(".ann-location")
        info_text = ann.select_one(".ann-info").get_text(" ", strip=True) if ann.select_one(".ann-info") else ""

        link = urljoin("https://www.encuentra24.com", link_tag["href"]) if link_tag else ""
        nombre = nombre_tag.get_text(strip=True) if nombre_tag else ""
        descripcion = desc_tag.get_text(strip=True) if desc_tag else ""
        precio = precio_tag.get_text(strip=True) if precio_tag else ""
        ubicacion = ubic_tag.get_text(strip=True) if ubic_tag else ""

        cuartos = ""
        banos = ""
        metraje = ""
        if "hab" in info_text:
            cuartos = info_text.split("hab")[0].strip().split()[-1]
        if "ba" in info_text:
            banos = info_text.split("ba")[0].strip().split()[-1]
        if "m²" in info_text:
            metraje = info_text.split("m²")[0].strip().split()[-1]

        operacion = "Venta" if "venta" in nombre.lower() else "Alquiler" if "alquiler" in nombre.lower() else ""
        tipo = "Apartamento" if "apartamento" in nombre.lower() else "Casa" if "casa" in nombre.lower() else ""

        results.append({
            "link": link,
            "nombre": nombre,
            "descripcion": descripcion,
            "cuartos": cuartos,
            "banos": banos,
            "metraje": metraje,
            "ubicacion": ubicacion,
            "precio": precio,
            "operacion": operacion,
            "tipo": tipo
        })

    return results
