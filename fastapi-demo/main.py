from fastapi import FastAPI
from scraper import scrape_profile  # 👈 usa la versión Selenium

app = FastAPI()

@app.get("/scrape")
def scrape(user_id: int = 465250):
    rows = scrape_profile(user_id=user_id)
    return rows

@app.get("/health/which")
def health_which():
    import shutil, os
    return {
        "chromium": shutil.which("chromium") or shutil.which("google-chrome") or "not-found",
        "chromedriver": shutil.which("chromedriver") or "not-found",
        "env": {"CHROME_BIN": os.getenv("CHROME_BIN"), "CHROMEDRIVER_BIN": os.getenv("CHROMEDRIVER_BIN")},
    }

@app.get("/health/selenium")
def health_selenium():
    try:
        d = make_driver(headless=True)
        d.get("https://httpbin.org/headers")
        t = d.title
        d.quit()
        return {"ok": True, "title": t}
    except Exception as e:
        return {"ok": False, "error": str(e)}
