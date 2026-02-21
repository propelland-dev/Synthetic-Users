"""
Planner heurístico (v1) para convertir una descripción de investigación libre en un ResearchPlan.

Objetivo:
- No limitar la investigación a un formulario
- Detectar preguntas si existen (survey)
- Si no hay preguntas explícitas, proponer un flujo tipo entrevista y/o simulación de comportamiento
"""

from __future__ import annotations

import re
from typing import Dict, Any, List

from core.models import ResearchPlan


_BULLET_RE = re.compile(r"^\s*([-*•]|\d+[.)])\s+(?P<text>.+?)\s*$")


def _extract_questions(text: str, is_preguntas_field: bool = False) -> List[str]:
    """
    Extrae preguntas de un texto. 
    Si is_preguntas_field es True, se asume que cada línea no vacía es una pregunta 
    si no se detectan patrones específicos.
    """
    if not isinstance(text, str):
        return []

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    candidates: List[str] = []

    for ln in lines:
        # Si contiene ? lo tomamos como pregunta
        if "?" in ln:
            candidates.append(ln.strip("-*• ").strip())
            continue

        # Si es bullet/num y parece pregunta (prefijos típicos)
        m = _BULLET_RE.match(ln)
        if m:
            t = (m.group("text") or "").strip()
            # heurística: si empieza con interrogativo o verbo en 2a persona
            if re.match(r"^(qué|que|cómo|como|cuál|cual|por qué|por que|dónde|donde|cuándo|cuando)\b", t.lower()):
                candidates.append(t)
            elif is_preguntas_field:
                # En el campo específico, si es bullet, lo tomamos como pregunta
                candidates.append(t)
            continue
        
        # Si no hay patrones pero estamos en el campo específico de preguntas, 
        # tomamos la línea como pregunta
        if is_preguntas_field:
            candidates.append(ln.strip("-*• ").strip())

    # Deduplicar preservando orden
    seen = set()
    out = []
    for q in candidates:
        key = q.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(q)
    return out


def build_plan(descripcion: str, estilo_investigacion: str = "Entrevista", preguntas: str = "") -> Dict[str, Any]:
    """
    Devuelve un dict serializable (compatible con ResearchPlan).
    El estilo_investigacion determina directamente el tipo de investigación.
    Se priorizan las preguntas explícitas del campo 'preguntas'.
    """
    desc = descripcion or ""
    pregs = preguntas or ""
    steps: List[Dict[str, Any]] = []

    # Extraer preguntas: priorizar el campo específico (con modo lenient)
    questions = _extract_questions(pregs, is_preguntas_field=True)
    
    # Si no hay preguntas en el campo específico, intentar extraer de la descripción
    if not questions:
        questions = _extract_questions(desc, is_preguntas_field=False)

    # Determinar tipo basado en el estilo seleccionado
    if estilo_investigacion == "Cuestionario":
        steps.append({"type": "cuestionario", "questions": questions})
        research_type = "cuestionario"
    else:
        # Por defecto, entrevista. Pasamos las preguntas detectadas si existen.
        n = len(questions) if questions else 6
        steps.append({"type": "entrevista", "n_questions": n, "questions": questions})
        research_type = "entrevista"

    plan = ResearchPlan(version=1, research_type=research_type, steps=steps)
    return plan.model_dump()

