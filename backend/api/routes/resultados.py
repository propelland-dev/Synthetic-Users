"""
Endpoints para obtener resultados de entrevistas
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import json
from pathlib import Path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import STORAGE_DIR

router = APIRouter(prefix="/api/resultados", tags=["resultados"])


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
        for filepath in resultados_dir.glob("*_investigacion.json"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
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
                            if isinstance(step, dict) and step.get("type") == "survey" and isinstance(step.get("questions"), list):
                                num_preguntas += len(step.get("questions") or [])

                entrevistas.append({
                    "id": filepath.stem,
                    "timestamp": data.get("timestamp"),
                    "usuario": usuario_nombre,
                    "producto": (
                        data.get("producto", {}).get("nombre_producto")
                        or (data.get("producto", {}).get("descripcion", "")[:60] + ("…" if len(data.get("producto", {}).get("descripcion", "")) > 60 else ""))
                        or "N/A"
                    ),
                    "num_preguntas": num_preguntas
                })
        
        # Ordenar por timestamp descendente (más recientes primero)
        entrevistas.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
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
        
        # Buscar el archivo más reciente
        resultado_files = list(resultados_dir.glob("*_investigacion.json"))
        if not resultado_files:
            raise HTTPException(status_code=404, detail="No hay resultados disponibles")
        
        latest_file = max(resultado_files, key=lambda p: p.stat().st_mtime)
        
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
        filepath = resultados_dir / f"{rid}.json"
        
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Resultado no encontrado")
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resultado: {str(e)}")
