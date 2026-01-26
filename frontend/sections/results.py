import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar config
sys.path.append(str(Path(__file__).parent.parent))
from config import API_BASE_URL

def render_resultados():
    st.markdown('<div class="section-title">📊 Resultados de la Investigación</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Visualiza y analiza los resultados de la investigación con usuarios sintéticos.
    """)
    
    # Estado de la investigación
    st.markdown("### Estado de la Investigación")
    
    col_status1, col_status2, col_status3, col_status4 = st.columns(4)
    
    with col_status1:
        st.metric("Estado", "En progreso", delta=None)
    
    with col_status2:
        st.metric("Usuarios activos", "8/10", delta="2 nuevos")
    
    with col_status3:
        st.metric("Días transcurridos", "3/7", delta=None)
    
    with col_status4:
        st.metric("Completitud", "42%", delta="+5%")
    
    # Resumen ejecutivo
    st.markdown("### Resumen Ejecutivo")
    
    with st.expander("📈 Ver resumen ejecutivo", expanded=True):
        st.markdown("""
        **Hallazgos principales:**
        - Los usuarios sintéticos muestran una alta satisfacción inicial (NPS promedio: 7.2/10)
        - La funcionalidad X es la más utilizada (85% de los usuarios)
        - Se identificaron 3 áreas de mejora principales
        
        **Recomendaciones:**
        1. Mejorar la navegación en la sección Y
        2. Optimizar el proceso de onboarding
        3. Agregar más opciones de personalización
        """)
    
    # Métricas principales
    st.markdown("### Métricas Principales")
    
    col_met1, col_met2 = st.columns(2)
    
    with col_met1:
        st.markdown("#### Satisfacción (NPS)")
        # Datos de ejemplo
        nps_data = pd.DataFrame({
            'Fecha': pd.date_range('2025-01-20', periods=7, freq='D'),
            'NPS': [6.5, 6.8, 7.0, 7.2, 7.1, 7.3, 7.2]
        })
        st.line_chart(nps_data.set_index('Fecha'))
    
    with col_met2:
        st.markdown("#### Tasa de Uso Diario")
        uso_data = pd.DataFrame({
            'Fecha': pd.date_range('2025-01-20', periods=7, freq='D'),
            'Usuarios activos': [5, 6, 7, 8, 8, 9, 8]
        })
        st.bar_chart(uso_data.set_index('Fecha'))
    
    # Feedback de usuarios
    st.markdown("### Feedback de Usuarios Sintéticos")
    
    # Tabla de feedback (datos de ejemplo)
    feedback_data = pd.DataFrame({
        'Usuario': [f'Usuario {i}' for i in range(1, 6)],
        'Fecha': ['2025-01-24', '2025-01-23', '2025-01-24', '2025-01-22', '2025-01-24'],
        'Puntuación': [8, 7, 9, 6, 8],
        'Comentario': [
            'Muy intuitiva la interfaz',
            'Falta más información en el onboarding',
            'Excelente experiencia general',
            'Algunos botones son difíciles de encontrar',
            'Me encanta la funcionalidad X'
        ]
    })
    
    st.dataframe(feedback_data, use_container_width=True, hide_index=True)
    
    # Análisis por segmentos
    st.markdown("### Análisis por Segmentos")
    
    segmento_seleccionado = st.selectbox(
        "Selecciona un segmento para analizar",
        options=["Por edad", "Por género", "Por ubicación", "Por nivel educativo"]
    )
    
    if segmento_seleccionado == "Por edad":
        segment_data = pd.DataFrame({
            'Segmento': ['18-30', '31-45', '46-60', '60+'],
            'NPS Promedio': [7.5, 7.2, 6.8, 6.5],
            'Usuarios': [3, 4, 2, 1]
        })
        st.bar_chart(segment_data.set_index('Segmento'))
    
    # Exportar resultados
    st.markdown("---")
    col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 2])
    
    with col_exp1:
        if st.button("📥 Exportar PDF", use_container_width=True):
            st.info("📄 Generando reporte PDF...")
    
    with col_exp2:
        if st.button("📊 Exportar Excel", use_container_width=True):
            st.info("📊 Generando archivo Excel...")
    
    # Botón para refrescar datos
    if st.button("🔄 Actualizar Resultados"):
        st.info("🔄 Actualizando datos desde la API...")
        # Aquí irá la lógica para obtener datos actualizados de la API
