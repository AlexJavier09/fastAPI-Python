from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from scraper import scrape_profile
import random

app = FastAPI()

# Configuración CORS (ajusta según tus necesidades)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Configuración avanzada de headers
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit...",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko..."
]

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://www.encuentra24.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests": "1"
}

@app.get("/scrape")
async def scrape_endpoint(
    user_id: int = 465250,
    delay: float = 3.0,  # Delay base aumentado
    max_pages: int = 3,  # Páginas reducidas por defecto
    use_proxy: bool = False  # Opción para proxies
):
    """
    Endpoint mejorado para scraping resistente
    Parámetros:
    - user_id: ID de perfil
    - delay: Segundos entre requests (3-5 recomendado)
    - max_pages: Máximo de páginas a scrapear
    - use_proxy: Usar proxies rotativos (requiere configuración)
    """
    try:
        # Configuración dinámica
        headers = BASE_HEADERS.copy()
        headers["User-Agent"] = random.choice(USER_AGENTS)
        
        # Parámetros extendidos para el scraper
        scraper_params = {
            "user_id": user_id,
            "delay": max(delay, 2.5),  # Mínimo 2.5 segundos
            "max_pages": min(max_pages, 5),  # Máximo 5 páginas
            "headers": headers,
            "use_proxy": use_proxy
        }

        # Ejecuta el scraper con configuración mejorada
        results = scrape_profile(**scraper_params)
        
        return {
            "status": "success",
            "user_id": user_id,
            "items": len(results),
            "data": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "scraping_failed",
                "message": str(e),
                "solution": "Try increasing delay or using proxies"
            }
        )

# Health Check
@app.get("/")
async def health_check():
    return {
        "status": "running",
        "service": "encuentra24-scraper",
        "recommended_delay": "3-5 seconds"
    }