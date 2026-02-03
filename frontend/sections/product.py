import streamlit as st
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar config
sys.path.append(str(Path(__file__).parent.parent))
from utils import cargar_config, existe_config

def render_producto():
    st.markdown('<div class="section-title">📦 Configuración del Producto</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Describe el producto/servicio o experiencia que quieres evaluar. Puede ser **cualquier cosa** (no solo chatbots).
    """)
    
    # Cargar configuración guardada si existe
    config_cargada = cargar_config("producto") if existe_config("producto") else None
    
    # Descripción del producto
    st.markdown("### Descripción")
    if "producto_descripcion" not in st.session_state:
        st.session_state["producto_descripcion"] = config_cargada.get("descripcion", "") if config_cargada else ""

    st.text_area(
        "Describe el producto",
        key="producto_descripcion",
        placeholder="Describe qué es, para quién, cómo se usa, funcionalidades, contexto, etc.",
        height=260,
        help="Esta descripción se usará como contexto en la entrevista"
    )

    # Mantener config en sesión siempre actualizada (se persistirá al cambiar de página)
    st.session_state["producto_config"] = {
        "descripcion": st.session_state.get("producto_descripcion", "") or ""
    }
    
    # Acciones
    st.markdown("---")
    if st.button("🔄 Resetear", use_container_width=True):
        st.session_state.pop("producto_descripcion", None)
        st.session_state.pop("producto_config", None)
        st.session_state.pop("producto_config_synced_backend", None)
        st.rerun()
