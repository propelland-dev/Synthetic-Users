"""
Endpoints para gestión de investigaciones/entrevistas
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from datetime import datetime
from pathlib import Path
import time
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import STORAGE_DIR
from core.research_engine import ResearchEngine
from core.multi_research_engine import MultiResearchEngine
from core.llm_client import LLMClient
from core.models import UsuarioConfigV2
from core.planner import build_plan
from pydantic import ValidationError

router = APIRouter(prefix="/api/investigacion", tags=["investigacion"])


class InvestigacionConfig(BaseModel):
    """Modelo de configuración de investigación"""
    descripcion: str


class SystemConfig(BaseModel):
    """Modelo de configuración del sistema"""
    llm_provider: str
    temperatura: Optional[float] = None
    max_tokens: Optional[int] = None
    modelo_path: Optional[str] = None
    prompt_perfil: Optional[str] = None
    prompt_investigacion: Optional[str] = None
    # AnythingLLM
    anythingllm_base_url: Optional[str] = None
    anythingllm_api_key: Optional[str] = None
    anythingllm_workspace_slug: Optional[str] = None
    anythingllm_mode: Optional[str] = None


class IniciarInvestigacionRequest(BaseModel):
    """Request para iniciar una investigación"""
    system_config: Optional[SystemConfig] = None

def _normalize_llm_provider(value: Optional[str]) -> str:
    """
    Normaliza valores de proveedor LLM recibidos desde el frontend.

    Históricamente el frontend enviaba etiquetas tipo 'LLaMA Local'.
    El backend/LLMClient espera 'ollama' (y en el futuro otros).
    """
    if not value:
        return "ollama"

    v = str(value).strip().lower()

    # Valores amigables/legacy del frontend
    if v in {"llama local", "llama", "l\u200blla\u200bma local"}:
        return "ollama"
    if v in {"anythingllm", "anything llm", "anything-llm", "anything_llm"}:
        return "anythingllm"

    # Valores esperados
    if v in {"ollama", "llama-cpp-python", "anythingllm"}:
        return v

    # Fallback conservador
    return "ollama"


@router.post("")
async def guardar_investigacion(config: InvestigacionConfig):
    """
    Guarda la configuración de la investigación en un archivo
    """
    try:
        investigaciones_dir = STORAGE_DIR / "investigaciones"
        investigaciones_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_config.json"
        filepath = investigaciones_dir / filename
        
        data = {
            "config": config.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return {
            "status": "success",
            "message": "Configuración de investigación guardada",
            "file": filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar investigación: {str(e)}")


@router.post("/iniciar")
def iniciar_investigacion(request: IniciarInvestigacionRequest):
    """
    Inicia una investigación completa:
    1. Carga usuario y producto más recientes
    2. Genera perfil detallado del usuario
    3. Ejecuta todas las preguntas
    4. Retorna resultados
    """
    try:
        # Cargar configuraciones más recientes
        usuarios_dir = STORAGE_DIR / "usuarios"
        productos_dir = STORAGE_DIR / "productos"
        investigaciones_dir = STORAGE_DIR / "investigaciones"
        
        # Cargar usuario
        usuario_files = list(usuarios_dir.glob("*_config.json"))
        if not usuario_files:
            raise HTTPException(status_code=400, detail="No hay usuario configurado")
        usuario_file = max(usuario_files, key=lambda p: p.stat().st_mtime)
        with open(usuario_file, "r", encoding="utf-8") as f:
            usuario_data = json.load(f)
        usuario_config_raw = usuario_data.get("config") or {}
        # Aceptar v2 o legacy
        try:
            if isinstance(usuario_config_raw, dict) and usuario_config_raw.get("mode") in {"single", "population"}:
                usuario_cfg_v2 = UsuarioConfigV2.model_validate(usuario_config_raw)
            else:
                usuario_cfg_v2 = UsuarioConfigV2.from_legacy(usuario_config_raw if isinstance(usuario_config_raw, dict) else {})
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"Config de usuario inválida: {e}")
        
        # Cargar producto
        producto_files = list(productos_dir.glob("*_config.json"))
        if not producto_files:
            raise HTTPException(status_code=400, detail="No hay producto configurado")
        producto_file = max(producto_files, key=lambda p: p.stat().st_mtime)
        with open(producto_file, "r", encoding="utf-8") as f:
            producto_data = json.load(f)
        producto_config = producto_data["config"]
        # Normalizar producto (nuevo esquema solo tiene 'descripcion')
        if "nombre_producto" not in producto_config:
            producto_config["nombre_producto"] = "Producto"
        if "descripcion" not in producto_config:
            producto_config["descripcion"] = ""
        
        # Cargar investigación
        investigacion_files = list(investigaciones_dir.glob("*_config.json"))
        if not investigacion_files:
            raise HTTPException(status_code=400, detail="No hay investigación configurada")
        investigacion_file = max(investigacion_files, key=lambda p: p.stat().st_mtime)
        with open(investigacion_file, "r", encoding="utf-8") as f:
            investigacion_data = json.load(f)
        investigacion_config = investigacion_data.get("config", {})
        investigacion_descripcion = investigacion_config.get("descripcion", "")
        if not isinstance(investigacion_descripcion, str) or not investigacion_descripcion.strip():
            raise HTTPException(status_code=400, detail="La investigación debe incluir una descripción")
        
        # Configurar LLM client
        system_config_dict = request.system_config.dict() if request.system_config else {}
        normalized_provider = _normalize_llm_provider(system_config_dict.get("llm_provider"))
        llm_config = {
            "provider": normalized_provider,
            "temperature": system_config_dict.get("temperatura", 0.7),
            "max_tokens": system_config_dict.get("max_tokens", 1000),
        }
        if normalized_provider == "anythingllm":
            workspace_slug = system_config_dict.get("anythingllm_workspace_slug")
            # Para este proyecto, usamos AnythingLLM como proxy de LLM.
            # El modo query tiende a devolver "no relevant information" si no hay chunks,
            # así que forzamos chat por defecto.
            mode = str(system_config_dict.get("anythingllm_mode") or "chat").strip().lower()
            if mode != "chat":
                mode = "chat"
            llm_config.update({
                "base_url": system_config_dict.get("anythingllm_base_url"),
                "api_key": system_config_dict.get("anythingllm_api_key"),
                "workspace_slug": workspace_slug,
                "mode": mode,
            })
        llm_client = LLMClient(provider="llama", config=llm_config)
        
        # Ejecutar investigación (resultado único)
        prompt_investigacion = system_config_dict.get("prompt_investigacion")
        if not prompt_investigacion:
            raise HTTPException(
                status_code=400,
                detail="Falta 'prompt_investigacion' en la configuración del sistema. Ve a ⚙️ Configuración y guarda la configuración del sistema.",
            )
        # Nuevo pipeline por etapas (soporta población y single)
        plan = build_plan(investigacion_descripcion)
        respondents = [r.model_dump() for r in usuario_cfg_v2.to_effective_respondents()]

        engine = MultiResearchEngine(
            respondents=respondents,
            producto=producto_config,
            investigacion_descripcion=investigacion_descripcion,
            llm_client=llm_client,
            plan=plan,
            prompt_perfil=system_config_dict.get("prompt_perfil"),
            prompt_sintesis=prompt_investigacion,
        )
        resultados = engine.execute()
        
        return {
            "status": "success",
            "message": "Investigación completada",
            "resultados": resultados
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al ejecutar investigación: {str(e)}")


def _sse(data: Dict[str, Any]) -> str:
    """
    Server-Sent Events helper.
    We only emit `data:` lines with JSON payload.
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f"data: {payload}\n\n"


@router.post("/iniciar_stream")
def iniciar_investigacion_stream(request: IniciarInvestigacionRequest):
    """
    Inicia una investigación completa, emitiendo progreso por SSE (text/event-stream).

    La respuesta es un stream de eventos JSON:
      - {event: "...", message: "...", ...}
      - Al final: {event: "done", result: { ...resultado final... }}
    """
    def gen():
        # ping inicial para que el cliente se enganche rápido
        yield _sse({"event": "start", "message": "Iniciando investigación..."})
        try:
            # Cargar configuraciones más recientes (igual que /iniciar)
            usuarios_dir = STORAGE_DIR / "usuarios"
            productos_dir = STORAGE_DIR / "productos"
            investigaciones_dir = STORAGE_DIR / "investigaciones"

            usuario_files = list(usuarios_dir.glob("*_config.json"))
            if not usuario_files:
                yield _sse({"event": "error", "message": "No hay usuario configurado"})
                return
            usuario_file = max(usuario_files, key=lambda p: p.stat().st_mtime)
            with open(usuario_file, "r", encoding="utf-8") as f:
                usuario_data = json.load(f)
            usuario_config_raw = usuario_data.get("config") or {}
            try:
                if isinstance(usuario_config_raw, dict) and usuario_config_raw.get("mode") in {"single", "population"}:
                    usuario_cfg_v2 = UsuarioConfigV2.model_validate(usuario_config_raw)
                else:
                    usuario_cfg_v2 = UsuarioConfigV2.from_legacy(usuario_config_raw if isinstance(usuario_config_raw, dict) else {})
            except ValidationError as e:
                yield _sse({"event": "error", "message": f"Config de usuario inválida: {e}"})
                return

            producto_files = list(productos_dir.glob("*_config.json"))
            if not producto_files:
                yield _sse({"event": "error", "message": "No hay producto configurado"})
                return
            producto_file = max(producto_files, key=lambda p: p.stat().st_mtime)
            with open(producto_file, "r", encoding="utf-8") as f:
                producto_data = json.load(f)
            producto_config = producto_data["config"]
            if "nombre_producto" not in producto_config:
                producto_config["nombre_producto"] = "Producto"
            if "descripcion" not in producto_config:
                producto_config["descripcion"] = ""

            investigacion_files = list(investigaciones_dir.glob("*_config.json"))
            if not investigacion_files:
                yield _sse({"event": "error", "message": "No hay investigación configurada"})
                return
            investigacion_file = max(investigacion_files, key=lambda p: p.stat().st_mtime)
            with open(investigacion_file, "r", encoding="utf-8") as f:
                investigacion_data = json.load(f)
            investigacion_config = investigacion_data.get("config", {})
            investigacion_descripcion = investigacion_config.get("descripcion", "")
            if not isinstance(investigacion_descripcion, str) or not investigacion_descripcion.strip():
                yield _sse({"event": "error", "message": "La investigación debe incluir una descripción"})
                return

            # Configurar LLM client
            system_config_dict = request.system_config.dict() if request.system_config else {}
            normalized_provider = _normalize_llm_provider(system_config_dict.get("llm_provider"))
            llm_config = {
                "provider": normalized_provider,
                "temperature": system_config_dict.get("temperatura", 0.7),
                "max_tokens": system_config_dict.get("max_tokens", 1000),
            }
            if normalized_provider == "anythingllm":
                workspace_slug = system_config_dict.get("anythingllm_workspace_slug")
                mode = str(system_config_dict.get("anythingllm_mode") or "chat").strip().lower()
                if mode != "chat":
                    mode = "chat"
                llm_config.update({
                    "base_url": system_config_dict.get("anythingllm_base_url"),
                    "api_key": system_config_dict.get("anythingllm_api_key"),
                    "workspace_slug": workspace_slug,
                    "mode": mode,
                })
            llm_client = LLMClient(provider="llama", config=llm_config)

            prompt_investigacion = system_config_dict.get("prompt_investigacion")
            if not prompt_investigacion:
                yield _sse({
                    "event": "error",
                    "message": "Falta 'prompt_investigacion' en la configuración del sistema. Ve a ⚙️ Configuración y guarda la configuración del sistema.",
                })
                return

            yield _sse({"event": "planning", "message": "Preparando plan..."})
            plan = build_plan(investigacion_descripcion)
            respondents = [r.model_dump() for r in usuario_cfg_v2.to_effective_respondents()]
            yield _sse({"event": "planning_done", "message": f"Plan listo. Respondientes: {len(respondents)}."})

            engine = MultiResearchEngine(
                respondents=respondents,
                producto=producto_config,
                investigacion_descripcion=investigacion_descripcion,
                llm_client=llm_client,
                plan=plan,
                prompt_perfil=system_config_dict.get("prompt_perfil"),
                prompt_sintesis=prompt_investigacion,
            )

            for ev in engine.execute_stream():
                yield _sse(ev if isinstance(ev, dict) else {"event": "progress", "message": str(ev)})
                # pequeño flush-friendly delay (evita que algunos proxys agrupen demasiado)
                time.sleep(0.001)

        except Exception as e:
            yield _sse({"event": "error", "message": f"Error al ejecutar investigación: {str(e)}"})

    return StreamingResponse(gen(), media_type="text/event-stream")
