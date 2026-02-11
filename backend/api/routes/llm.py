"""
Endpoints para verificación de LLM/Ollama
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from core.llm_client import LLMClient
from config import LLAMA_CONFIG

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/status")
async def verificar_ollama() -> Dict[str, Any]:
    """
    Verifica el estado de la conexión con Ollama
    """
    try:
        # Forzar el provider a ollama para esta verificación específica
        ollama_config = dict(LLAMA_CONFIG)
        ollama_config["provider"] = "ollama"
        llm_client = LLMClient(provider="llama", config=ollama_config)
        status = llm_client.check_connection()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al verificar Ollama: {str(e)}")


class LLMStatusRequest(BaseModel):
    """Request genérico para verificar un proveedor LLM."""
    llm_provider: str
    # AnythingLLM
    anythingllm_base_url: Optional[str] = None
    anythingllm_api_key: Optional[str] = None
    anythingllm_workspace_slug: Optional[str] = None
    anythingllm_mode: Optional[str] = None
    # Hugging Face
    huggingface_api_key: Optional[str] = None
    huggingface_model: Optional[str] = None


@router.post("/status")
async def verificar_llm(request: LLMStatusRequest) -> Dict[str, Any]:
    """
    Verifica el estado de la conexión con el proveedor seleccionado.

    - Para Ollama: usa la config del backend (env/`backend/config.py`)
    - Para AnythingLLM: usa parámetros enviados en el body
    """
    try:
        provider = (request.llm_provider or "ollama").strip().lower()

        if provider == "anythingllm":
            mode = str(request.anythingllm_mode or "chat").strip().lower()
            if mode != "chat":
                mode = "chat"
            llm_config = {
                "provider": "anythingllm",
                "base_url": request.anythingllm_base_url,
                "api_key": request.anythingllm_api_key,
                "workspace_slug": request.anythingllm_workspace_slug,
                "mode": mode,
            }
        elif provider == "huggingface":
            llm_config = {
                "provider": "huggingface",
                "model": request.huggingface_model,
            }
            # Solo enviar api_key si se proporcionó explícitamente (ahora se prefiere .env)
            if request.huggingface_api_key:
                llm_config["api_key"] = request.huggingface_api_key
        else:
            llm_config = dict(LLAMA_CONFIG)
            llm_config["provider"] = "ollama"

        llm_client = LLMClient(provider="llama", config=llm_config)
        return llm_client.check_connection()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al verificar LLM: {str(e)}")
