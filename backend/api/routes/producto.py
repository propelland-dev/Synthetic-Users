"""
Endpoints para gestión de productos
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional, List
import json
from datetime import datetime
from pathlib import Path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import STORAGE_DIR
from core.llm_client import LLMClient

router = APIRouter(prefix="/api/producto", tags=["producto"])


class ProductoConfig(BaseModel):
    """Modelo de configuración de producto"""
    # Campo canónico usado por la investigación
    descripcion: str

    # Parámetros guiados (opcionales)
    producto_tipo: Optional[str] = None  # "nuevo" | "existente"
    nombre_producto: Optional[str] = None
    descripcion_input: Optional[str] = None
    problema_a_resolver: Optional[str] = None
    propuesta_valor: Optional[str] = None
    funcionalidades_clave: Optional[str] = None
    canal_soporte: Optional[str] = None
    productos_sustitutivos: Optional[str] = None
    fuentes_a_ingestar: Optional[str] = None
    observaciones: Optional[str] = None
    riesgos: Optional[str] = None
    dependencias: Optional[str] = None

    # Existente: adjuntos (por ahora: metadatos)
    url: Optional[str] = None
    documentos: Optional[List[Dict[str, Any]]] = None
    fotos: Optional[List[Dict[str, Any]]] = None

    # Artefacto derivado
    ficha_producto: Optional[str] = None


class SystemConfigFichaProducto(BaseModel):
    llm_provider: str
    temperatura: Optional[float] = None
    max_tokens: Optional[int] = None
    prompt_ficha_producto: Optional[str] = None
    # AnythingLLM (opcional)
    anythingllm_base_url: Optional[str] = None
    anythingllm_api_key: Optional[str] = None
    anythingllm_workspace_slug: Optional[str] = None
    anythingllm_mode: Optional[str] = None
    # Hugging Face (opcional)
    huggingface_api_key: Optional[str] = None
    huggingface_model: Optional[str] = None


class GenerarFichaProductoRequest(BaseModel):
    producto: ProductoConfig
    system_config: SystemConfigFichaProducto


def _normalize_llm_provider(value: Optional[str]) -> str:
    if not value:
        return "ollama"
    v = str(value).strip().lower()
    if v in {"anythingllm", "anything llm", "anything-llm", "anything_llm"}:
        return "anythingllm"
    if v in {"huggingface", "hugging face", "hf"}:
        return "huggingface"
    if v in {"ollama", "anythingllm", "huggingface"}:
        return v
    return "ollama"


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "N/A"


def _product_format_data(producto: Dict[str, Any]) -> _SafeFormatDict:
    def _s(k: str) -> str:
        v = producto.get(k)
        return str(v).strip() if isinstance(v, (str, int, float)) and str(v).strip() else "N/A"

    # Adjuntos: metadatos
    def _list_names(k: str) -> str:
        arr = producto.get(k)
        if not isinstance(arr, list) or not arr:
            return "N/A"
        names = []
        for it in arr:
            if isinstance(it, dict):
                n = it.get("name") or it.get("filename")
                if isinstance(n, str) and n.strip():
                    names.append(n.strip())
        return ", ".join(names) if names else "N/A"

    return _SafeFormatDict(
        {
            "producto_tipo": _s("producto_tipo"),
            "nombre_producto": _s("nombre_producto"),
            "descripcion_input": _s("descripcion_input"),
            "problema_a_resolver": _s("problema_a_resolver"),
            "propuesta_valor": _s("propuesta_valor"),
            "funcionalidades_clave": _s("funcionalidades_clave"),
            "canal_soporte": _s("canal_soporte"),
            "productos_sustitutivos": _s("productos_sustitutivos"),
            "fuentes_a_ingestar": _s("fuentes_a_ingestar"),
            "observaciones": _s("observaciones"),
            "riesgos": _s("riesgos"),
            "dependencias": _s("dependencias"),
            "url": _s("url"),
            "documentos": _list_names("documentos"),
            "fotos": _list_names("fotos"),
        }
    )


DEFAULT_PROMPT_FICHA_PRODUCTO = """Eres un asistente de research. Con los datos estructurados de un producto, genera una “Ficha de producto” en español (Markdown), clara y accionable.

DATOS
- Tipo: {producto_tipo}  (nuevo/existente)
- Nombre: {nombre_producto}
- Descripción (input libre): {descripcion_input}
- Problema a resolver: {problema_a_resolver}
- Propuesta de valor: {propuesta_valor}
- Funcionalidades clave: {funcionalidades_clave}
- Canal de soporte: {canal_soporte}
- Productos sustitutivos: {productos_sustitutivos}
- Fuentes a ingestar: {fuentes_a_ingestar}
- Observaciones: {observaciones}
- Riesgos: {riesgos}
- Dependencias: {dependencias}

SI ES EXISTENTE (opcional)
- URL: {url}
- Documentos: {documentos}
- Fotos: {fotos}

REQUISITOS DE SALIDA
- Devuelve SOLO Markdown.
- Incluye secciones: Resumen, Problema, Propuesta de valor, Alcance/No alcance, Funcionalidades clave, Soporte/Operación, Sustitutivos/Alternativas, Riesgos, Dependencias, Fuentes a ingestar, Observaciones, Preguntas abiertas.
- Si falta información, no inventes: marca “(pendiente)” y añade preguntas concretas a “Preguntas abiertas”.
"""


@router.post("")
async def guardar_producto(config: ProductoConfig):
    """
    Guarda la configuración del producto en un archivo
    """
    try:
        productos_dir = STORAGE_DIR / "productos"
        productos_dir.mkdir(parents=True, exist_ok=True)
        
        filename = "config.json"
        filepath = productos_dir / filename
        
        data = {
            "config": config.model_dump(),
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


@router.post("/generar_ficha")
async def generar_ficha_producto(request: GenerarFichaProductoRequest):
    """
    Genera una ficha de producto (Markdown) a partir de parámetros + descripción libre.
    """
    try:
        producto = request.producto.model_dump()
        sys_cfg = request.system_config.model_dump()

        prompt_template = sys_cfg.get("prompt_ficha_producto") or DEFAULT_PROMPT_FICHA_PRODUCTO
        format_data = _product_format_data(producto)
        prompt = str(prompt_template).format_map(format_data)

        provider = _normalize_llm_provider(sys_cfg.get("llm_provider"))
        llm_config: Dict[str, Any] = {
            "provider": provider,
            "temperature": sys_cfg.get("temperatura", 0.7),
            "max_tokens": sys_cfg.get("max_tokens", 1000),
        }
        if provider == "anythingllm":
            mode = str(sys_cfg.get("anythingllm_mode") or "chat").strip().lower()
            if mode != "chat":
                mode = "chat"
            llm_config.update(
                {
                    "base_url": sys_cfg.get("anythingllm_base_url"),
                    "api_key": sys_cfg.get("anythingllm_api_key"),
                    "workspace_slug": sys_cfg.get("anythingllm_workspace_slug"),
                    "mode": mode,
                }
            )
        elif provider == "huggingface":
            llm_config.update(
                {
                    "api_key": sys_cfg.get("huggingface_api_key"),
                    "model": sys_cfg.get("huggingface_model"),
                }
            )

        llm_client = LLMClient(provider="llama", config=llm_config)
        ficha = llm_client.generate(prompt)
        return {"status": "success", "ficha_producto": ficha}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar ficha de producto: {str(e)}")


@router.get("/latest")
async def obtener_producto_latest():
    """
    Obtiene la configuración más reciente del producto
    """
    try:
        productos_dir = STORAGE_DIR / "productos"
        
        if not productos_dir.exists():
            raise HTTPException(status_code=404, detail="No hay productos configurados")
        
        # Primero intentar cargar config.json
        config_json = productos_dir / "config.json"
        if config_json.exists():
            with open(config_json, "r", encoding="utf-8") as f:
                return json.load(f)

        # Fallback: Buscar el archivo más reciente
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
