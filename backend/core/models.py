"""
Modelos compartidos (contratos) para el pipeline de investigación.

Objetivo:
- Soportar configuración de usuario en modo single o población (mix por arquetipos)
- Representar un plan de investigación (planner output)
- Representar artefactos por respondiente y resultado final
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# -----------------------
# UsuarioConfig (V2)
# -----------------------

class UsuarioSingle(BaseModel):
    arquetipo: str = Field(default="Personalizado")
    comportamiento: str = Field(default="")
    necesidades: str = Field(default="")
    barreras: str = Field(default="")


class UsuarioPopulationMixEntry(BaseModel):
    """
    Entrada de mix para población.

    Nota: incluimos dimensiones para que el backend no dependa del catálogo de arquetipos.
    La UI puede rellenarlas automáticamente desde `frontend/configs/arquetipos.json`.
    """

    arquetipo: str
    count: int = Field(ge=0)
    comportamiento: str = Field(default="")
    necesidades: str = Field(default="")
    barreras: str = Field(default="")


class UsuarioPopulation(BaseModel):
    n: int = Field(default=10, ge=1)
    mix: List[UsuarioPopulationMixEntry] = Field(default_factory=list)


UsuarioMode = Literal["single", "population"]


class UsuarioConfigV2(BaseModel):
    mode: UsuarioMode = Field(default="single")
    single: Optional[UsuarioSingle] = None
    population: Optional[UsuarioPopulation] = None

    @staticmethod
    def from_legacy(payload: Dict[str, Any]) -> "UsuarioConfigV2":
        """
        Mapea el esquema legacy (arquetipo+3 dimensiones en raíz) al esquema v2 (mode=single).
        """
        return UsuarioConfigV2(
            mode="single",
            single=UsuarioSingle(
                arquetipo=str(payload.get("arquetipo", "Personalizado")),
                comportamiento=str(payload.get("comportamiento", "")),
                necesidades=str(payload.get("necesidades", "")),
                barreras=str(payload.get("barreras", "")),
            ),
        )

    def to_effective_respondents(self) -> List[UsuarioSingle]:
        """
        Expande la config a una lista de respondientes (cada uno con 3 dimensiones).
        """
        if self.mode == "single":
            return [self.single or UsuarioSingle()]

        pop = self.population or UsuarioPopulation()
        respondents: List[UsuarioSingle] = []
        for entry in pop.mix:
            for _ in range(max(0, int(entry.count))):
                respondents.append(
                    UsuarioSingle(
                        arquetipo=entry.arquetipo,
                        comportamiento=entry.comportamiento,
                        necesidades=entry.necesidades,
                        barreras=entry.barreras,
                    )
                )
        # Si el mix no suma N, recortamos o completamos con "Personalizado" vacío.
        if len(respondents) > pop.n:
            respondents = respondents[: pop.n]
        elif len(respondents) < pop.n:
            missing = pop.n - len(respondents)
            respondents.extend([UsuarioSingle()] * missing)
        return respondents


# -----------------------
# ResearchPlan (planner output)
# -----------------------

ResearchStepType = Literal["survey", "interview", "behavior_sim"]
ResearchType = Literal["survey", "interview", "behavior_sim", "mixed"]


class SurveyStep(BaseModel):
    type: Literal["survey"] = "survey"
    questions: List[str] = Field(default_factory=list)


class InterviewStep(BaseModel):
    type: Literal["interview"] = "interview"
    # Entrevista en un solo turno (una sola llamada) por respondiente.
    # `questions` es opcional: si viene vacío, el motor genera preguntas implícitas.
    n_questions: int = Field(default=6, ge=1)
    questions: List[str] = Field(default_factory=list)


class BehaviorSimStep(BaseModel):
    type: Literal["behavior_sim"] = "behavior_sim"
    scenarios: List[str] = Field(default_factory=list)


class ResearchPlan(BaseModel):
    version: int = 1
    research_type: ResearchType = "mixed"
    steps: List[Any] = Field(default_factory=list)


# -----------------------
# Artefactos y resultados
# -----------------------

class RespondentArtifact(BaseModel):
    respondent_id: str
    arquetipo: str = "Personalizado"
    perfil_generado: str = ""
    steps: List[Dict[str, Any]] = Field(default_factory=list)


class InvestigationResult(BaseModel):
    """
    Resultado final agregado (archivo *_investigacion.json).
    Mantiene claves legacy para no romper la UI.
    """

    timestamp: str
    resultado_id: Optional[str] = None

    # Legacy-compatible
    usuario: Dict[str, Any] = Field(default_factory=dict)
    usuario_nombre: Optional[str] = None
    producto: Dict[str, Any] = Field(default_factory=dict)
    investigacion: Dict[str, Any] = Field(default_factory=dict)
    resultado: str = ""

    # Nuevo
    plan: Optional[Dict[str, Any]] = None
    respondents: Optional[List[Dict[str, Any]]] = None

