# app.py
from fastapi import FastAPI
from scraper import scrape_profile

app = FastAPI()

@app.get("/scrape")
def scrape(user_id: int = 465250):
    """
    Endpoint para scrapear un perfil de encuentra24 por user_id
    Ejemplo:
    GET /scrape?user_id=465250
    """
    rows = scrape_profile(user_id)
    return rows