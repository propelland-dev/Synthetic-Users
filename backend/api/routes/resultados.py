"""
Endpoints para obtener resultados de entrevistas
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
from pathlib import Path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import STORAGE_DIR, DEFAULT_PROMPTS
from core.llm_client import LLMClient

router = APIRouter(prefix="/api/resultados", tags=["resultados"])


class RefineRequest(BaseModel):
    text: str
    llm_provider: Optional[str] = "ollama"
    huggingface_api_key: Optional[str] = None
    huggingface_model: Optional[str] = None
    anythingllm_base_url: Optional[str] = None
    anythingllm_api_key: Optional[str] = None
    anythingllm_workspace_slug: Optional[str] = None


@router.post("/refinar")
async def refinar_texto(request: RefineRequest):
    """
    Limpia y refina un texto usando una llamada extra al LLM.
    """
    if not request.text or len(request.text) < 10:
        return {"status": "success", "refined_text": request.text}

    try:
        # Construir cliente LLM con la config proporcionada
        llm_config = {
            "provider": request.llm_provider,
            "temperature": 0.0,  # Máxima fidelidad
            "max_tokens": 4000
        }
        
        if request.llm_provider == "huggingface":
            llm_config.update({
                "api_key": request.huggingface_api_key,
                "model": request.huggingface_model
            })
        elif request.llm_provider == "anythingllm":
            llm_config.update({
                "base_url": request.anythingllm_base_url,
                "api_key": request.anythingllm_api_key,
                "workspace_slug": request.anythingllm_workspace_slug
            })

        client = LLMClient(provider="llama", config=llm_config)
        
        # Usar el prompt de refinado
        prompt = DEFAULT_PROMPTS.get("refinado", "{texto}").format(texto=request.text)
        
        refined = client.generate(prompt)
        
        return {
            "status": "success",
            "refined_text": refined.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al refinar texto: {str(e)}")


def _extract_summary(data: Dict[str, Any], filepath: Path) -> Dict[str, Any]:
    usuario_nombre = (
        data.get("usuario_nombre")
        or data.get("usuario", {}).get("nombre")
        or "N/A"
    )
    # num_preguntas: legacy `preguntas` o extraído del plan (survey)
    num_preguntas = 0
    if isinstance(data.get("preguntas"), list):
        num_preguntas = len(data.get("preguntas", []))
    elif isinstance(data.get("plan"), dict):
        steps = data.get("plan", {}).get("steps", [])
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict) and step.get("type") == "cuestionario" and isinstance(step.get("questions"), list):
                    num_preguntas += len(step.get("questions") or [])

    return {
        "id": filepath.parent.name if filepath.name == "analisis.json" else filepath.stem,
        "timestamp": data.get("timestamp"),
        "usuario": usuario_nombre,
        "producto": (
            data.get("producto", {}).get("nombre_producto")
            or (data.get("producto", {}).get("descripcion", "")[:60] + ("…" if len(data.get("producto", {}).get("descripcion", "")) > 60 else ""))
            or "N/A"
        ),
        "num_preguntas": num_preguntas
    }


@router.get("")
async def listar_resultados():
    """
    Lista todas las investigaciones ejecutadas
    """
    try:
        resultados_dir = STORAGE_DIR / "resultados"
        
        if not resultados_dir.exists():
            return {"resultados": []}
        
        entrevistas = []
        
        # 1. Buscar en carpetas (nuevo sistema)
        for d in resultados_dir.iterdir():
            if d.is_dir():
                analisis_file = d / "analisis.json"
                if analisis_file.exists():
                    try:
                        with open(analisis_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            entrevistas.append(_extract_summary(data, analisis_file))
                    except Exception:
                        continue
        
        # 2. Buscar archivos sueltos (legacy sistema)
        for filepath in resultados_dir.glob("*_investigacion.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    entrevistas.append(_extract_summary(data, filepath))
            except Exception:
                continue
        
        # Ordenar por timestamp descendente (más recientes primero)
        entrevistas.sort(key=lambda x: x.get("timestamp", "") or "", reverse=True)
        
        return {"resultados": entrevistas}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar resultados: {str(e)}")


@router.get("/latest")
async def obtener_resultado_latest():
    """
    Obtiene el resultado más reciente
    """
    try:
        resultados_dir = STORAGE_DIR / "resultados"
        
        if not resultados_dir.exists():
            raise HTTPException(status_code=404, detail="No hay resultados disponibles")
        
        # Buscar el archivo/carpeta más reciente
        # Consideramos tanto analisis.json dentro de carpetas como archivos sueltos
        all_files = []
        for d in resultados_dir.iterdir():
            if d.is_dir() and (d / "analisis.json").exists():
                all_files.append(d / "analisis.json")
        all_files.extend(list(resultados_dir.glob("*_investigacion.json")))
        
        if not all_files:
            raise HTTPException(status_code=404, detail="No hay resultados disponibles")
        
        latest_file = max(all_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resultado: {str(e)}")


@router.get("/{resultado_id}")
async def obtener_resultado(resultado_id: str):
    """
    Obtiene los resultados de una investigación específica
    """
    try:
        resultados_dir = STORAGE_DIR / "resultados"
        rid = resultado_id[:-5] if resultado_id.endswith(".json") else resultado_id
        
        # 1. Intentar como carpeta (nuevo sistema)
        folder_analisis = resultados_dir / rid / "analisis.json"
        if folder_analisis.exists():
            with open(folder_analisis, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # 2. Intentar como archivo suelto (legacy)
        filepath = resultados_dir / f"{rid}.json"
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # 3. Intentar con sufijo _investigacion (legacy alternativo)
        filepath_legacy = resultados_dir / f"{rid}_investigacion.json"
        if filepath_legacy.exists():
            with open(filepath_legacy, "r", encoding="utf-8") as f:
                return json.load(f)
        
        raise HTTPException(status_code=404, detail="Resultado no encontrado")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resultado: {str(e)}")


@router.get("/{resultado_id}/respondent/{respondent_id}")
async def obtener_respondiente(resultado_id: str, respondent_id: str):
    """
    Obtiene los detalles de un respondiente específico de una investigación
    """
    try:
        resultados_dir = STORAGE_DIR / "resultados"
        rid = resultado_id[:-5] if resultado_id.endswith(".json") else resultado_id
        
        # El respondent_id suele ser "respondent_01.json"
        # Buscamos en la carpeta del resultado
        filepath = resultados_dir / rid / "respondents" / respondent_id
        
        if not filepath.exists():
            # Intentar sin extensión si no la tiene
            if not respondent_id.endswith(".json"):
                filepath = resultados_dir / rid / "respondents" / f"{respondent_id}.json"
        
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        
        raise HTTPException(status_code=404, detail="Respondiente no encontrado")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener respondiente: {str(e)}")
