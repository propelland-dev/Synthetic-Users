"""
Configuración de la aplicación
"""
import os
import requests
import json
from typing import Dict, Any, Optional

# Configuración Hugging Face (Solo para UI)
HUGGINGFACE_UI_CONFIG = {
    "models_list": [
        "ServiceNow-AI/Apriel-1.6-15b-Thinker:together",
        "Qwen/Qwen3-4B-Thinking-2507:nscale",
        "meta-llama/Llama-3.1-8B-Instruct:novita",
        "microsoft/Phi-3.5-mini-instruct",
        "Qwen/Qwen2.5-7B-Instruct",
        "HuggingFaceH4/zephyr-7b-beta"
    ]
}

# URL base de la API
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# Endpoints de la API
API_ENDPOINTS = {
    "usuario": f"{API_BASE_URL}/api/usuario",
    "producto": f"{API_BASE_URL}/api/producto",
    "producto_ficha": f"{API_BASE_URL}/api/producto/generar_ficha",
    "investigacion": f"{API_BASE_URL}/api/investigacion",
    "resultados": f"{API_BASE_URL}/api/resultados",
    "iniciar": f"{API_BASE_URL}/api/investigacion/iniciar",
    "iniciar_stream": f"{API_BASE_URL}/api/investigacion/iniciar_stream",
    "job_start": f"{API_BASE_URL}/api/investigacion/job/start",
    "job_events": f"{API_BASE_URL}/api/investigacion/job",
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


def iniciar_investigacion_job(system_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Inicia una investigación como job cancelable. Devuelve run_id.
    """
    try:
        payload: Dict[str, Any] = {}
        if system_config:
            payload["system_config"] = system_config
        resp = requests.post(API_ENDPOINTS["job_start"], json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("status") == "success":
            return str(data.get("run_id") or "")
        return None
    except Exception as e:
        print(f"Error al iniciar investigación (job): {e}")
        return None


def obtener_job_events(run_id: str, cursor: int = 0) -> Optional[Dict[str, Any]]:
    """
    Recupera eventos del job desde un cursor.
    """
    try:
        url = f"{API_ENDPOINTS['job_events']}/{run_id}/events"
        resp = requests.get(url, params={"cursor": int(cursor or 0)}, timeout=20)
        if resp.status_code >= 400:
            try:
                return {"status": "error", "message": resp.json().get("detail")}
            except Exception:
                return {"status": "error", "message": resp.text}
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": f"Error al obtener eventos: {e}"}


def cancelar_investigacion_job(run_id: str) -> bool:
    try:
        url = f"{API_ENDPOINTS['job_events']}/{run_id}/cancel"
        resp = requests.post(url, timeout=20)
        return resp.status_code < 400
    except Exception as e:
        print(f"Error al cancelar job: {e}")
        return False


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
        # Aumentamos el timeout a 20s para dar margen al backend (que tiene 5s internos)
        response = requests.get(f"{API_BASE_URL}/api/llm/status", timeout=20)
        if response.status_code >= 400:
            return {"status": "error", "message": f"Error del backend ({response.status_code}): {response.text}"}
        return response.json()
    except Exception as e:
        print(f"Error al verificar Ollama: {e}")
        return {"status": "error", "message": f"Backend no accesible: {str(e)}"}


def verificar_llm(system_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Verifica el estado del proveedor LLM seleccionado (Ollama o AnythingLLM)."""
    try:
        # Aumentamos el timeout a 20s
        response = requests.post(f"{API_BASE_URL}/api/llm/status", json=system_config, timeout=20)
        if response.status_code >= 400:
            return {"status": "error", "message": f"Error del backend ({response.status_code}): {response.text}"}
        return response.json()
    except Exception as e:
        print(f"Error al verificar LLM: {e}")
        return {"status": "error", "message": f"Backend no accesible: {str(e)}"}
