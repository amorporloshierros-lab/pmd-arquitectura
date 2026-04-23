# ============================================
# Lucas Chatbot — Dockerfile para Railway
# ============================================
FROM python:3.11-slim

# Variables de build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Carpeta de trabajo
WORKDIR /app

# Instalar dependencias del sistema (curl para healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python primero (mejor caching de capas)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiar el código
COPY . .

# Asegurar que existe la carpeta de logs (Railway la borra entre deploys)
RUN mkdir -p logs/leads credentials

# Railway inyecta la variable PORT dinámicamente
# Defaulteamos a 8000 si se corre local
ENV HOST=0.0.0.0 \
    PORT=8000

# Exponer puerto (más decorativo que funcional con Railway)
EXPOSE 8000

# Healthcheck para que Railway sepa si la app está viva
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Arrancar uvicorn directamente (más eficiente que python main.py en producción)
# El --host 0.0.0.0 es OBLIGATORIO en contenedores
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
