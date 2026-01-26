import streamlit as st
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar config
sys.path.append(str(Path(__file__).parent.parent))
from config import API_BASE_URL

def render_usuarios_sinteticos():
    st.markdown('<div class="section-title">👥 Configuración de Usuarios Sintéticos</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Configure los parámetros para generar usuarios sintéticos que participarán en la investigación.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        num_usuarios = st.number_input(
            "Número de usuarios sintéticos",
            min_value=1,
            max_value=1000,
            value=10,
            step=1,
            help="Cantidad de usuarios sintéticos a generar"
        )
        
        rango_edad_min = st.number_input(
            "Edad mínima",
            min_value=18,
            max_value=100,
            value=25,
            step=1
        )
        
        rango_edad_max = st.number_input(
            "Edad máxima",
            min_value=18,
            max_value=100,
            value=65,
            step=1
        )
    
    with col2:
        generos = st.multiselect(
            "Géneros",
            options=["Masculino", "Femenino", "Otro", "Prefiero no decir"],
            default=["Masculino", "Femenino"],
            help="Géneros a incluir en la muestra"
        )
        
        ubicaciones = st.multiselect(
            "Ubicaciones geográficas",
            options=["España", "México", "Argentina", "Colombia", "Chile", "Perú"],
            default=["España"],
            help="Países de origen de los usuarios"
        )
    
    # Características adicionales
    st.markdown("### Características Adicionales")
    
    col3, col4 = st.columns(2)
    
    with col3:
        nivel_educativo = st.multiselect(
            "Nivel educativo",
            options=["Primaria", "Secundaria", "Universidad", "Postgrado"],
            default=["Secundaria", "Universidad"]
        )
        
        ingresos = st.select_slider(
            "Rango de ingresos (EUR/mes)",
            options=["< 1,000", "1,000 - 2,500", "2,500 - 5,000", "5,000 - 10,000", "> 10,000"],
            value=("1,000 - 2,500", "5,000 - 10,000")
        )
    
    with col4:
        intereses = st.multiselect(
            "Intereses",
            options=["Tecnología", "Deportes", "Arte", "Música", "Viajes", "Gastronomía", "Cine"],
            default=["Tecnología", "Viajes"]
        )
        
        experiencia_tecnologica = st.select_slider(
            "Nivel de experiencia tecnológica",
            options=["Básico", "Intermedio", "Avanzado", "Experto"],
            value=("Básico", "Avanzado")
        )
    
    # Botón para guardar configuración
    st.markdown("---")
    col_save1, col_save2, col_save3 = st.columns([1, 1, 2])
    
    with col_save1:
        if st.button("💾 Guardar Configuración", type="primary", use_container_width=True):
            # Aquí irá la lógica para enviar a la API
            config = {
                "num_usuarios": num_usuarios,
                "rango_edad": [rango_edad_min, rango_edad_max],
                "generos": generos,
                "ubicaciones": ubicaciones,
                "nivel_educativo": nivel_educativo,
                "ingresos": ingresos,
                "intereses": intereses,
                "experiencia_tecnologica": experiencia_tecnologica
            }
            st.session_state['usuarios_config'] = config
            st.success("✅ Configuración de usuarios guardada!")
    
    with col_save2:
        if st.button("🔄 Resetear", use_container_width=True):
            st.session_state['usuarios_config'] = None
            st.rerun()
    
    # Mostrar configuración guardada
    if 'usuarios_config' in st.session_state and st.session_state['usuarios_config']:
        with st.expander("📋 Ver configuración guardada"):
            st.json(st.session_state['usuarios_config'])