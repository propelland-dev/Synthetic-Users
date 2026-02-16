"""
Utilidades para guardar y cargar configuraciones
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

# Directorio para guardar configuraciones
CONFIG_DIR = Path(__file__).parent / "configs"
CONFIG_DIR.mkdir(exist_ok=True)

# Archivos de configuración
CONFIG_FILES = {
    "usuario": CONFIG_DIR / "config_syntetic_user.json",
    "producto": CONFIG_DIR / "config_producto.json",
    "producto_ficha": CONFIG_DIR / "config_producto_ficha.json",
    "investigacion": CONFIG_DIR / "config_investigacion.json",
    "system": CONFIG_DIR / "config_system.json"
}


def guardar_config(tipo: str, config: Dict[str, Any]) -> bool:
    """
    Guarda una configuración en un archivo JSON
    
    Args:
        tipo: Tipo de configuración ("usuario", "producto", "investigacion", "system")
        config: Diccionario con la configuración
    
    Returns:
        True si se guardó correctamente, False en caso contrario
    """
    try:
        if tipo not in CONFIG_FILES:
            return False
        
        filepath = CONFIG_FILES[tipo]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error al guardar configuración {tipo}: {e}")
        return False


def cargar_config(tipo: str) -> Optional[Dict[str, Any]]:
    """
    Carga una configuración desde un archivo JSON
    
    Args:
        tipo: Tipo de configuración ("usuario", "producto", "investigacion", "system")
    
    Returns:
        Diccionario con la configuración o None si no existe
    """
    try:
        if tipo not in CONFIG_FILES:
            return None
        
        filepath = CONFIG_FILES[tipo]
        if not filepath.exists():
            return None
        
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error al cargar configuración {tipo}: {e}")
        return None


def existe_config(tipo: str) -> bool:
    """
    Verifica si existe una configuración guardada
    
    Args:
        tipo: Tipo de configuración
    
    Returns:
        True si existe, False en caso contrario
    """
    if tipo not in CONFIG_FILES:
        return False
    return CONFIG_FILES[tipo].exists()


def limpiar_respuesta_llm(text: str) -> str:
    """
    Limpia la respuesta de la IA eliminando ÚNICAMENTE etiquetas técnicas 
    como <think> y bloques de código redundantes.
    NO realiza recortes de contenido por anclajes ni filtrado inteligente.
    """
    if not text:
        return ""
    
    import re
    
    # 1. Eliminar bloques completos <think>...</think>
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. Manejar tags huérfanos
    text = re.sub(r'</?think>', '', text, flags=re.IGNORECASE)
            
    # 3. Eliminar envoltorios de bloques de código Markdown globales
    text = text.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if len(lines) >= 2 and lines[0].startswith('```') and lines[-1].strip() == '```':
            text = "\n".join(lines[1:-1])

    return text.strip()
