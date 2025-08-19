import os
from fastapi import FastAPI, HTTPException
from scraper import scrape_profile, make_driver

app = FastAPI()

@app.get("/health/which")
def health_which():
    import shutil
    return {
        "chromium": shutil.which("chromium") or shutil.which("google-chrome") or "not-found",
        # undetected-chromedriver no requiere chromedriver binario,
        # pero mostramos si existe igualmente
        "chromedriver": shutil.which("chromedriver") or "not-found",
        "env": {
            "PROXY_URL": os.getenv("PROXY_URL", ""),
        }
    }

@app.get("/health/selenium")
def health_selenium():
    try:
        d = make_driver(headless=True)  # usará PROXY_URL si está en env
        d.get("https://httpbin.org/headers")
        ua = d.execute_script("return navigator.userAgent")
        html_length = len(d.page_source or "")
        d.quit()
        return {"ok": True, "userAgent": ua, "html_length": html_length}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/scrape")
def scrape(user_id: int, headless: bool = True, proxy: str | None = None):
    """
    Llama al scraper. Si 'proxy' viene en query, tiene prioridad sobre PROXY_URL (ENV).
    Formato de proxy: 'host:port:user:pass' (Decodo)
    """
    proxy_str = proxy if proxy else os.getenv("PROXY_URL")
    rows = scrape_profile(user_id=user_id, headless=headless, proxy_str=proxy_str)
    if not rows:
        raise HTTPException(status_code=502, detail="No se cargaron listings (Cloudflare/cookies/AJAX)")
    return rows
