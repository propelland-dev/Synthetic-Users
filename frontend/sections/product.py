import streamlit as st
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar config
sys.path.append(str(Path(__file__).parent.parent))
from config import API_BASE_URL

def render_producto():
    st.markdown('<div class="section-title">📦 Configuración del Producto</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Configure los detalles del producto o servicio que será evaluado por los usuarios sintéticos.
    """)
    
    # Información básica del producto
    col1, col2 = st.columns(2)
    
    with col1:
        nombre_producto = st.text_input(
            "Nombre del producto",
            placeholder="Ej: Nueva App Móvil",
            help="Nombre del producto o servicio"
        )
        
        categoria = st.selectbox(
            "Categoría",
            options=["Tecnología", "E-commerce", "Fintech", "Salud", "Educación", "Entretenimiento", "Otro"],
            help="Categoría principal del producto"
        )
        
        tipo_producto = st.selectbox(
            "Tipo de producto",
            options=["Aplicación móvil", "Plataforma web", "Servicio", "Producto físico", "Híbrido"],
            help="Tipo de producto o servicio"
        )
    
    with col2:
        version = st.text_input(
            "Versión",
            placeholder="v1.0.0",
            help="Versión del producto"
        )
        
        estado = st.selectbox(
            "Estado del producto",
            options=["En desarrollo", "Beta", "Lanzado", "Actualización"],
            help="Estado actual del producto"
        )
    
    # Descripción del producto
    st.markdown("### Descripción del Producto")
    descripcion = st.text_area(
        "Descripción detallada",
        placeholder="Describe las características principales, funcionalidades y propuesta de valor del producto...",
        height=150,
        help="Descripción completa del producto"
    )
    
    # Características principales
    st.markdown("### Características Principales")
    
    col3, col4 = st.columns(2)
    
    with col3:
        caracteristicas = st.text_area(
            "Lista de características",
            placeholder="• Característica 1\n• Característica 2\n• Característica 3",
            height=100,
            help="Lista las características principales del producto"
        )
        
        precio = st.number_input(
            "Precio (EUR)",
            min_value=0.0,
            value=0.0,
            step=0.01,
            help="Precio del producto o servicio"
        )
    
    with col4:
        publico_objetivo = st.text_area(
            "Público objetivo",
            placeholder="Describe el público objetivo del producto...",
            height=100,
            help="Descripción del público objetivo"
        )
        
        modelo_negocio = st.selectbox(
            "Modelo de negocio",
            options=["Gratis", "Freemium", "Suscripción", "Pago único", "Publicidad", "Híbrido"],
            help="Modelo de negocio del producto"
        )
    
    # Archivos adjuntos (opcional)
    st.markdown("### Archivos Adicionales")
    archivo = st.file_uploader(
        "Subir documentación adicional (opcional)",
        type=['pdf', 'docx', 'txt'],
        help="Documentación adicional sobre el producto"
    )
    
    if archivo is not None:
        st.info(f"📄 Archivo cargado: {archivo.name}")
    
    # Botones de acción
    st.markdown("---")
    col_save1, col_save2, col_save3 = st.columns([1, 1, 2])
    
    with col_save1:
        if st.button("💾 Guardar Configuración", type="primary", use_container_width=True):
            config = {
                "nombre_producto": nombre_producto,
                "categoria": categoria,
                "tipo_producto": tipo_producto,
                "version": version,
                "estado": estado,
                "descripcion": descripcion,
                "caracteristicas": caracteristicas,
                "precio": precio,
                "publico_objetivo": publico_objetivo,
                "modelo_negocio": modelo_negocio
            }
            st.session_state['producto_config'] = config
            st.success("✅ Configuración del producto guardada!")
    
    with col_save2:
        if st.button("🔄 Resetear", use_container_width=True):
            st.session_state['producto_config'] = None
            st.rerun()
    
    # Mostrar configuración guardada
    if 'producto_config' in st.session_state and st.session_state['producto_config']:
        with st.expander("📋 Ver configuración guardada"):
            st.json(st.session_state['producto_config'])