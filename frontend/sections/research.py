import streamlit as st
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar config
sys.path.append(str(Path(__file__).parent.parent))
from config import API_BASE_URL

def render_investigacion():
    st.markdown('<div class="section-title">🔬 Configuración de la Investigación</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Configure los parámetros y metodología de la investigación con usuarios sintéticos.
    """)
    
    # Verificación de configuraciones previas
    if 'usuarios_config' not in st.session_state or not st.session_state.get('usuarios_config'):
        st.warning("⚠️ Primero debes configurar los usuarios sintéticos en la sección correspondiente.")
    
    if 'producto_config' not in st.session_state or not st.session_state.get('producto_config'):
        st.warning("⚠️ Primero debes configurar el producto en la sección correspondiente.")
    
    # Tipo de investigación
    st.markdown("### Tipo de Investigación")
    
    tipo_investigacion = st.selectbox(
        "Selecciona el tipo de investigación",
        options=[
            "Test de usabilidad",
            "Análisis de feedback",
            "Estudio de adopción",
            "Análisis de satisfacción",
            "Test A/B con usuarios sintéticos",
            "Análisis de comportamiento"
        ],
        help="Tipo de investigación a realizar"
    )
    
    # Objetivos de la investigación
    st.markdown("### Objetivos")
    objetivos = st.text_area(
        "Objetivos de la investigación",
        placeholder="Ej: Evaluar la usabilidad de la nueva interfaz, medir la satisfacción del usuario, etc.",
        height=100,
        help="Define los objetivos principales de la investigación"
    )
    
    # Metodología
    st.markdown("### Metodología")
    
    col1, col2 = st.columns(2)
    
    with col1:
        duracion_estimada = st.number_input(
            "Duración estimada (días)",
            min_value=1,
            max_value=365,
            value=7,
            step=1,
            help="Duración estimada de la investigación en días"
        )
        
        frecuencia_interaccion = st.selectbox(
            "Frecuencia de interacción",
            options=["Diaria", "Semanal", "Quincenal", "Mensual", "Única vez"],
            help="Con qué frecuencia interactuarán los usuarios sintéticos"
        )
    
    with col2:
        metricas = st.multiselect(
            "Métricas a evaluar",
            options=[
                "Tasa de conversión",
                "Tiempo de uso",
                "Satisfacción (NPS)",
                "Facilidad de uso",
                "Retención",
                "Engagement",
                "Errores encontrados"
            ],
            default=["Satisfacción (NPS)", "Facilidad de uso"],
            help="Métricas que se evaluarán durante la investigación"
        )
        
        nivel_detalle = st.select_slider(
            "Nivel de detalle del análisis",
            options=["Básico", "Intermedio", "Avanzado", "Muy detallado"],
            value="Intermedio"
        )
    
    # Preguntas específicas
    st.markdown("### Preguntas de Investigación")
    st.markdown("Agrega preguntas específicas que quieres que los usuarios sintéticos respondan:")
    
    preguntas = []
    num_preguntas = st.number_input(
        "Número de preguntas",
        min_value=0,
        max_value=20,
        value=3,
        step=1
    )
    
    for i in range(num_preguntas):
        pregunta = st.text_input(
            f"Pregunta {i+1}",
            placeholder=f"Ej: ¿Qué te parece la interfaz del producto?",
            key=f"pregunta_{i}"
        )
        if pregunta:
            preguntas.append(pregunta)
    
    # Escenarios de uso
    st.markdown("### Escenarios de Uso")
    escenarios = st.text_area(
        "Define escenarios de uso para los usuarios sintéticos",
        placeholder="Ej: \n1. Usuario nuevo que descarga la app por primera vez\n2. Usuario que busca una funcionalidad específica\n3. Usuario que realiza una compra",
        height=120,
        help="Escenarios que los usuarios sintéticos deberán simular"
    )
    
    # Botones de acción
    st.markdown("---")
    col_save1, col_save2, col_save3 = st.columns([1, 1, 2])
    
    with col_save1:
        if st.button("💾 Guardar Configuración", type="primary", use_container_width=True):
            config = {
                "tipo_investigacion": tipo_investigacion,
                "objetivos": objetivos,
                "duracion_estimada": duracion_estimada,
                "frecuencia_interaccion": frecuencia_interaccion,
                "metricas": metricas,
                "nivel_detalle": nivel_detalle,
                "preguntas": preguntas,
                "escenarios": escenarios
            }
            st.session_state['investigacion_config'] = config
            st.success("✅ Configuración de investigación guardada!")
    
    with col_save2:
        if st.button("🚀 Iniciar Investigación", use_container_width=True):
            # Verificar que todas las configuraciones estén listas
            if (st.session_state.get('usuarios_config') and 
                st.session_state.get('producto_config') and 
                st.session_state.get('investigacion_config')):
                st.info("🔄 Iniciando investigación... Esto enviará los datos a la API.")
                # Aquí irá la lógica para enviar todo a la API
            else:
                st.error("❌ Por favor completa todas las configuraciones antes de iniciar.")
    
    with col_save3:
        if st.button("🔄 Resetear", use_container_width=True):
            st.session_state['investigacion_config'] = None
            st.rerun()
    
    # Mostrar configuración guardada
    if 'investigacion_config' in st.session_state and st.session_state['investigacion_config']:
        with st.expander("📋 Ver configuración guardada"):
            st.json(st.session_state['investigacion_config'])
