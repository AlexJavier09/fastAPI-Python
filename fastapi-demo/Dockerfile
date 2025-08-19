FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 👉 Añade chromium (el navegador) y dependencias de runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    ca-certificates curl unzip \
    fonts-liberation fonts-noto fonts-noto-color-emoji \
    libglib2.0-0 libnss3 libx11-6 libxcb1 libxcomposite1 libxdamage1 libxfixes3 \
    libxi6 libxrandr2 libxext6 libxrender1 libxkbcommon0 libgbm1 libgtk-3-0 \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libpango-1.0-0 libdbus-1-3 tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
ENV PORT=8000

CMD ["uvicorn", "main:app", "--workers", "1", "--host", "0.0.0.0", "--port", "8000"]
