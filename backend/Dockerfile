# Usar una imagen ligera de Python
FROM python:3.11-slim

# Evitar que Python genere archivos .pyc y permitir logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar (asumiendo que se construye desde la raíz)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del backend
COPY backend/ ./backend/

# Configurar el PYTHONPATH para que los imports funcionen correctamente
ENV PYTHONPATH=/app/backend

# Exponer el puerto del API
EXPOSE 8000

# Comando para ejecutar la aplicación
# Nos movemos a la carpeta backend para que el comando uvicorn api.main:app funcione con los paths actuales
WORKDIR /app/backend
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
