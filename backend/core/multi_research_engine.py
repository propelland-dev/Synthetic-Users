"""
Motor de investigación por etapas (pipeline) para múltiples respondientes.

Pipeline v1:
1) Planner -> ResearchPlan (ya se genera fuera y se pasa aquí)
2) Para cada respondiente:
   - Generar perfil (prompt_perfil)
   - Ejecutar steps (survey / interview / behavior_sim)
   - Guardar artefacto por respondiente
3) Síntesis agregada (prompt_investigacion) y guardado del resultado final
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.llm_client import LLMClient
from core.synthetic_user import SyntheticUser

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import STORAGE_DIR, DEFAULT_PROMPTS


def _safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    if not isinstance(text, str) or not text.strip():
        return None
    # Intento directo
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    # Intento: extraer bloque JSON
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def _safe_json_parse_any(text: str) -> Optional[Any]:
    if not isinstance(text, str) or not text.strip():
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None
    return None


class MultiResearchEngine:
    def __init__(
        self,
        respondents: List[Dict[str, Any]],
        producto: Dict[str, Any],
        investigacion_descripcion: str,
        llm_client: LLMClient,
        plan: Dict[str, Any],
        prompt_perfil: Optional[str] = None,
        prompt_sintesis: Optional[str] = None,
    ):
        self.respondents = respondents
        self.producto = producto
        self.investigacion_descripcion = investigacion_descripcion
        self.llm_client = llm_client
        self.plan = plan
        self.prompt_perfil = prompt_perfil
        self.prompt_sintesis = prompt_sintesis

        self._run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._run_iso = datetime.now().isoformat()

    def _resultados_dir(self) -> Path:
        d = STORAGE_DIR / "resultados"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _save_json(self, filename: str, data: Dict[str, Any]) -> Path:
        path = self._resultados_dir() / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def _survey_answer_prompt(self, nombre_usuario: str, perfil_usuario: str, pregunta: str) -> str:
        return (
            "Eres {nombre_usuario}, con el siguiente perfil:\n"
            "{perfil_usuario}\n\n"
            "Producto/experiencia:\n"
            "Nombre: {nombre_producto}\n"
            "Descripción: {descripcion_producto}\n\n"
            "Contexto de investigación:\n"
            "{investigacion_descripcion}\n\n"
            "Pregunta (formulario): {pregunta}\n\n"
            "Responde como este usuario. Sé natural y concreto, en español."
        ).format(
            nombre_usuario=nombre_usuario,
            perfil_usuario=perfil_usuario,
            nombre_producto=self.producto.get("nombre_producto", "Producto"),
            descripcion_producto=self.producto.get("descripcion", ""),
            investigacion_descripcion=self.investigacion_descripcion,
            pregunta=pregunta,
        )

    def _survey_batch_prompt(self, nombre_usuario: str, perfil_usuario: str, preguntas: List[str]) -> str:
        preguntas_json = json.dumps([p for p in preguntas if isinstance(p, str) and p.strip()], ensure_ascii=False)
        return (
            "Eres {nombre_usuario}, con el siguiente perfil:\n"
            "{perfil_usuario}\n\n"
            "Producto/experiencia:\n"
            "Nombre: {nombre_producto}\n"
            "Descripción: {descripcion_producto}\n\n"
            "Contexto de investigación:\n"
            "{investigacion_descripcion}\n\n"
            "Este es un cuestionario. Aquí tienes las preguntas en JSON:\n"
            "{preguntas}\n\n"
            "Responde en texto (NO JSON) en el mismo orden que las preguntas, con el formato:\n"
            "Q1: ...\nA1: ...\n\nQ2: ...\nA2: ...\n\n..."
        ).format(
            nombre_usuario=nombre_usuario,
            perfil_usuario=perfil_usuario,
            nombre_producto=self.producto.get("nombre_producto", "Producto"),
            descripcion_producto=self.producto.get("descripcion", ""),
            investigacion_descripcion=self.investigacion_descripcion,
            preguntas=preguntas_json,
        )

    def _interview_single_prompt(
        self,
        nombre_usuario: str,
        perfil_usuario: str,
        n_questions: int = 6,
        seed: Optional[int] = None,
    ) -> str:
        """
        Entrevista en un solo turno (una sola llamada) por respondiente.
        No hay transcript/turnos para evitar crecimiento de contexto y reducir rate limits.
        """
        n = max(1, min(int(n_questions or 6), 12))
        seed_txt = f"{int(seed)}" if isinstance(seed, int) else ""
        return (
            "Eres {nombre_usuario}, con el siguiente perfil:\n"
            "{perfil_usuario}\n\n"
            "Producto/experiencia:\n"
            "Nombre: {nombre_producto}\n"
            "Descripción: {descripcion_producto}\n\n"
            "Contexto de investigación:\n"
            "{investigacion_descripcion}\n\n"
            "Simula una entrevista completa en un solo mensaje.\n"
            "Genera {n} preguntas del entrevistador y respóndelas como este usuario.\n"
            "Para que distintos respondientes no respondan igual, usa este seed (si está): {seed}\n\n"
            "Devuelve SOLO texto (NO JSON) con el formato:\n"
            "Q1: ...\nA1: ...\n\nQ2: ...\nA2: ...\n\n..."
        ).format(
            nombre_usuario=nombre_usuario,
            perfil_usuario=perfil_usuario,
            nombre_producto=self.producto.get("nombre_producto", "Producto"),
            descripcion_producto=self.producto.get("descripcion", ""),
            investigacion_descripcion=self.investigacion_descripcion,
            n=n,
            seed=seed_txt or "N/A",
        )

    def _behavior_sim_prompt(self, nombre_usuario: str, perfil_usuario: str, scenario: str) -> str:
        sc = scenario or "Explora el producto e intenta completar tu objetivo principal según la investigación."
        return (
            "Eres {nombre_usuario}, con el siguiente perfil:\n"
            "{perfil_usuario}\n\n"
            "Producto/experiencia:\n"
            "Nombre: {nombre_producto}\n"
            "Descripción: {descripcion_producto}\n\n"
            "Contexto de investigación:\n"
            "{investigacion_descripcion}\n\n"
            "Escenario:\n"
            "{scenario}\n\n"
            "Simula tu comportamiento paso a paso e identifica fricciones.\n"
            "Devuelve SOLO JSON con claves: steps (list), frictions (list), needs (list), suggestions (list)."
        ).format(
            nombre_usuario=nombre_usuario,
            perfil_usuario=perfil_usuario,
            nombre_producto=self.producto.get("nombre_producto", "Producto"),
            descripcion_producto=self.producto.get("descripcion", ""),
            investigacion_descripcion=self.investigacion_descripcion,
            scenario=sc,
        )

    def execute(self) -> Dict[str, Any]:
        # Guardar plan
        plan_id = f"{self._run_ts}_plan.json"
        self._save_json(plan_id, {"timestamp": self._run_iso, "plan": self.plan})

        respondents_meta: List[Dict[str, Any]] = []
        respondents_artifacts: List[Dict[str, Any]] = []

        steps = self.plan.get("steps") if isinstance(self.plan, dict) else []
        if not isinstance(steps, list):
            steps = []

        for idx, perfil_basico in enumerate(self.respondents):
            # 1) Perfil
            usuario = SyntheticUser(perfil_basico)
            perfil_det = usuario.generate_profile(self.llm_client, self.prompt_perfil)
            perfil_text = (perfil_det or {}).get("perfil_generado", "")
            nombre = (perfil_det or {}).get("nombre") or usuario.nombre or f"Respondent_{idx+1}"

            artifact_steps: List[Dict[str, Any]] = []

            # 2) Ejecutar steps
            for step in steps:
                if not isinstance(step, dict):
                    continue
                stype = step.get("type")

                if stype == "survey":
                    questions = step.get("questions", [])
                    if not isinstance(questions, list):
                        questions = []
                    questions = [q for q in questions if isinstance(q, str) and q.strip()]
                    # 1 llamada por cuestionario y respondiente (sin parsear JSON)
                    out = ""
                    if questions:
                        batch_prompt = self._survey_batch_prompt(nombre, perfil_text, questions)
                        out = self.llm_client.generate(batch_prompt)
                    artifact_steps.append({"type": "survey", "questions": questions, "text": out})

                elif stype == "interview":
                    n_questions = step.get("n_questions", 6)
                    try:
                        n_i = max(1, int(n_questions))
                    except Exception:
                        n_i = 6
                    prompt = self._interview_single_prompt(nombre, perfil_text, n_questions=n_i, seed=idx + 1)
                    out = self.llm_client.generate(prompt)
                    artifact_steps.append({"type": "interview", "n_questions": n_i, "text": out})

                elif stype == "behavior_sim":
                    scenarios = step.get("scenarios", [])
                    if not isinstance(scenarios, list) or not scenarios:
                        scenarios = [""]
                    sims = []
                    for sc in scenarios:
                        prompt = self._behavior_sim_prompt(nombre, perfil_text, sc if isinstance(sc, str) else "")
                        out = self.llm_client.generate(prompt)
                        parsed = _safe_json_parse(out)
                        sims.append({"scenario": sc, "output": parsed or {"raw": out}})
                    artifact_steps.append({"type": "behavior_sim", "sims": sims})

            respondent_id = f"{self._run_ts}_respondent_{idx+1:02d}.json"
            artifact = {
                "timestamp": self._run_iso,
                "respondent_id": respondent_id,
                "perfil_basico": perfil_basico,
                "usuario_nombre": nombre,
                "perfil_generado": perfil_text,
                "steps": artifact_steps,
            }
            self._save_json(respondent_id, artifact)

            respondents_meta.append({"respondent_id": respondent_id, "arquetipo": perfil_basico.get("arquetipo", "Personalizado")})
            respondents_artifacts.append(artifact)

        # 3) Síntesis agregada
        prompt_template = self.prompt_sintesis or DEFAULT_PROMPTS["investigacion"]

        # Construir un contexto compacto para síntesis
        if len(respondents_artifacts) == 1:
            perfil_usuario = respondents_artifacts[0].get("perfil_generado", "")
            nombre_usuario = respondents_artifacts[0].get("usuario_nombre", "Usuario")
        else:
            # resumen población
            counts: Dict[str, int] = {}
            for r in respondents_meta:
                a = r.get("arquetipo") or "Personalizado"
                counts[a] = counts.get(a, 0) + 1
            mix = ", ".join(f"{k} x{v}" for k, v in counts.items())
            nombre_usuario = "Población"
            perfil_usuario = f"Respondientes: {len(respondents_meta)}. Mix: {mix}."

        base_prompt = prompt_template.format(
            nombre_usuario=nombre_usuario,
            perfil_usuario=perfil_usuario,
            nombre_producto=self.producto.get("nombre_producto", "Producto"),
            descripcion_producto=self.producto.get("descripcion", ""),
            investigacion_descripcion=self.investigacion_descripcion,
        )

        # Adjuntar artefactos (en JSON) para que la síntesis tenga evidencia
        artifacts_json = json.dumps(
            [{"respondent": r["respondent_id"], "arquetipo": r.get("arquetipo"), "steps": a.get("steps")} for r, a in zip(respondents_meta, respondents_artifacts)],
            ensure_ascii=False,
        )
        synthesis_prompt = (
            base_prompt
            + "\n\n---\n"
            + "A continuación tienes los datos crudos (JSON) de las respuestas por respondiente.\n"
            + "Usa estos datos para generar el informe. Cita evidencias (frases/paráfrasis) cuando sea útil.\n\n"
            + artifacts_json
        )

        resultado_texto = self.llm_client.generate(synthesis_prompt)

        # 4) Resultado final (compatibilidad UI)
        final_filename = f"{self._run_ts}_investigacion.json"
        usuario_basico: Dict[str, Any]
        if len(respondents_artifacts) == 1:
            usuario_basico = dict(respondents_artifacts[0].get("perfil_basico") or {})
        else:
            usuario_basico = {"mode": "population", "arquetipo": "Población"}

        final = {
            "timestamp": self._run_iso,
            "resultado_id": final_filename,
            "usuario": usuario_basico,
            "usuario_nombre": nombre_usuario,
            "producto": self.producto,
            "investigacion": {"descripcion": self.investigacion_descripcion},
            "resultado": resultado_texto,
            "plan": self.plan,
            "respondents": respondents_meta,
            "artifacts": {
                "plan_id": plan_id,
            },
        }
        self._save_json(final_filename, final)
        return final

    def execute_stream(self):
        """
        Ejecuta la investigación emitiendo eventos de progreso.

        Yields:
          dict events, por ejemplo:
            {"event": "respondent_start", "i": 1, "n": 10, "message": "..."}
            {"event": "step_done", "i": 1, "n": 10, "step_type": "survey", "message": "..."}
            {"event": "done", "result": {...}}
        """
        # Guardar plan
        plan_id = f"{self._run_ts}_plan.json"
        self._save_json(plan_id, {"timestamp": self._run_iso, "plan": self.plan})
        yield {"event": "plan_saved", "plan_id": plan_id, "message": "Plan de investigación preparado."}

        respondents_meta: List[Dict[str, Any]] = []
        respondents_artifacts: List[Dict[str, Any]] = []

        steps = self.plan.get("steps") if isinstance(self.plan, dict) else []
        if not isinstance(steps, list):
            steps = []

        total = len(self.respondents) if isinstance(self.respondents, list) else 0
        if total <= 0:
            total = 1

        for idx, perfil_basico in enumerate(self.respondents):
            arquetipo = (perfil_basico or {}).get("arquetipo", "Personalizado") if isinstance(perfil_basico, dict) else "Personalizado"
            yield {
                "event": "respondent_start",
                "i": idx + 1,
                "n": total,
                "arquetipo": arquetipo,
                "message": f"Respondiente {idx+1}/{total} ({arquetipo})",
            }

            # 1) Perfil
            yield {"event": "profile_start", "i": idx + 1, "n": total, "message": f"Generando perfil del respondiente {idx+1}/{total}..."}
            usuario = SyntheticUser(perfil_basico if isinstance(perfil_basico, dict) else {})
            perfil_det = usuario.generate_profile(self.llm_client, self.prompt_perfil)
            perfil_text = (perfil_det or {}).get("perfil_generado", "")
            nombre = (perfil_det or {}).get("nombre") or usuario.nombre or f"Respondent_{idx+1}"
            yield {"event": "profile_done", "i": idx + 1, "n": total, "message": f"Perfil generado ({nombre})."}

            artifact_steps: List[Dict[str, Any]] = []

            # 2) Ejecutar steps
            for step in steps:
                if not isinstance(step, dict):
                    continue
                stype = step.get("type")
                if not stype:
                    continue

                yield {
                    "event": "step_start",
                    "i": idx + 1,
                    "n": total,
                    "step_type": stype,
                    "message": f"Ejecutando '{stype}' para {nombre}...",
                }

                if stype == "survey":
                    questions = step.get("questions", [])
                    if not isinstance(questions, list):
                        questions = []
                    questions = [q for q in questions if isinstance(q, str) and q.strip()]
                    out = ""
                    if questions:
                        batch_prompt = self._survey_batch_prompt(nombre, perfil_text, questions)
                        out = self.llm_client.generate(batch_prompt)
                    artifact_steps.append({"type": "survey", "questions": questions, "text": out})

                elif stype == "interview":
                    n_questions = step.get("n_questions", 6)
                    try:
                        n_i = max(1, int(n_questions))
                    except Exception:
                        n_i = 6
                    prompt = self._interview_single_prompt(nombre, perfil_text, n_questions=n_i, seed=idx + 1)
                    out = self.llm_client.generate(prompt)
                    artifact_steps.append({"type": "interview", "n_questions": n_i, "text": out})

                elif stype == "behavior_sim":
                    scenarios = step.get("scenarios", [])
                    if not isinstance(scenarios, list) or not scenarios:
                        scenarios = [""]
                    sims = []
                    for sc in scenarios:
                        prompt = self._behavior_sim_prompt(nombre, perfil_text, sc if isinstance(sc, str) else "")
                        out = self.llm_client.generate(prompt)
                        parsed = _safe_json_parse(out)
                        sims.append({"scenario": sc, "output": parsed or {"raw": out}})
                    artifact_steps.append({"type": "behavior_sim", "sims": sims})

                yield {
                    "event": "step_done",
                    "i": idx + 1,
                    "n": total,
                    "step_type": stype,
                    "message": f"'{stype}' completado para {nombre}.",
                }

            respondent_id = f"{self._run_ts}_respondent_{idx+1:02d}.json"
            artifact = {
                "timestamp": self._run_iso,
                "respondent_id": respondent_id,
                "perfil_basico": perfil_basico,
                "usuario_nombre": nombre,
                "perfil_generado": perfil_text,
                "steps": artifact_steps,
            }
            self._save_json(respondent_id, artifact)

            respondents_meta.append({"respondent_id": respondent_id, "arquetipo": arquetipo})
            respondents_artifacts.append(artifact)

            yield {
                "event": "respondent_done",
                "i": idx + 1,
                "n": total,
                "respondent_id": respondent_id,
                "message": f"Respondiente {idx+1}/{total} guardado.",
            }

        # 3) Síntesis agregada
        yield {"event": "synthesis_start", "message": "Generando síntesis agregada..."}
        prompt_template = self.prompt_sintesis or DEFAULT_PROMPTS["investigacion"]

        if len(respondents_artifacts) == 1:
            perfil_usuario = respondents_artifacts[0].get("perfil_generado", "")
            nombre_usuario = respondents_artifacts[0].get("usuario_nombre", "Usuario")
        else:
            counts: Dict[str, int] = {}
            for r in respondents_meta:
                a = r.get("arquetipo") or "Personalizado"
                counts[a] = counts.get(a, 0) + 1
            mix = ", ".join(f"{k} x{v}" for k, v in counts.items())
            nombre_usuario = "Población"
            perfil_usuario = f"Respondientes: {len(respondents_meta)}. Mix: {mix}."

        base_prompt = prompt_template.format(
            nombre_usuario=nombre_usuario,
            perfil_usuario=perfil_usuario,
            nombre_producto=self.producto.get("nombre_producto", "Producto"),
            descripcion_producto=self.producto.get("descripcion", ""),
            investigacion_descripcion=self.investigacion_descripcion,
        )

        artifacts_json = json.dumps(
            [{"respondent": r["respondent_id"], "arquetipo": r.get("arquetipo"), "steps": a.get("steps")} for r, a in zip(respondents_meta, respondents_artifacts)],
            ensure_ascii=False,
        )
        synthesis_prompt = (
            base_prompt
            + "\n\n---\n"
            + "A continuación tienes los datos crudos (JSON) de las respuestas por respondiente.\n"
            + "Usa estos datos para generar el informe. Cita evidencias (frases/paráfrasis) cuando sea útil.\n\n"
            + artifacts_json
        )

        resultado_texto = self.llm_client.generate(synthesis_prompt)
        yield {"event": "synthesis_done", "message": "Síntesis completada."}

        # 4) Resultado final (compatibilidad UI)
        final_filename = f"{self._run_ts}_investigacion.json"
        usuario_basico: Dict[str, Any]
        if len(respondents_artifacts) == 1:
            usuario_basico = dict(respondents_artifacts[0].get("perfil_basico") or {})
        else:
            usuario_basico = {"mode": "population", "arquetipo": "Población"}

        final = {
            "timestamp": self._run_iso,
            "resultado_id": final_filename,
            "usuario": usuario_basico,
            "usuario_nombre": nombre_usuario,
            "producto": self.producto,
            "investigacion": {"descripcion": self.investigacion_descripcion},
            "resultado": resultado_texto,
            "plan": self.plan,
            "respondents": respondents_meta,
            "artifacts": {
                "plan_id": plan_id,
            },
        }
        self._save_json(final_filename, final)
        yield {"event": "done", "result": final, "message": "Investigación completada."}

