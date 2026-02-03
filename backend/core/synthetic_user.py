"""
Agente de usuario sintético
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from core.llm_client import LLMClient
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import STORAGE_DIR, DEFAULT_PROMPTS


class _SafeFormatDict(dict):
    """Dict para format_map que no falla si faltan keys."""

    def __missing__(self, key: str) -> str:
        return "N/A"


class SyntheticUser:
    """Representa un usuario sintético con su perfil y capacidad de respuesta"""
    
    def __init__(self, perfil_basico: Dict[str, Any]):
        """
        Inicializa el usuario sintético con un perfil básico
        
        Args:
            perfil_basico: Diccionario con el arquetipo y sus dimensiones (comportamiento, necesidades, barreras)
        """
        self.perfil_basico = perfil_basico
        self.perfil_detallado: Optional[Dict[str, Any]] = None
        self.nombre: Optional[str] = None
    
    def generate_profile(self, llm_client: LLMClient, prompt_template: Optional[str] = None) -> Dict[str, Any]:
        """
        Genera un perfil detallado del usuario usando el LLM
        
        Args:
            llm_client: Cliente LLM para generar el perfil
            prompt_template: Template del prompt (opcional, usa default si no se proporciona)
        
        Returns:
            Diccionario con el perfil detallado generado
        """
        prompt_template = prompt_template or DEFAULT_PROMPTS["perfil"]
        
        # Formatear el prompt con las características básicas.
        # Incluye compatibilidad con prompts antiguos que referencien {edad}, {genero}, etc.
        format_data = _SafeFormatDict({
            # Nuevo modelo
            "arquetipo": self.perfil_basico.get("arquetipo", "Personalizado"),
            "comportamiento": self.perfil_basico.get("comportamiento", ""),
            "necesidades": self.perfil_basico.get("necesidades", ""),
            "barreras": self.perfil_basico.get("barreras", ""),
            # Campos legacy (por compatibilidad; si no existen, se verán como N/A)
            "edad": self.perfil_basico.get("edad", "N/A"),
            "genero": self.perfil_basico.get("genero", "N/A"),
            "ubicacion": self.perfil_basico.get("ubicacion", "N/A"),
            "experiencia_tecnologica": self.perfil_basico.get("experiencia_tecnologica", "N/A"),
            "intereses": ", ".join(self.perfil_basico.get("intereses", [])) if isinstance(self.perfil_basico.get("intereses"), list) else self.perfil_basico.get("intereses", "N/A"),
        })
        prompt = prompt_template.format_map(format_data)
        
        # Generar perfil usando LLM
        respuesta = llm_client.generate(prompt)
        
        # Nombre base para la investigación (simple y estable)
        # Si el arquetipo es uno de los predefinidos, lo usamos como etiqueta.
        arquetipo = (self.perfil_basico.get("arquetipo") or "").strip()
        self.nombre = arquetipo if arquetipo and arquetipo.lower() != "personalizado" else "Usuario"
        
        # Guardar perfil detallado
        self.perfil_detallado = {
            "perfil_basico": self.perfil_basico,
            "perfil_generado": respuesta,
            "nombre": self.nombre,
            "timestamp": datetime.now().isoformat()
        }
        
        # Guardar en archivo
        self._save_profile()
        
        return self.perfil_detallado
    
    def respond_to_question(self, pregunta: str, contexto_producto: Dict[str, Any],
                          llm_client: LLMClient, prompt_template: Optional[str] = None) -> str:
        """
        Responde una pregunta como este usuario sintético
        
        Args:
            pregunta: La pregunta a responder
            contexto_producto: Información del producto sobre el que se pregunta
            llm_client: Cliente LLM para generar la respuesta
            prompt_template: Template del prompt (opcional)
        
        Returns:
            Respuesta del usuario sintético
        """
        if not self.perfil_detallado:
            raise ValueError("El perfil detallado debe generarse primero. Llama a generate_profile()")
        
        prompt_template = prompt_template or DEFAULT_PROMPTS["investigacion"]
        
        # Formatear el prompt
        prompt = prompt_template.format(
            nombre_usuario=self.nombre,
            perfil_usuario=self.perfil_detallado.get("perfil_generado", ""),
            nombre_producto=contexto_producto.get("nombre_producto", "Producto"),
            descripcion_producto=contexto_producto.get("descripcion", ""),
            pregunta=pregunta
        )
        
        # Generar respuesta usando LLM
        respuesta = llm_client.generate(prompt)
        
        return respuesta
    
    def _save_profile(self):
        """Guarda el perfil generado en un archivo JSON"""
        usuarios_dir = STORAGE_DIR / "usuarios"
        usuarios_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{self.nombre or 'usuario'}.json"
        filepath = usuarios_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.perfil_detallado, f, indent=2, ensure_ascii=False)
        
        return filepath
