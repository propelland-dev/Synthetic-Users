"""
Configuración de la aplicación
"""
import os
import requests
import json
from typing import Dict, Any, Optional

# URL base de la API
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Endpoints de la API
API_ENDPOINTS = {
    "usuario": f"{API_BASE_URL}/api/usuario",
    "producto": f"{API_BASE_URL}/api/producto",
    "producto_ficha": f"{API_BASE_URL}/api/producto/generar_ficha",
    "investigacion": f"{API_BASE_URL}/api/investigacion",
    "resultados": f"{API_BASE_URL}/api/resultados",
    "iniciar": f"{API_BASE_URL}/api/investigacion/iniciar",
    "iniciar_stream": f"{API_BASE_URL}/api/investigacion/iniciar_stream",
    "health": f"{API_BASE_URL}/health",
}

def verificar_backend() -> Optional[Dict[str, Any]]:
    """Verifica si el backend está accesible (health check)."""
    try:
        response = requests.get(API_ENDPOINTS["health"], timeout=3)
        response.raise_for_status()
        return {"status": "connected", "message": "Backend OK"}
    except Exception as e:
        return {"status": "disconnected", "message": f"Backend no accesible: {e}"}


def enviar_usuario(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Envía configuración de usuario a la API"""
    try:
        response = requests.post(API_ENDPOINTS["usuario"], json=config, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error al enviar usuario: {e}")
        return None


def enviar_producto(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Envía configuración de producto a la API"""
    try:
        response = requests.post(API_ENDPOINTS["producto"], json=config, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error al enviar producto: {e}")
        return None


def generar_ficha_producto(producto_config: Dict[str, Any], system_config: Dict[str, Any]) -> Optional[str]:
    """
    Genera la ficha del producto (Markdown) usando el backend + LLM.
    """
    try:
        payload = {"producto": producto_config, "system_config": system_config}
        response = requests.post(API_ENDPOINTS["producto_ficha"], json=payload, timeout=300)
        if response.status_code >= 400:
            try:
                err = response.json()
                raise Exception(err.get("detail") or err.get("message") or str(err))
            except Exception:
                raise Exception(response.text or f"HTTP {response.status_code}")
        data = response.json()
        if isinstance(data, dict) and data.get("status") == "success":
            ficha = data.get("ficha_producto")
            return str(ficha) if ficha is not None else ""
        return None
    except Exception as e:
        print(f"Error al generar ficha de producto: {e}")
        return None


def enviar_investigacion(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Envía configuración de investigación a la API"""
    try:
        response = requests.post(API_ENDPOINTS["investigacion"], json=config, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error al enviar investigación: {e}")
        return None


def iniciar_investigacion(system_config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Inicia una investigación en la API"""
    try:
        payload = {}
        if system_config:
            payload["system_config"] = system_config
        
        response = requests.post(API_ENDPOINTS["iniciar"], json=payload, timeout=300)
        if response.status_code >= 400:
            # Intentar devolver detalle del backend (FastAPI suele enviar {"detail": "..."} )
            try:
                return response.json()
            except Exception:
                return {"detail": response.text or f"HTTP {response.status_code}"}
        return response.json()
    except Exception as e:
        print(f"Error al iniciar investigación: {e}")
        return None


def iniciar_investigacion_stream(system_config: Optional[Dict[str, Any]] = None):
    """
    Inicia una investigación consumiendo progreso por SSE.

    Yields eventos dict:
      - {"event": "...", "message": "...", ...}
      - al final: {"event": "done", "result": {...}}
    """
    payload: Dict[str, Any] = {}
    if system_config:
        payload["system_config"] = system_config

    try:
        response = requests.post(API_ENDPOINTS["iniciar_stream"], json=payload, stream=True, timeout=300)
        if response.status_code >= 400:
            try:
                err = response.json()
            except Exception:
                err = {"detail": response.text or f"HTTP {response.status_code}"}
            yield {"event": "error", "message": err.get("detail") or err.get("message") or str(err)}
            return

        for raw in response.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            if not line.startswith("data:"):
                continue
            data = line.replace("data:", "", 1).strip()
            if not data:
                continue
            try:
                obj = json.loads(data)
                if isinstance(obj, dict):
                    yield obj
                else:
                    yield {"event": "progress", "message": str(obj)}
            except Exception:
                yield {"event": "progress", "message": data}
    except Exception as e:
        yield {"event": "error", "message": f"Error al iniciar investigación (stream): {e}"}


# Compatibilidad con versiones anteriores del frontend
def iniciar_entrevista(system_config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Alias legacy: iniciar investigación."""
    return iniciar_investigacion(system_config)


def obtener_resultados_latest() -> Optional[Dict[str, Any]]:
    """Obtiene el resultado más reciente de la API"""
    try:
        response = requests.get(f"{API_ENDPOINTS['resultados']}/latest", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error al obtener resultados: {e}")
        return None


def listar_resultados() -> Optional[Dict[str, Any]]:
    """Lista todos los resultados disponibles"""
    try:
        response = requests.get(API_ENDPOINTS["resultados"], timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error al listar resultados: {e}")
        return None


def verificar_ollama() -> Optional[Dict[str, Any]]:
    """Verifica el estado de la conexión con Ollama"""
    try:
        # Puede tardar un poco si Ollama está lento (timeout del backend + red)
        response = requests.get(f"{API_BASE_URL}/api/llm/status", timeout=12)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error al verificar Ollama: {e}")
        return None


def verificar_llm(system_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Verifica el estado del proveedor LLM seleccionado (Ollama o AnythingLLM)."""
    try:
        response = requests.post(f"{API_BASE_URL}/api/llm/status", json=system_config, timeout=12)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error al verificar LLM: {e}")
        return None