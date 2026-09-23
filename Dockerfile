# Imagen base homologada con tu entorno Conda local
FROM python:3.11.9-slim

# Variables de entorno para estabilidad del contenedor
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Instalación estandarizada de librerías C++ compartidas para Playwright RPA
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Inyección del stack congelado compatible con macOS Monterey
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Descarga e instalación de binarios Chromium para automatización headless
RUN playwright install chromium --with-deps

# Transferencia del código fuente del monorepo
COPY backend/ ./backend/

# Exposición del puerto estándar
EXPOSE 10000

# Arranque del motor ASGI Uvicorn desacoplado
CMD ["python", "backend/run.py"]
