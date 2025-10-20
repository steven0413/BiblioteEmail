FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    unixodbc-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY app/ ./app/

# Puerto expuesto (Railway usa variable PORT)
EXPOSE $PORT

# Comando para Railway
CMD uvicorn app.main:app --host=0.0.0.0 --port=${PORT:-8000}