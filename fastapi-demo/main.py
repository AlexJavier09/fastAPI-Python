from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
from scraper import scrape_profile  # Asegúrate de que scrape_profile acepte headers personalizados

app = FastAPI()

# Configura CORS si tu API se consume desde un frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Headers IDÉNTICOS a los de tu script local
SCRAPER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://www.encuentra24.com/",  # ¡Añade esto!
}

@app.get("/scrape")
def scrape(user_id: int = 465250, delay: float = 1.0, max_pages: int = 5):
    """
    Endpoint para scrapear encuentra24.com.
    Parámetros:
    - user_id: ID del perfil (ej: 465250).
    - delay: Segundos entre requests (evita baneos).
    - max_pages: Límite de páginas a scrapear.
    """
    try:
        # Pasa los headers personalizados a scrape_profile
        rows = scrape_profile(user_id, delay=delay, max_pages=max_pages, headers=SCRAPER_HEADERS)
        return {
            "success": True,
            "data": rows,
            "count": len(rows)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al scrapear: {str(e)}"
        )