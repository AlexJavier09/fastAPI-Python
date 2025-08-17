from fastapi import FastAPI
from scraper import scrape_profile  # 👈 usa la versión Selenium

app = FastAPI()

@app.get("/scrape")
def scrape(user_id: int = 465250, headless: bool = True):
    rows = scrape_profile(user_id=user_id, headless=headless)
    return rows
