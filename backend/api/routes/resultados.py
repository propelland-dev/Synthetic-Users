"""
Endpoints para obtener resultados de entrevistas
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import json
from pathlib import Path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import STORAGE_DIR

router = APIRouter(prefix="/api/resultados", tags=["resultados"])


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
