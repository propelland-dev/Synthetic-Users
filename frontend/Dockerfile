FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del frontend
COPY frontend/ ./frontend/

# Exponer el puerto de Streamlit
EXPOSE 8501

WORKDIR /app/frontend

# Configurar variable de entorno para conectar con el backend en la red de docker
# Por defecto apuntará al nombre del servicio en el compose
ENV API_BASE_URL=http://backend:8000

# Comando para ejecutar Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
