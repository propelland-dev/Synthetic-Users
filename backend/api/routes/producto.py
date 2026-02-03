"""
Endpoints para gestión de productos
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
from datetime import datetime
from pathlib import Path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import STORAGE_DIR

router = APIRouter(prefix="/api/producto", tags=["producto"])


class ProductoConfig(BaseModel):
    """Modelo de configuración de producto"""
    descripcion: str


@router.post("")
async def guardar_producto(config: ProductoConfig):
    """
    Guarda la configuración del producto en un archivo
    """
    try:
        productos_dir = STORAGE_DIR / "productos"
        productos_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_config.json"
        filepath = productos_dir / filename
        
        data = {
            "config": config.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return {
            "status": "success",
            "message": "Configuración de producto guardada",
            "file": filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar producto: {str(e)}")


@router.get("/latest")
async def obtener_producto_latest():
    """
    Obtiene la configuración más reciente del producto
    """
    try:
        productos_dir = STORAGE_DIR / "productos"
        
        if not productos_dir.exists():
            raise HTTPException(status_code=404, detail="No hay productos configurados")
        
        # Buscar el archivo más reciente
        config_files = list(productos_dir.glob("*_config.json"))
        if not config_files:
            raise HTTPException(status_code=404, detail="No hay productos configurados")
        
        latest_file = max(config_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener producto: {str(e)}")
