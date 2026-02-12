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




class MultiResearchEngine:
    def __init__(
        self,
        respondents: List[Dict[str, Any]],
        producto: Dict[str, Any],
        investigacion_descripcion: str,
        llm_client: LLMClient,
        plan: Dict[str, Any],
        prompt_perfil: Optional[str] = None,
        prompt_cuestionario: Optional[str] = None,
        prompt_entrevista: Optional[str] = None,
        prompt_sintesis: Optional[str] = None,
        investigacion_objetivo: Optional[str] = "",
        investigacion_preguntas: Optional[str] = "",
        estilo_investigacion: Optional[str] = None,
    ):
        self.respondents = respondents
        self.producto = producto
        self.investigacion_descripcion = investigacion_descripcion
        self.investigacion_objetivo = investigacion_objetivo or ""
        self.investigacion_preguntas = investigacion_preguntas or ""
        self.estilo_investigacion = estilo_investigacion
        # Usamos `llm_client` como "prototipo" de configuración.
        # Para evitar compartir estado entre respondientes (p.ej. throttling/estado interno),
        # creamos instancias nuevas para cada respondiente y otra para la síntesis final.
        self.llm_client = llm_client
        self.plan = plan
        self.prompt_perfil = prompt_perfil
        self.prompt_cuestionario = prompt_cuestionario
        self.prompt_entrevista = prompt_entrevista
        self.prompt_sintesis = prompt_sintesis

        self._run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._run_iso = datetime.now().isoformat()

    def _fresh_llm_client(self) -> LLMClient:
        """
        Crea un LLMClient nuevo clonando configuración del prototipo.
        """
        proto = self.llm_client
        provider = getattr(proto, "provider", "llama")
        config = dict(getattr(proto, "config", {}) or {})
        return LLMClient(provider=provider, config=config)

    def _resultados_dir(self) -> Path:
        d = STORAGE_DIR / "resultados" / self._run_ts
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _save_json(self, filename: str, data: Dict[str, Any], subdir: Optional[str] = None) -> Path:
        base_dir = self._resultados_dir()
        if subdir:
            target_dir = base_dir / subdir
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            target_dir = base_dir
            
        path = target_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def _cuestionario_prompt(self, nombre_usuario: str, perfil_usuario: str, preguntas: List[str]) -> str:
        preguntas_texto = "\n".join([f"Q{i+1}: {p}" for i, p in enumerate(preguntas) if isinstance(p, str) and p.strip()])
        
        prompt_template = self.prompt_cuestionario or DEFAULT_PROMPTS["cuestionario"]
        return prompt_template.format(
            nombre_usuario=nombre_usuario,
            perfil_usuario=perfil_usuario,
            nombre_producto=self.producto.get("nombre_producto", "Producto"),
            descripcion_producto=self.producto.get("descripcion", ""),
            investigacion_descripcion=self.investigacion_descripcion,
            investigacion_objetivo=self.investigacion_objetivo,
            investigacion_preguntas=self.investigacion_preguntas,
            preguntas=preguntas_texto,
        )

    def _entrevista_prompt(
        self,
        nombre_usuario: str,
        perfil_usuario: str,
        n_questions: int = 6,
        seed: Optional[int] = None,
    ) -> str:
        n = max(1, min(int(n_questions or 6), 12))
        seed_txt = f"{int(seed)}" if isinstance(seed, int) else "N/A"
        
        prompt_template = self.prompt_entrevista or DEFAULT_PROMPTS["entrevista"]
        return prompt_template.format(
            nombre_usuario=nombre_usuario,
            perfil_usuario=perfil_usuario,
            nombre_producto=self.producto.get("nombre_producto", "Producto"),
            descripcion_producto=self.producto.get("descripcion", ""),
            investigacion_descripcion=self.investigacion_descripcion,
            investigacion_objetivo=self.investigacion_objetivo,
            investigacion_preguntas=self.investigacion_preguntas,
            n_questions=n,
            seed=seed_txt,
        )


    def execute(self) -> Dict[str, Any]:
        # Guardar configuraciones utilizadas
        self._save_json("producto.json", self.producto, subdir="configs")
        self._save_json("investigacion.json", {
            "descripcion": self.investigacion_descripcion,
            "objetivo": self.investigacion_objetivo,
            "preguntas": self.investigacion_preguntas,
        }, subdir="configs")
        self._save_json("respondientes_config.json", {"respondents": self.respondents}, subdir="configs")

        # Guardar plan
        plan_id = "plan.json"
        self._save_json(plan_id, {"timestamp": self._run_iso, "plan": self.plan})

        respondents_meta: List[Dict[str, Any]] = []
        respondents_artifacts: List[Dict[str, Any]] = []

        steps = self.plan.get("steps") if isinstance(self.plan, dict) else []
        if not isinstance(steps, list):
            steps = []

        for idx, perfil_basico in enumerate(self.respondents):
            llm_client_r = self._fresh_llm_client()
            usuario = SyntheticUser(perfil_basico)
            perfil_det = usuario.generate_profile(llm_client_r, self.prompt_perfil)
            perfil_text = (perfil_det or {}).get("perfil_generado", "")
            nombre = (perfil_det or {}).get("nombre") or usuario.nombre or f"Respondent_{idx+1}"

            artifact_steps: List[Dict[str, Any]] = []

            for step in steps:
                if not isinstance(step, dict):
                    continue
                stype = step.get("type")

                if stype == "cuestionario":
                    questions = step.get("questions", [])
                    if not isinstance(questions, list):
                        questions = []
                    questions = [q for q in questions if isinstance(q, str) and q.strip()]
                    out = ""
                    if questions:
                        prompt = self._cuestionario_prompt(nombre, perfil_text, questions)
                        out = llm_client_r.generate(prompt)
                    artifact_steps.append({"type": "cuestionario", "questions": questions, "respuestas": out})

                elif stype == "entrevista":
                    n_questions = step.get("n_questions", 6)
                    try:
                        n_i = max(1, int(n_questions))
                    except Exception:
                        n_i = 6
                    prompt = self._entrevista_prompt(nombre, perfil_text, n_questions=n_i, seed=idx + 1)
                    out = llm_client_r.generate(prompt)
                    artifact_steps.append({"type": "entrevista", "n_questions": n_i, "transcripcion": out})

            respondent_filename = f"respondent_{idx+1:02d}.json"
            artifact = {
                "timestamp": self._run_iso,
                "respondent_id": respondent_filename,
                "perfil_basico": perfil_basico,
                "usuario_nombre": nombre,
                "perfil_generado": perfil_text,
                "steps": artifact_steps,
            }
            self._save_json(respondent_filename, artifact, subdir="respondents")

            respondents_meta.append({"respondent_id": respondent_filename, "arquetipo": perfil_basico.get("arquetipo", "Personalizado")})
            respondents_artifacts.append(artifact)

        # 3) Síntesis agregada
        prompt_template = self.prompt_sintesis or DEFAULT_PROMPTS["sintesis"]

        if len(respondents_artifacts) == 1:
            nombre_usuario = "1 respondiente"
        else:
            counts: Dict[str, int] = {}
            for r in respondents_meta:
                a = r.get("arquetipo") or "Personalizado"
                counts[a] = counts.get(a, 0) + 1
            mix = ", ".join(f"{k} x{v}" for k, v in counts.items())
            nombre_usuario = f"{len(respondents_meta)} respondientes ({mix})"

        base_prompt = prompt_template.format(
            nombre_usuario=nombre_usuario,
            nombre_producto=self.producto.get("nombre_producto", "Producto"),
            descripcion_producto=self.producto.get("descripcion", ""),
            investigacion_descripcion=self.investigacion_descripcion,
            investigacion_objetivo=self.investigacion_objetivo,
            investigacion_preguntas=self.investigacion_preguntas,
        )

        # Crear un resumen de datos más legible (texto plano en lugar de JSON)
        datos_texto = []
        for r, a in zip(respondents_meta, respondents_artifacts):
            arquetipo = r.get("arquetipo", "Personalizado")
            nombre = a.get("usuario_nombre", "Usuario")
            datos_texto.append(f"\n=== RESPONDIENTE: {nombre} ({arquetipo}) ===")
            
            for step in a.get("steps", []):
                if step.get("type") == "cuestionario":
                    datos_texto.append("\n--- CUESTIONARIO ---")
                    datos_texto.append(step.get("respuestas", ""))
                elif step.get("type") == "entrevista":
                    datos_texto.append("\n--- ENTREVISTA ---")
                    datos_texto.append(step.get("transcripcion", ""))

        synthesis_prompt = (
            base_prompt
            + "\n\n" + "="*50 + "\n"
            + "DATOS RECOPILADOS:\n"
            + "\n".join(datos_texto)
        )

        llm_client_s = self._fresh_llm_client()
        resultado_texto = llm_client_s.generate(synthesis_prompt)

        # 4) Resultado final (analisis.json)
        final_filename = "analisis.json"
        usuario_basico: Dict[str, Any]
        if len(respondents_artifacts) == 1:
            usuario_basico = dict(respondents_artifacts[0].get("perfil_basico") or {})
        else:
            usuario_basico = {"mode": "population", "arquetipo": "Población"}

        final = {
            "timestamp": self._run_iso,
            "resultado_id": self._run_ts, # Usamos el timestamp de la carpeta como ID
            "usuario": usuario_basico,
            "usuario_nombre": nombre_usuario,
            "producto": self.producto,
            "investigacion": {
                "descripcion": self.investigacion_descripcion,
                "objetivo": self.investigacion_objetivo,
                "preguntas": self.investigacion_preguntas,
                "estilo_investigacion": self.estilo_investigacion,
            },
            "resultado": resultado_texto,
            "plan": self.plan,
            "respondents": respondents_meta,
            "artifacts": {
                "plan_id": "plan.json",
            },
        }
        self._save_json(final_filename, final)
        return final

    def execute_stream(self, cancel_check=None):
        def _is_cancelled() -> bool:
            try:
                return bool(cancel_check()) if callable(cancel_check) else False
            except Exception:
                return False

        # Guardar configuraciones utilizadas
        self._save_json("producto.json", self.producto, subdir="configs")
        self._save_json("investigacion.json", {
            "descripcion": self.investigacion_descripcion,
            "objetivo": self.investigacion_objetivo,
            "preguntas": self.investigacion_preguntas,
        }, subdir="configs")
        self._save_json("respondientes_config.json", {"respondents": self.respondents}, subdir="configs")

        # Guardar plan
        plan_id = "plan.json"
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
            if _is_cancelled():
                yield {"event": "cancelled", "message": "Investigación cancelada por el usuario."}
                return
            arquetipo = (perfil_basico or {}).get("arquetipo", "Personalizado") if isinstance(perfil_basico, dict) else "Personalizado"
            yield {
                "event": "respondent_start",
                "i": idx + 1,
                "n": total,
                "arquetipo": arquetipo,
                "message": f"Respondiente {idx+1}/{total} ({arquetipo})",
            }

            llm_client_r = self._fresh_llm_client()
            usuario = SyntheticUser(perfil_basico if isinstance(perfil_basico, dict) else {})
            perfil_det = usuario.generate_profile(llm_client_r, self.prompt_perfil)
            perfil_text = (perfil_det or {}).get("perfil_generado", "")
            nombre = (perfil_det or {}).get("nombre") or usuario.nombre or f"Respondent_{idx+1}"
            
            artifact_steps: List[Dict[str, Any]] = []

            for step in steps:
                if not isinstance(step, dict):
                    continue
                stype = step.get("type")
                if not stype:
                    continue
                if _is_cancelled():
                    yield {"event": "cancelled", "message": "Investigación cancelada por el usuario."}
                    return

                yield {
                    "event": "step_start",
                    "i": idx + 1,
                    "n": total,
                    "step_type": stype,
                    "message": f"Ejecutando '{stype}' para {nombre}...",
                }

                if stype == "cuestionario":
                    questions = step.get("questions", [])
                    if not isinstance(questions, list):
                        questions = []
                    questions = [q for q in questions if isinstance(q, str) and q.strip()]
                    out = ""
                    if questions:
                        prompt = self._cuestionario_prompt(nombre, perfil_text, questions)
                        out = llm_client_r.generate(prompt)
                    artifact_steps.append({"type": "cuestionario", "questions": questions, "respuestas": out})

                elif stype == "entrevista":
                    n_questions = step.get("n_questions", 6)
                    try:
                        n_i = max(1, int(n_questions))
                    except Exception:
                        n_i = 6
                    prompt = self._entrevista_prompt(nombre, perfil_text, n_questions=n_i, seed=idx + 1)
                    out = llm_client_r.generate(prompt)
                    artifact_steps.append({"type": "entrevista", "n_questions": n_i, "transcripcion": out})

                yield {
                    "event": "step_done",
                    "i": idx + 1,
                    "n": total,
                    "step_type": stype,
                    "message": f"'{stype}' completado para {nombre}.",
                }

            respondent_filename = f"respondent_{idx+1:02d}.json"
            artifact = {
                "timestamp": self._run_iso,
                "respondent_id": respondent_filename,
                "perfil_basico": perfil_basico,
                "usuario_nombre": nombre,
                "perfil_generado": perfil_text,
                "steps": artifact_steps,
            }
            self._save_json(respondent_filename, artifact, subdir="respondents")

            respondents_meta.append({"respondent_id": respondent_filename, "arquetipo": arquetipo})
            respondents_artifacts.append(artifact)

            yield {
                "event": "respondent_done",
                "i": idx + 1,
                "n": total,
                "respondent_id": respondent_filename,
                "message": f"Respondiente {idx+1}/{total} guardado.",
            }

        if _is_cancelled():
            yield {"event": "cancelled", "message": "Investigación cancelada por el usuario."}
            return
        
        yield {"event": "synthesis_start", "message": "Generando síntesis agregada..."}
        prompt_template = self.prompt_sintesis or DEFAULT_PROMPTS["sintesis"]

        if len(respondents_artifacts) == 1:
            nombre_usuario = "1 respondiente"
        else:
            counts: Dict[str, int] = {}
            for r in respondents_meta:
                a = r.get("arquetipo") or "Personalizado"
                counts[a] = counts.get(a, 0) + 1
            mix = ", ".join(f"{k} x{v}" for k, v in counts.items())
            nombre_usuario = f"{len(respondents_meta)} respondientes ({mix})"

        base_prompt = prompt_template.format(
            nombre_usuario=nombre_usuario,
            nombre_producto=self.producto.get("nombre_producto", "Producto"),
            descripcion_producto=self.producto.get("descripcion", ""),
            investigacion_descripcion=self.investigacion_descripcion,
            investigacion_objetivo=self.investigacion_objetivo,
            investigacion_preguntas=self.investigacion_preguntas,
        )

        # Crear un resumen de datos más legible (texto plano en lugar de JSON)
        datos_texto = []
        for r, a in zip(respondents_meta, respondents_artifacts):
            arquetipo = r.get("arquetipo", "Personalizado")
            nombre = a.get("usuario_nombre", "Usuario")
            datos_texto.append(f"\n=== RESPONDIENTE: {nombre} ({arquetipo}) ===")
            
            for step in a.get("steps", []):
                if step.get("type") == "cuestionario":
                    datos_texto.append("\n--- CUESTIONARIO ---")
                    datos_texto.append(step.get("respuestas", ""))
                elif step.get("type") == "entrevista":
                    datos_texto.append("\n--- ENTREVISTA ---")
                    datos_texto.append(step.get("transcripcion", ""))

        synthesis_prompt = (
            base_prompt
            + "\n\n" + "="*50 + "\n"
            + "DATOS RECOPILADOS:\n"
            + "\n".join(datos_texto)
        )

        llm_client_s = self._fresh_llm_client()
        resultado_texto = llm_client_s.generate(synthesis_prompt)
        yield {"event": "synthesis_done", "message": "Síntesis completada."}

        final_filename = "analisis.json"
        usuario_basico: Dict[str, Any]
        if len(respondents_artifacts) == 1:
            usuario_basico = dict(respondents_artifacts[0].get("perfil_basico") or {})
        else:
            usuario_basico = {"mode": "population", "arquetipo": "Población"}

        final = {
            "timestamp": self._run_iso,
            "resultado_id": self._run_ts,
            "usuario": usuario_basico,
            "usuario_nombre": nombre_usuario,
            "producto": self.producto,
            "investigacion": {
                "descripcion": self.investigacion_descripcion,
                "objetivo": self.investigacion_objetivo,
                "preguntas": self.investigacion_preguntas,
                "estilo_investigacion": self.estilo_investigacion,
            },
            "resultado": resultado_texto,
            "plan": self.plan,
            "respondents": respondents_meta,
            "artifacts": {
                "plan_id": "plan.json",
            },
        }
        self._save_json(final_filename, final)
        yield {"event": "done", "result": final, "message": "Investigación completada."}
