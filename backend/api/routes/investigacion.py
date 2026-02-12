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
import threading
import uuid
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import STORAGE_DIR
from core.multi_research_engine import MultiResearchEngine
from core.llm_client import LLMClient
from core.models import UsuarioConfigV2
from core.planner import build_plan
from pydantic import ValidationError

router = APIRouter(prefix="/api/investigacion", tags=["investigacion"])

# -------------------------
# Job runner (cancelable)
# -------------------------

_JOBS_LOCK = threading.Lock()
_JOBS: Dict[str, Dict[str, Any]] = {}


def _job_get(run_id: str) -> Optional[Dict[str, Any]]:
    with _JOBS_LOCK:
        return _JOBS.get(run_id)


def _job_put(run_id: str, job: Dict[str, Any]) -> None:
    with _JOBS_LOCK:
        _JOBS[run_id] = job
        # Best-effort cleanup: keep last 20 jobs
        if len(_JOBS) > 20:
            # remove oldest by created_at
            items = sorted(_JOBS.items(), key=lambda kv: kv[1].get("created_at") or "")
            for rid, _ in items[:-20]:
                _JOBS.pop(rid, None)


def _job_append_event(job: Dict[str, Any], ev: Dict[str, Any]) -> None:
    if not isinstance(job, dict):
        return
    lock = job.get("lock")
    if lock is None:
        # create if missing
        lock = threading.Lock()
        job["lock"] = lock
    with lock:
        events = job.get("events")
        if not isinstance(events, list):
            events = []
            job["events"] = events
        events.append(ev)


def _load_latest_configs() -> tuple[UsuarioConfigV2, Dict[str, Any], Dict[str, Any], str, str, str, str]:
    """
    Load latest user/product/research configs from storage.
    Returns: (usuario_cfg_v2, producto_config, investigacion_config, investigacion_descripcion, estilo_investigacion, investigacion_objetivo, investigacion_preguntas)
    """
    usuarios_dir = STORAGE_DIR / "usuarios"
    productos_dir = STORAGE_DIR / "productos"
    investigaciones_dir = STORAGE_DIR / "investigaciones"

    # Auxiliar para cargar config.json o el más reciente
    def _load_config(directory: Path) -> Dict[str, Any]:
        cjson = directory / "config.json"
        if cjson.exists():
            with open(cjson, "r", encoding="utf-8") as f:
                return json.load(f)
        files = list(directory.glob("*_config.json"))
        if not files:
            return {}
        latest = max(files, key=lambda p: p.stat().st_mtime)
        with open(latest, "r", encoding="utf-8") as f:
            return json.load(f)

    usuario_data = _load_config(usuarios_dir)
    if not usuario_data:
        raise HTTPException(status_code=400, detail="No hay usuario configurado")
    
    usuario_config_raw = usuario_data.get("config") or {}
    try:
        if isinstance(usuario_config_raw, dict) and usuario_config_raw.get("mode") in {"single", "population"}:
            usuario_cfg_v2 = UsuarioConfigV2.model_validate(usuario_config_raw)
        else:
            usuario_cfg_v2 = UsuarioConfigV2.from_legacy(usuario_config_raw if isinstance(usuario_config_raw, dict) else {})
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Config de usuario inválida: {e}")

    producto_data = _load_config(productos_dir)
    if not producto_data:
        raise HTTPException(status_code=400, detail="No hay producto configurado")
    
    producto_config = producto_data.get("config") or {}
    if "nombre_producto" not in producto_config:
        producto_config["nombre_producto"] = "Producto"
    if "descripcion" not in producto_config:
        producto_config["descripcion"] = ""

    investigacion_data = _load_config(investigaciones_dir)
    if not investigacion_data:
        raise HTTPException(status_code=400, detail="No hay investigación configurada")
    
    investigacion_config = investigacion_data.get("config", {}) or {}
    investigacion_descripcion = investigacion_config.get("descripcion", "")
    investigacion_objetivo = investigacion_config.get("objetivo", "")
    investigacion_preguntas = investigacion_config.get("preguntas", "")

    if not any([
        isinstance(investigacion_descripcion, str) and investigacion_descripcion.strip(),
        isinstance(investigacion_objetivo, str) and investigacion_objetivo.strip(),
        isinstance(investigacion_preguntas, str) and investigacion_preguntas.strip()
    ]):
        raise HTTPException(status_code=400, detail="La investigación debe incluir al menos una descripción, objetivo o preguntas")
    
    estilo_investigacion = investigacion_config.get("estilo_investigacion", "Entrevista")
    if not isinstance(estilo_investigacion, str) or estilo_investigacion.strip() not in ["Cuestionario", "Entrevista"]:
        estilo_investigacion = "Entrevista"

    return usuario_cfg_v2, producto_config, investigacion_config, investigacion_descripcion, estilo_investigacion, investigacion_objetivo, investigacion_preguntas


def _normalize_llm_provider(value: Optional[str]) -> str:
    if not value:
        return "ollama"
    v = str(value).strip().lower()
    if v in {"llama local", "llama", "l\u200blla\u200bma local"}:
        return "ollama"
    if v in {"anythingllm", "anything llm", "anything-llm", "anything_llm"}:
        return "anythingllm"
    if v in {"huggingface", "hugging face", "hf"}:
        return "huggingface"
    if v in {"ollama", "llama-cpp-python", "anythingllm", "huggingface"}:
        return v
    return "ollama"


def _build_llm_client(system_config_dict: Dict[str, Any]) -> LLMClient:
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
        llm_config.update(
            {
                "base_url": system_config_dict.get("anythingllm_base_url"),
                "api_key": system_config_dict.get("anythingllm_api_key"),
                "workspace_slug": workspace_slug,
                "mode": mode,
            }
        )
    elif normalized_provider == "huggingface":
        llm_config.update(
            {
                "api_key": system_config_dict.get("huggingface_api_key"),
                "model": system_config_dict.get("huggingface_model"),
            }
        )
    return LLMClient(provider="llama", config=llm_config)


def _run_job(run_id: str, system_config_dict: Dict[str, Any]) -> None:
    job = _job_get(run_id)
    if not job:
        return
    cancel_event: threading.Event = job["cancel_event"]

    def cancelled() -> bool:
        return bool(cancel_event.is_set())

    try:
        _job_append_event(job, {"event": "start", "message": "Iniciando investigación..."})
        usuario_cfg_v2, producto_config, _inv_cfg, investigacion_descripcion, estilo_investigacion, investigacion_objetivo, investigacion_preguntas = _load_latest_configs()

        # Verificar que los prompts necesarios estén configurados
        required_prompts = ["prompt_perfil", "prompt_sintesis"]
        missing_prompts = [p for p in required_prompts if not system_config_dict.get(p)]
        if missing_prompts:
            _job_append_event(
                job,
                {
                    "event": "error",
                    "message": f"Faltan prompts en la configuración: {', '.join(missing_prompts)}. Ve a ⚙️ Configuración.",
                },
            )
            job["status"] = "error"
            return

        llm_client = _build_llm_client(system_config_dict)
        _job_append_event(job, {"event": "planning", "message": "Preparando plan..."})
        plan = build_plan(investigacion_descripcion, estilo_investigacion)
        respondents = [r.model_dump() for r in usuario_cfg_v2.to_effective_respondents()]
        _job_append_event(job, {"event": "planning_done", "message": f"Plan listo. Respondientes: {len(respondents)}."})

        engine = MultiResearchEngine(
            respondents=respondents,
            producto=producto_config,
            investigacion_descripcion=investigacion_descripcion,
            investigacion_objetivo=investigacion_objetivo,
            investigacion_preguntas=investigacion_preguntas,
            estilo_investigacion=estilo_investigacion,
            llm_client=llm_client,
            plan=plan,
            prompt_perfil=system_config_dict.get("prompt_perfil"),
            prompt_cuestionario=system_config_dict.get("prompt_cuestionario"),
            prompt_entrevista=system_config_dict.get("prompt_entrevista"),
            prompt_sintesis=system_config_dict.get("prompt_sintesis"),
        )

        for ev in engine.execute_stream(cancel_check=cancelled):
            if cancelled():
                _job_append_event(job, {"event": "cancelled", "message": "Investigación cancelada por el usuario."})
                job["status"] = "cancelled"
                return
            _job_append_event(job, ev if isinstance(ev, dict) else {"event": "progress", "message": str(ev)})
            if isinstance(ev, dict) and ev.get("event") == "done":
                job["status"] = "done"
                job["result"] = ev.get("result")
                return
            if isinstance(ev, dict) and ev.get("event") == "cancelled":
                job["status"] = "cancelled"
                return

        # If finished without done
        if job.get("status") not in {"done", "cancelled", "error"}:
            job["status"] = "done"
    except HTTPException as e:
        _job_append_event(job, {"event": "error", "message": str(e.detail)})
        job["status"] = "error"
    except Exception as e:
        import traceback
        error_msg = f"Error al ejecutar investigación: {str(e)}"
        print(f"[ERROR] {error_msg}")
        print(f"[TRACEBACK] {traceback.format_exc()}")
        _job_append_event(job, {"event": "error", "message": error_msg})
        job["status"] = "error"


class InvestigacionConfig(BaseModel):
    """Modelo de configuración de investigación"""
    descripcion: str
    objetivo: Optional[str] = ""
    preguntas: Optional[str] = ""
    estilo_investigacion: Optional[str] = None


class SystemConfig(BaseModel):
    """Modelo de configuración del sistema"""
    llm_provider: str
    temperatura: Optional[float] = None
    max_tokens: Optional[int] = None
    modelo_path: Optional[str] = None
    prompt_perfil: Optional[str] = None
    prompt_cuestionario: Optional[str] = None
    prompt_entrevista: Optional[str] = None
    prompt_sintesis: Optional[str] = None
    # AnythingLLM
    anythingllm_base_url: Optional[str] = None
    anythingllm_api_key: Optional[str] = None
    anythingllm_workspace_slug: Optional[str] = None
    anythingllm_mode: Optional[str] = None
    # Hugging Face
    huggingface_api_key: Optional[str] = None
    huggingface_model: Optional[str] = None


class JobStartRequest(BaseModel):
    system_config: Optional[SystemConfig] = None


class IniciarInvestigacionRequest(BaseModel):
    """Request para iniciar una investigación"""
    system_config: Optional[SystemConfig] = None


@router.post("/job/start")
def job_start(request: JobStartRequest):
    system_config_dict = request.system_config.dict() if request.system_config else {}
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:10]}"
    job = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "status": "running",
        "events": [],
        "result": None,
        "cancel_event": threading.Event(),
        "lock": threading.Lock(),
    }
    _job_put(run_id, job)
    t = threading.Thread(target=_run_job, args=(run_id, system_config_dict), daemon=True)
    job["thread"] = t
    t.start()
    return {"status": "success", "run_id": run_id}


@router.get("/job/{run_id}/events")
def job_events(run_id: str, cursor: int = 0):
    job = _job_get(run_id)
    if not job:
        raise HTTPException(status_code=404, detail="run_id no encontrado")
    lock = job.get("lock")
    if lock is None:
        lock = threading.Lock()
        job["lock"] = lock
    with lock:
        events = job.get("events") if isinstance(job.get("events"), list) else []
        c = max(0, int(cursor or 0))
        out = events[c:]
        new_cursor = len(events)
        return {"status": "success", "run_id": run_id, "job_status": job.get("status"), "cursor": new_cursor, "events": out}


@router.post("/job/{run_id}/cancel")
def job_cancel(run_id: str):
    job = _job_get(run_id)
    if not job:
        raise HTTPException(status_code=404, detail="run_id no encontrado")
    cancel_event: threading.Event = job["cancel_event"]
    cancel_event.set()
    job["status"] = "cancelled"
    _job_append_event(job, {"event": "cancel_requested", "message": "Cancelación solicitada."})
    return {"status": "success", "run_id": run_id, "job_status": job.get("status")}


@router.post("")
async def guardar_investigacion(config: InvestigacionConfig):
    """
    Guarda la configuración de la investigación en un archivo
    """
    try:
        investigaciones_dir = STORAGE_DIR / "investigaciones"
        investigaciones_dir.mkdir(parents=True, exist_ok=True)
        
        filename = "config.json"
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
    try:
        usuario_cfg_v2, producto_config, _inv_cfg, investigacion_descripcion, estilo_investigacion, investigacion_objetivo, investigacion_preguntas = _load_latest_configs()
        system_config_dict = request.system_config.dict() if request.system_config else {}
        llm_client = _build_llm_client(system_config_dict)
        
        # Verificar que los prompts necesarios estén configurados
        required_prompts = ["prompt_perfil", "prompt_sintesis"]
        missing_prompts = [p for p in required_prompts if not system_config_dict.get(p)]
        if missing_prompts:
            raise HTTPException(status_code=400, detail=f"Faltan prompts: {', '.join(missing_prompts)}")

        plan = build_plan(investigacion_descripcion, estilo_investigacion)
        respondents = [r.model_dump() for r in usuario_cfg_v2.to_effective_respondents()]

        engine = MultiResearchEngine(
            respondents=respondents,
            producto=producto_config,
            investigacion_descripcion=investigacion_descripcion,
            investigacion_objetivo=investigacion_objetivo,
            investigacion_preguntas=investigacion_preguntas,
            estilo_investigacion=estilo_investigacion,
            llm_client=llm_client,
            plan=plan,
            prompt_perfil=system_config_dict.get("prompt_perfil"),
            prompt_cuestionario=system_config_dict.get("prompt_cuestionario"),
            prompt_entrevista=system_config_dict.get("prompt_entrevista"),
            prompt_sintesis=system_config_dict.get("prompt_sintesis"),
        )
        resultados = engine.execute()
        return {"status": "success", "message": "Investigación completada", "resultados": resultados}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al ejecutar investigación: {str(e)}")


def _sse(data: Dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"data: {payload}\n\n"


@router.post("/iniciar_stream")
def iniciar_investigacion_stream(request: IniciarInvestigacionRequest):
    def gen():
        yield _sse({"event": "start", "message": "Iniciando investigación..."})
        try:
            usuario_cfg_v2, producto_config, _inv_cfg, investigacion_descripcion, estilo_investigacion, investigacion_objetivo, investigacion_preguntas = _load_latest_configs()
            system_config_dict = request.system_config.dict() if request.system_config else {}
            llm_client = _build_llm_client(system_config_dict)

            # Verificar prompts necesarios
            required_prompts = ["prompt_perfil", "prompt_sintesis"]
            missing_prompts = [p for p in required_prompts if not system_config_dict.get(p)]
            if missing_prompts:
                yield _sse({"event": "error", "message": f"Faltan prompts: {', '.join(missing_prompts)}"})
                return

            yield _sse({"event": "planning", "message": "Preparando plan..."})
            plan = build_plan(investigacion_descripcion, estilo_investigacion)
            respondents = [r.model_dump() for r in usuario_cfg_v2.to_effective_respondents()]
            yield _sse({"event": "planning_done", "message": f"Plan listo. Respondientes: {len(respondents)}."})

            engine = MultiResearchEngine(
                respondents=respondents,
                producto=producto_config,
                investigacion_descripcion=investigacion_descripcion,
                investigacion_objetivo=investigacion_objetivo,
                investigacion_preguntas=investigacion_preguntas,
                estilo_investigacion=estilo_investigacion,
                llm_client=llm_client,
                plan=plan,
                prompt_perfil=system_config_dict.get("prompt_perfil"),
                prompt_sintesis=system_config_dict.get("prompt_sintesis"),
            )

            for ev in engine.execute_stream():
                yield _sse(ev if isinstance(ev, dict) else {"event": "progress", "message": str(ev)})
                time.sleep(0.001)

        except Exception as e:
            yield _sse({"event": "error", "message": f"Error: {str(e)}"})

    return StreamingResponse(gen(), media_type="text/event-stream")
