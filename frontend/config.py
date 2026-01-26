"""
Configuración de la aplicación
"""
import os

# URL base de la API
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Endpoints de la API
API_ENDPOINTS = {
    "usuarios": f"{API_BASE_URL}/api/usuarios",
    "producto": f"{API_BASE_URL}/api/producto",
    "investigacion": f"{API_BASE_URL}/api/investigacion",
    "resultados": f"{API_BASE_URL}/api/resultados",
    "iniciar": f"{API_BASE_URL}/api/investigacion/iniciar"
}