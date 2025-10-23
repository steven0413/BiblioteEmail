# Dockerfile para Biblioteca Email Automation
# Imagen optimizada para producción en Azure

# POR QUÉ python:3.11-slim?
# - Python 3.14 tiene warnings de compatibilidad con Pydantic
# - Slim es 40% más pequeño que la imagen completa
# - Tiene todo lo necesario sin bloat
# - Más seguro (menos superficie de ataque)
FROM python:3.11-slim

# Dependencias del sistema - SOLO las necesarias
# gcc, g++: Para compilar pyodbc (necesario para Azure SQL)
# unixodbc-dev: Controladores ODBC para SQL Server
# curl: Para health checks y debugging
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    unixodbc-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*  # Limpiar cache para imagen más pequeña

# Directorio de trabajo
WORKDIR /app

# Dependencias Python - copiar primero para mejor cache
# Estrategia: requirements primero, luego código
# Así cuando cambie el código, no reinstalamos dependencias
COPY requirements.txt .

# Instalación limpia de dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación - solo lo necesario
# Nota: No copiamos tests/, docs/, etc. para imagen más limpia
COPY app/ ./app/

# Puerto - flexible para diferentes hosts
# Azure App Service usa variable PORT, local usa 8000
EXPOSE $PORT

# 🚀 Comando de inicio - simple y efectivo
# Usamos variables de entorno para flexibilidad
# No usamos --reload en producción (solo en desarrollo)
CMD uvicorn app.main:app --host=0.0.0.0 --port=${PORT:-8000}