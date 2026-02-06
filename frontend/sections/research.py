import streamlit as st
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar config
sys.path.append(str(Path(__file__).parent.parent))
from utils import cargar_config, existe_config

def render_investigacion():
    st.markdown('<div class="section-title"><span class="material-symbols-outlined">travel_explore</span>Investigación</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Describe la investigación. Si quieres hacer una entrevista, puedes incluir las preguntas dentro de esta descripción
    (por ejemplo, una por línea).
    """)
    
    # Cargar configuración guardada si existe
    config_cargada = cargar_config("investigacion") if existe_config("investigacion") else None
    config_cargada = config_cargada if isinstance(config_cargada, dict) else {}

    # Estilo de investigación
    st.markdown("### Estilo de investigación")
    estilos = [
        "Cuestionario cerrado",
        "Entrevista abierta",
        "Observación / Shadowing",
        "Simulación de comportamiento",
        "Diarios",
        "Prototipos",
    ]

    if "investigacion_estilo" not in st.session_state:
        saved = str(config_cargada.get("estilo_investigacion") or "").strip()
        st.session_state["investigacion_estilo"] = saved if saved in estilos else "Entrevista abierta"

    st.selectbox(
        "Estilo de investigación",
        options=estilos,
        index=estilos.index(st.session_state["investigacion_estilo"]) if st.session_state["investigacion_estilo"] in estilos else 1,
        key="investigacion_estilo",
        help="Este estilo se incluirá al inicio del contexto de investigación.",
    )
    
    # Descripción de investigación (nuevo modelo)
    st.markdown("### Descripción de la investigación")

    descripcion_default = ""
    if config_cargada:
        # Migración visual desde config antigua (preguntas -> descripcion)
        if isinstance(config_cargada.get("descripcion"), str):
            descripcion_default = config_cargada.get("descripcion", "")
        elif isinstance(config_cargada.get("preguntas"), list):
            preguntas = [str(p).strip() for p in config_cargada.get("preguntas", []) if str(p).strip()]
            if preguntas:
                descripcion_default = "Investigación\n\nPreguntas:\n" + "\n".join(f"- {p}" for p in preguntas)

    if "investigacion_descripcion" not in st.session_state:
        st.session_state["investigacion_descripcion"] = descripcion_default

    st.text_area(
        "Describe el objetivo, contexto y (si aplica) preguntas",
        key="investigacion_descripcion",
        placeholder="Ejemplo:\nQueremos investigar la experiencia de uso del producto X.\n\nPreguntas:\n- ¿Qué te ha gustado?\n- ¿Qué cambiarías?\n- ¿A quién se lo recomendarías y por qué?",
        height=260,
        help="Este texto se guarda como investigación. Si incluyes preguntas (una por línea), se usarán para la entrevista."
    )
    
    # Mantener config en sesión siempre actualizada (se persistirá al cambiar de página)
    st.session_state["investigacion_config"] = {
        "estilo_investigacion": st.session_state.get("investigacion_estilo") or "Entrevista abierta",
        "descripcion": st.session_state.get("investigacion_descripcion", "") or "",
    }

    # Acciones
    st.markdown("---")
    if st.button("Resetear", use_container_width=True, key="investigacion_reset"):
        st.session_state.pop("investigacion_descripcion", None)
        st.session_state.pop("investigacion_estilo", None)
        st.session_state.pop("investigacion_config", None)
        st.session_state.pop("investigacion_config_synced_backend", None)
        st.rerun()
