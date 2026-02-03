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


def build_plan(descripcion: str) -> Dict[str, Any]:
    """
    Devuelve un dict serializable (compatible con ResearchPlan).
    """
    desc = descripcion or ""
    questions = _extract_questions(desc)

    steps: List[Dict[str, Any]] = []

    # 1) Survey si hay preguntas explícitas
    if questions:
        steps.append({"type": "survey", "questions": questions})

    # 2) Entrevista si el texto sugiere entrevista o si no hay preguntas
    lower = desc.lower()
    wants_interview = any(w in lower for w in ["entrevista", "conversación", "conversacion", "profundizar", "follow up", "follow-up"])
    if wants_interview or not questions:
        # Entrevista en 1 turno (1 llamada) por respondiente.
        # Si hay preguntas explícitas, ya van en survey; aquí dejamos preguntas vacías
        # para que el motor haga una entrevista libre guiada por la descripción.
        steps.append({"type": "interview", "n_questions": 6, "questions": []})

    # 3) Simulación de comportamiento si se menciona explícitamente
    wants_sim = any(w in lower for w in ["simula", "simulación", "simulacion", "escenario", "tarea", "journey", "flujo"])
    if wants_sim:
        steps.append({"type": "behavior_sim", "scenarios": []})

    research_type = "mixed"
    only_types = {s.get("type") for s in steps}
    if only_types == {"survey"}:
        research_type = "survey"
    elif only_types == {"interview"}:
        research_type = "interview"
    elif only_types == {"behavior_sim"}:
        research_type = "behavior_sim"

    plan = ResearchPlan(version=1, research_type=research_type, steps=steps)
    return plan.model_dump()

