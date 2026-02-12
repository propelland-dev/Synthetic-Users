"""
Motor de ejecución de investigaciones

Genera un único resultado (texto) para la investigación.
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional

from core.synthetic_user import SyntheticUser
from core.llm_client import LLMClient

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import STORAGE_DIR


class ResearchEngine:
    """Motor que ejecuta investigaciones completas con usuarios sintéticos"""

    def __init__(
        self,
        usuario: SyntheticUser,
        producto: Dict[str, Any],
        investigacion_descripcion: str,
        llm_client: LLMClient,
        prompt_template: Optional[str] = None,
        investigacion_objetivo: Optional[str] = "",
        investigacion_preguntas: Optional[str] = "",
        estilo_investigacion: Optional[str] = None,
    ):
        """
        Inicializa el motor de investigación

        Args:
            usuario: Instancia de SyntheticUser
            producto: Diccionario con información del producto
            investigacion_descripcion: Texto libre de la investigación (objetivo, contexto, etc.)
            llm_client: Cliente LLM para generar respuestas
            prompt_template: Template del prompt para investigación (opcional)
        """
        self.usuario = usuario
        self.producto = producto
        self.investigacion_descripcion = investigacion_descripcion
        self.investigacion_objetivo = investigacion_objetivo or ""
        self.investigacion_preguntas = investigacion_preguntas or ""
        self.estilo_investigacion = estilo_investigacion
        self.llm_client = llm_client
        self.prompt_template = prompt_template
        self.resultados: Optional[Dict[str, Any]] = None

    def execute(self) -> Dict[str, Any]:
        """
        Ejecuta la investigación completa.

        Returns:
            Diccionario con resultado y metadatos
        """
        # Asegurar que el usuario tiene perfil generado
        if not self.usuario.perfil_detallado:
            self.usuario.generate_profile(self.llm_client)

        if not isinstance(self.investigacion_descripcion, str) or not self.investigacion_descripcion.strip():
            raise ValueError("La investigación debe incluir una descripción no vacía")

        prompt_template = self.prompt_template
        if not prompt_template:
            raise ValueError("prompt_template es obligatorio para generar el resultado de investigación")

        prompt = prompt_template.format(
            nombre_usuario=self.usuario.nombre or "Usuario",
            perfil_usuario=self.usuario.perfil_detallado.get("perfil_generado", "") if self.usuario.perfil_detallado else "",
            nombre_producto=self.producto.get("nombre_producto", "Producto"),
            descripcion_producto=self.producto.get("descripcion", ""),
            investigacion_descripcion=self.investigacion_descripcion,
            investigacion_objetivo=self.investigacion_objetivo,
            investigacion_preguntas=self.investigacion_preguntas,
        )
        resultado_texto = self.llm_client.generate(prompt)

        # Compilar resultados
        usuario_basico = dict(self.usuario.perfil_basico or {})
        if getattr(self.usuario, "nombre", None):
            usuario_basico.setdefault("nombre", self.usuario.nombre)

        self.resultados = {
            "timestamp": datetime.now().isoformat(),
            "usuario": usuario_basico,
            "usuario_nombre": getattr(self.usuario, "nombre", None),
            "producto": self.producto,
            "investigacion": {
                "descripcion": self.investigacion_descripcion,
                "objetivo": self.investigacion_objetivo,
                "preguntas": self.investigacion_preguntas,
                "estilo_investigacion": self.estilo_investigacion,
            },
            "resultado": resultado_texto,
        }

        # Guardar resultados
        self._save_results()
        return self.resultados

    def _save_results(self):
        """Guarda los resultados de la investigación en un archivo JSON"""
        resultados_dir = STORAGE_DIR / "resultados"
        resultados_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_investigacion.json"
        filepath = resultados_dir / filename

        if self.resultados is None:
            self.resultados = {}
        self.resultados["resultado_id"] = filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False)

        return filepath

