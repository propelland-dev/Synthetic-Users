import streamlit as st
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar config
sys.path.append(str(Path(__file__).parent.parent))
from utils import cargar_config, existe_config

def render_investigacion():
    st.markdown('<div class="section-title"><span class="material-symbols-outlined">travel_explore</span>Investigación</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Describe la investigación que quieres realizar. El tipo de investigación se determinará por la opción seleccionada arriba.
    """)
    
    # Cargar configuración guardada si existe
    config_cargada = cargar_config("investigacion") if existe_config("investigacion") else None
    config_cargada = config_cargada if isinstance(config_cargada, dict) else {}

    # Estilo de investigación
    st.markdown("### Estilo de investigación")
    estilos = [
        "Cuestionario",
        "Entrevista",
    ]

    if "investigacion_estilo" not in st.session_state:
        saved = str(config_cargada.get("estilo_investigacion") or "").strip()
        # Migrar estilos antiguos a los nuevos
        if saved == "Cuestionario cerrado":
            saved = "Cuestionario"
        elif saved == "Entrevista abierta":
            saved = "Entrevista"
        st.session_state["investigacion_estilo"] = saved if saved in estilos else "Entrevista"

    st.selectbox(
        "Estilo de investigación",
        options=estilos,
        index=estilos.index(st.session_state["investigacion_estilo"]) if st.session_state["investigacion_estilo"] in estilos else 1,
        key="investigacion_estilo",
        help="Cuestionario: respuestas estructuradas a preguntas específicas. Entrevista: conversación más abierta y exploratoria.",
    )
    
    # Descripción de investigación (nuevo modelo)
    st.markdown("### Contexto de la investigación")

    descripcion_default = ""
    objetivo_default = ""
    preguntas_default = ""

    if config_cargada:
        # Migración visual desde config antigua
        if isinstance(config_cargada.get("descripcion"), str):
            descripcion_default = config_cargada.get("descripcion", "")
        
        if isinstance(config_cargada.get("objetivo"), str):
            objetivo_default = config_cargada.get("objetivo", "")
        
        if isinstance(config_cargada.get("preguntas"), str):
            preguntas_default = config_cargada.get("preguntas", "")
        elif isinstance(config_cargada.get("preguntas"), list):
            preguntas = [str(p).strip() for p in config_cargada.get("preguntas", []) if str(p).strip()]
            if preguntas:
                preguntas_default = "\n".join(f"- {p}" for p in preguntas)

    if "investigacion_descripcion" not in st.session_state:
        st.session_state["investigacion_descripcion"] = descripcion_default
    if "investigacion_objetivo" not in st.session_state:
        st.session_state["investigacion_objetivo"] = objetivo_default
    if "investigacion_preguntas" not in st.session_state:
        st.session_state["investigacion_preguntas"] = preguntas_default

    st.text_area(
        "Descripción",
        key="investigacion_descripcion",
        placeholder="Ejemplo: Queremos investigar la experiencia de uso del producto X en un entorno de oficina.",
        height=150,
        help="Describe el contexto general de la investigación."
    )

    st.text_area(
        "Objetivo",
        key="investigacion_objetivo",
        placeholder="Ejemplo: Entender qué funciones son más valoradas y cuáles generan frustración.",
        height=100,
        help="¿Qué quieres conseguir con esta investigación?"
    )

    st.text_area(
        "Preguntas",
        key="investigacion_preguntas",
        placeholder="Ejemplo:\n- ¿Qué te ha gustado?\n- ¿Qué cambiarías?\n- ¿A quién se lo recomendarías?",
        height=150,
        help="Si incluyes preguntas (una por línea), se usarán para la entrevista o cuestionario."
    )
    
    # Mantener config en sesión siempre actualizada (se persistirá al cambiar de página)
    st.session_state["investigacion_config"] = {
        "estilo_investigacion": st.session_state.get("investigacion_estilo") or "Entrevista abierta",
        "descripcion": st.session_state.get("investigacion_descripcion", "") or "",
        "objetivo": st.session_state.get("investigacion_objetivo", "") or "",
        "preguntas": st.session_state.get("investigacion_preguntas", "") or "",
    }

    # Acciones
    st.markdown("---")
    if st.button("Resetear", key="investigacion_reset"):
        st.session_state.pop("investigacion_descripcion", None)
        st.session_state.pop("investigacion_objetivo", None)
        st.session_state.pop("investigacion_preguntas", None)
        st.session_state.pop("investigacion_estilo", None)
        st.session_state.pop("investigacion_config", None)
        st.session_state.pop("investigacion_config_synced_backend", None)
        st.rerun()
        st.session_state.pop("investigacion_config", None)
        st.session_state.pop("investigacion_config_synced_backend", None)
        st.rerun()
