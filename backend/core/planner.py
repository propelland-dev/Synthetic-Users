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


def _extract_questions(text: str) -> List[str]:
    if not isinstance(text, str):
        return []

    lines = [ln.strip() for ln in text.splitlines()]
    candidates: List[str] = []

    for ln in lines:
        if not ln:
            continue

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

    # Deduplicar preservando orden
    seen = set()
    out = []
    for q in candidates:
        key = q.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(q)
    return out


def build_plan(descripcion: str, estilo_investigacion: str = "Entrevista") -> Dict[str, Any]:
    """
    Devuelve un dict serializable (compatible con ResearchPlan).
    El estilo_investigacion determina directamente el tipo de investigación.
    """
    desc = descripcion or ""
    steps: List[Dict[str, Any]] = []

    # Determinar tipo basado en el estilo seleccionado
    if estilo_investigacion == "Cuestionario":
        # Para cuestionario, extraer preguntas de la descripción
        questions = _extract_questions(desc)
        steps.append({"type": "cuestionario", "questions": questions})
        research_type = "cuestionario"
    else:
        # Por defecto, entrevista
        steps.append({"type": "entrevista", "n_questions": 6})
        research_type = "entrevista"

    plan = ResearchPlan(version=1, research_type=research_type, steps=steps)
    return plan.model_dump()

