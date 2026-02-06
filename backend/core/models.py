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

class UsuarioDemografia(BaseModel):
    """
    Variabilidad demográfica para la población de respondientes.
    """

    edad_min: int = Field(default=25, ge=0, le=120)
    edad_max: int = Field(default=55, ge=0, le=120)
    # 0.0 => solo mujeres, 1.0 => solo hombres
    # Compatibilidad: también aceptamos valores legacy tipo "partes" (p.ej. 1,2,3...) y los interpretamos junto a ratio_mujeres si existe.
    ratio_hombres: float = Field(default=0.5, ge=0.0, le=100.0)

    model_config = {"extra": "allow"}


class UsuarioSingle(BaseModel):
    arquetipo: str = Field(default="Personalizado")
    comportamiento: str = Field(default="")
    necesidades: str = Field(default="")
    barreras: str = Field(default="")
    # Opcional: se puede usar en prompts (p.ej. {edad}, {genero})
    edad: Optional[int] = None
    genero: Optional[str] = None


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
    demografia: Optional[UsuarioDemografia] = None


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

        # Aplicar variabilidad demográfica (si existe)
        if isinstance(pop.demografia, UsuarioDemografia):
            import random

            n = len(respondents)
            d = pop.demografia

            # Edad
            lo = int(d.edad_min)
            hi = int(d.edad_max)
            if hi < lo:
                lo, hi = hi, lo

            # Género (ratio 0..1)
            men_fraction: Optional[float] = None
            raw = None
            try:
                raw = float(getattr(d, "ratio_hombres", 0.5))
            except Exception:
                raw = None

            if raw is None:
                men_fraction = None
            elif 0.0 <= raw <= 1.0:
                # Nuevo esquema: fracción
                men_fraction = raw
            else:
                # Legacy: ratio por partes (ej. 1..N). Se interpreta con ratio_mujeres si existe.
                try:
                    rh_parts = max(0.0, float(raw))
                    extra = getattr(d, "model_extra", {}) or {}
                    rw_parts = float(extra.get("ratio_mujeres") or 0.0)
                    rw_parts = max(0.0, rw_parts)
                    total_parts = rw_parts + rh_parts
                    men_fraction = (rh_parts / total_parts) if total_parts > 0 else None
                except Exception:
                    men_fraction = None

            if men_fraction is None:
                genders = []
            else:
                men_fraction = max(0.0, min(1.0, float(men_fraction)))
                men_target = int(round(n * men_fraction))
                men_target = max(0, min(men_target, n))
                women_target = n - men_target
                genders = (["Hombre"] * men_target) + (["Mujer"] * women_target)
                random.shuffle(genders)

            for i, r in enumerate(respondents):
                # Edad aleatoria por respondiente
                try:
                    r.edad = random.randint(lo, hi)
                except Exception:
                    r.edad = None
                # Género según lista (si aplica)
                if genders:
                    r.genero = genders[i] if i < len(genders) else None

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

