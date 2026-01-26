import streamlit as st
from sections.syntetic_users import render_usuarios_sinteticos
from sections.product import render_producto
from sections.research import render_investigacion
from sections.results import render_resultados

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Usuarios Sintéticos",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .section-title {
        font-size: 1.8rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 1.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #3498db;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar - Navegación
st.sidebar.title("🧭 Navegación")
st.sidebar.markdown("---")

# Opciones del menú
menu_options = {
    "👥 Usuarios Sintéticos": "usuarios",
    "📦 Producto": "producto",
    "🔬 Investigación": "investigacion",
    "📊 Resultados": "resultados"
}

# Selección de sección
selected = st.sidebar.radio(
    "Selecciona una sección:",
    options=list(menu_options.keys()),
    label_visibility="collapsed"
)

# Obtener la clave de la sección seleccionada
section_key = menu_options[selected]

# Contenido principal
st.markdown(f'<div class="main-header">Sistema de Usuarios Sintéticos</div>', unsafe_allow_html=True)

# Renderizar la sección seleccionada
if section_key == "usuarios":
    render_usuarios_sinteticos()
elif section_key == "producto":
    render_producto()
elif section_key == "investigacion":
    render_investigacion()
elif section_key == "resultados":
    render_resultados()