"""
Endpoints para gestión de usuarios sintéticos
"""
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, Optional
import json
from datetime import datetime
from pathlib import Path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import STORAGE_DIR
from core.models import UsuarioConfigV2
from pydantic import ValidationError

router = APIRouter(prefix="/api/usuario", tags=["usuario"])


@router.post("")
async def guardar_usuario(config: Dict[str, Any]):
    """
    Guarda la configuración del usuario sintético en un archivo
    """
    try:
        # Aceptar legacy (plano) o v2 (mode=single|population)
        if isinstance(config, dict) and "mode" in config:
            parsed = UsuarioConfigV2.model_validate(config)
            stored_config = parsed.model_dump()
        else:
            parsed = UsuarioConfigV2.from_legacy(config if isinstance(config, dict) else {})
            stored_config = parsed.model_dump()

        usuarios_dir = STORAGE_DIR / "usuarios"
        usuarios_dir.mkdir(parents=True, exist_ok=True)
        
        filename = "config.json"
        filepath = usuarios_dir / filename
        
        data = {
            "config": stored_config,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return {
            "status": "success",
            "message": "Configuración de usuario guardada",
            "file": filename
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Config de usuario inválida: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar usuario: {str(e)}")


@router.get("/latest")
async def obtener_usuario_latest():
    """
    Obtiene la configuración más reciente del usuario
    """
    try:
        usuarios_dir = STORAGE_DIR / "usuarios"
        
        if not usuarios_dir.exists():
            raise HTTPException(status_code=404, detail="No hay usuarios configurados")
        
        # Primero intentar cargar config.json (nueva versión sobrescribible)
        config_json = usuarios_dir / "config.json"
        if config_json.exists():
            with open(config_json, "r", encoding="utf-8") as f:
                return json.load(f)

        # Fallback: Buscar el archivo más reciente (legacy)
        config_files = list(usuarios_dir.glob("*_config.json"))
        if not config_files:
            raise HTTPException(status_code=404, detail="No hay usuarios configurados")
        
        latest_file = max(config_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener usuario: {str(e)}")
