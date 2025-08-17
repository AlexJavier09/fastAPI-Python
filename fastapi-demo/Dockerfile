# Imagen base
FROM python:3.11-slim

# Config básica de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Instalar Chromium, Chromedriver y dependencias gráficas + utilidades
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    ca-certificates \
    curl \
    # Fuentes (para que no fallen renderizados)
    fonts-liberation \
    fonts-noto \
    fonts-noto-color-emoji \
    # Librerías que Chromium suele requerir
    libglib2.0-0 \
    libnss3 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxext6 \
    libxrender1 \
    libxkbcommon0 \
    libgbm1 \
    libgtk-3-0 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libpango-1.0-0 \
    libdbus-1-3 \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

# Rutas útiles para Selenium en contenedor
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver

# App
WORKDIR /app

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY . .

# Usuario no-root por seguridad
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Puerto coherente con Uvicorn
EXPOSE 8000
ENV PORT=8000

# Arranque de FastAPI
# OJO: asegúrate que tu archivo se llame app.py y tenga 'app = FastAPI()'
CMD ["uvicorn", "main:app", "--workers", "1", "--host", "0.0.0.0", "--port", "8000"]
