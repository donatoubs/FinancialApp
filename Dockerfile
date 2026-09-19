# ==============================================================================
# Dockerfile Multietapa Optimizado y Seguro para FinancialApp (Python 3.12 + FastAPI)
# ==============================================================================

FROM python:3.12-slim AS base

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema necesarias para compilar paquetes si se requiere
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no root para máxima seguridad
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Directorio de trabajo
WORKDIR /app

# Copiar e instalar requerimientos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación y el frontend
COPY app/ ./app/
COPY frontend/ ./frontend/

# Cambiar propiedad de archivos al usuario no root
RUN chown -R appuser:appgroup /app

# Cambiar a usuario no root
USER appuser

# Exponer el puerto de la aplicación
EXPOSE 8000

# Healthcheck de contenedor Docker
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Comando de inicio en producción con Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
