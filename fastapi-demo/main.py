from fastapi import FastAPI
from scraper import scrape_profile, make_driver   # 👈 importa make_driver

app = FastAPI()

@app.get("/scrape")
def scrape(user_id: int = 465250, headless: bool = True):
    rows = scrape_profile(user_id=user_id)
    if not rows:
        raise HTTPException(status_code=502, detail="No se cargaron listings (#currentlistings ausente)")
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
        ua = d.execute_script("return navigator.userAgent")
        html_len = len(d.page_source or "")
        d.quit()
        return {"ok": True, "userAgent": ua, "html_length": html_len}
    except Exception as e:
        return {"ok": False, "error": str(e)}

