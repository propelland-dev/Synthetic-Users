import streamlit as st
import sys
import re
from pathlib import Path
from datetime import datetime

# Agregar el directorio padre al path para importar config
sys.path.append(str(Path(__file__).parent.parent))
from config import obtener_resultados_latest


def _to_latin1_safe(text: str) -> str:
    """Evita errores de encoding en PDF (fpdf usa latin-1 por defecto)."""
    if text is None:
        return ""
    return str(text).encode("latin-1", errors="replace").decode("latin-1")

def _break_long_tokens(text: str, max_token_len: int = 60) -> str:
    """
    Inserta espacios en tokens demasiado largos (URLs, hashes, etc.) para evitar
    errores de fpdf2 del tipo "Not enough horizontal space to render a single character".
    """
    if not text:
        return ""
    out_parts = []
    for token in str(text).split(" "):
        if len(token) <= max_token_len:
            out_parts.append(token)
            continue
        chunks = [token[i:i + max_token_len] for i in range(0, len(token), max_token_len)]
        out_parts.append(" ".join(chunks))
    return " ".join(out_parts)


def _clean_html_for_fpdf(html: str) -> str:
    """
    Limpia el HTML para evitar errores en fpdf2 HTMLMixin.
    1. Elimina bloques <think>...</think> (razonamiento interno de LLMs).
    2. Reemplaza <strong> por <b> y <em> por <i>.
    3. Elimina tags anidados dentro de <td> y <th> que fpdf2 no soporta.
    4. Elimina thead, tbody, tfoot para simplificar la estructura de tablas.
    """
    if not html:
        return ""
    
    # 1. Eliminar bloques <think>...</think> completamente
    html = re.sub(r'<think>.*?</think>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. Reemplazos básicos de tags que fpdf2 sí soporta pero markdown genera como strong/em
    html = re.sub(r'<(strong|b)>', '<b>', html, flags=re.IGNORECASE)
    html = re.sub(r'</(strong|b)>', '</b>', html, flags=re.IGNORECASE)
    html = re.sub(r'<(em|i)>', '<i>', html, flags=re.IGNORECASE)
    html = re.sub(r'</(em|i)>', '</i>', html, flags=re.IGNORECASE)

    # 3. Función para limpiar el contenido de las celdas (fpdf2 no soporta tags anidados en <td>)
    def clean_cell(match):
        tag_open = match.group(1) or ""
        content = match.group(2) or ""
        tag_close = match.group(3) or ""
        # Eliminar todos los tags HTML del contenido de la celda
        clean_content = re.sub(r'<[^>]+>', '', content)
        return f"{tag_open}{clean_content}{tag_close}"

    # Limpiar <td> y <th>
    html = re.sub(r'(<td[^>]*>)(.*?)(</td>)', clean_cell, html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'(<th[^>]*>)(.*?)(</th>)', clean_cell, html, flags=re.DOTALL | re.IGNORECASE)

    # 4. Eliminar tags que suelen dar problemas en fpdf2 HTMLMixin (thead/tbody/tfoot)
    html = re.sub(r'</?(thead|tbody|tfoot)[^>]*>', '', html, flags=re.IGNORECASE)
    
    return html


def _build_result_pdf_bytes(resultados: dict) -> bytes:
    # Import local para que el módulo solo sea necesario cuando se usa.
    from fpdf import FPDF, HTMLMixin
    import markdown as md

    ts = resultados.get("timestamp") or datetime.now().isoformat()
    usuario = resultados.get("usuario") or {}
    producto = resultados.get("producto") or {}
    investigacion = resultados.get("investigacion") or {}
    resultado_texto = resultados.get("resultado") or ""

    class PDF(FPDF, HTMLMixin):
        pass

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def mc(txt: str, h: float, size: int):
        # Asegura que el cursor vuelve al margen izquierdo antes de escribir
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", size=size)
        safe = _to_latin1_safe(_break_long_tokens(txt))
        pdf.multi_cell(0, h, safe)

    mc("Resultados de la investigación", h=10, size=16)
    pdf.ln(2)

    # Resumen consolidado para el PDF
    pdf.set_font("Helvetica", "B", size=11)
    
    # Calcular Mix para el PDF
    if usuario.get("mode") == "population":
        respondents = resultados.get("respondents") or []
        counts = {}
        for r in respondents:
            if isinstance(r, dict):
                a = r.get("arquetipo") or "Personalizado"
                counts[a] = counts.get(a, 0) + 1
        mix_details = ", ".join(f"{v} {k}" for k, v in counts.items())
        mix_text = f"{len(respondents)} ({mix_details})"
    else:
        mix_text = "1 (Usuario único)"

    mc(f"Producto: {producto.get('nombre_producto', 'N/A')}", h=6, size=11)
    mc(f"Estilo de investigación: {investigacion.get('estilo_investigacion', 'N/A')}", h=6, size=11)
    mc(f"Población: {mix_text}", h=6, size=11)
    
    pdf.ln(2)
    mc(f"Timestamp: {ts}", h=5, size=9)
    pdf.ln(3)

    if producto.get("descripcion"):
        pdf.ln(1)
        mc("Descripción del producto:", h=6, size=11)
        mc(producto.get("descripcion", ""), h=5, size=10)

    if investigacion.get("descripcion"):
        pdf.ln(2)
        mc("Descripción de la investigación:", h=6, size=11)
        mc(investigacion.get("descripcion", ""), h=5, size=10)

    pdf.ln(3)
    mc("Resultado:", h=6, size=11)
    # Renderizar Markdown -> HTML (fpdf2 HTMLMixin)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", size=10)
    # Asegurar que resultado_texto no sea None
    texto_final = resultado_texto if resultado_texto is not None else ""
    md_input = _break_long_tokens(texto_final)
    html = md.markdown(md_input, extensions=["extra"])
    html = _clean_html_for_fpdf(html)
    html = _to_latin1_safe(html)
    pdf.write_html(html)

    # fpdf2: output(dest="S") puede devolver str, bytes o bytearray según versión/config
    out = pdf.output(dest="S")
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return str(out).encode("latin-1")

def render_resultados():
    st.markdown('<div class="section-title"><span class="material-symbols-outlined">analytics</span>Resultados de la Investigación</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Visualiza el resultado generado a partir de tu investigación.
    """)
    
    # Verificar si hay resultados guardados
    if 'resultados_investigacion' in st.session_state and st.session_state['resultados_investigacion']:
        resultados = st.session_state['resultados_investigacion']
        
        # Mostrar información consolidada
        if 'usuario' in resultados:
            usuario = resultados['usuario']
            producto = resultados.get("producto") or {}
            investigacion = resultados.get("investigacion") or {}
            
            # Calcular Mix de población si aplica
            mix_text = ""
            if usuario.get("mode") == "population":
                respondents = resultados.get("respondents") or []
                counts = {}
                for r in respondents:
                    if isinstance(r, dict):
                        a = r.get("arquetipo") or "Personalizado"
                        counts[a] = counts.get(a, 0) + 1
                mix_details = ", ".join(f"{v} {k}" for k, v in counts.items())
                mix_text = f"{len(respondents)} ({mix_details})"
            else:
                mix_text = "1 (Usuario único)"

            info_box = f"""
            **Producto:** {producto.get('nombre_producto', 'N/A')}  
            **Estilo de investigación:** {investigacion.get('estilo_investigacion', 'N/A')}  
            **Población:** {mix_text}
            """
            st.info(info_box)

            # Si viene un usuario single, mostramos dimensiones en un expander
            if usuario.get("mode") != "population":
                with st.expander("Ver detalles del usuario (Comportamiento / Necesidades / Barreras)", expanded=False):
                    st.markdown("**Comportamiento**")
                    st.write(usuario.get("comportamiento", ""))
                    st.markdown("**Necesidades**")
                    st.write(usuario.get("necesidades", ""))
                    st.markdown("**Barreras**")
                    st.write(usuario.get("barreras", ""))
            
        # Resultado único
        st.markdown("### Resultado de la investigación")
        resultado_texto = resultados.get("resultado", "")
        
        # Limpiar etiquetas <think> para la visualización en Streamlit
        resultado_limpio = re.sub(r'<think>.*?</think>', '', resultado_texto, flags=re.DOTALL | re.IGNORECASE)
        st.markdown(resultado_limpio or "_(Sin resultado)_")

        # Artefactos por respondiente (si existen)
        respondents = resultados.get("respondents")
        if isinstance(respondents, list) and respondents:
            with st.expander("Ver respondientes (IDs)", expanded=False):
                st.write("Cada respondiente genera un artefacto JSON guardado en el backend.")
                st.json(respondents)

        # Exportar PDF
        st.markdown("---")
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("Generar PDF", key="results_generate_pdf"):
                try:
                    pdf_bytes = _build_result_pdf_bytes(resultados)
                    st.session_state["pdf_resultados_bytes"] = pdf_bytes
                    st.session_state["pdf_resultados_ts"] = resultados.get("timestamp") or ""
                    st.success("✅ PDF generado. Ya puedes descargarlo.")
                except Exception as e:
                    st.warning(f"No se pudo generar el PDF: {e}")

            pdf_bytes = st.session_state.get("pdf_resultados_bytes")
            if pdf_bytes:
                ts = (st.session_state.get("pdf_resultados_ts") or "").replace(":", "").replace(".", "")
                filename = f"resultados_investigacion_{ts or 'export'}.pdf"
                st.download_button(
                    "Descargar PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    key="results_download_pdf",
                )
        
        # Botón para refrescar
        with col_b:
            if st.button("Actualizar Resultados", key="results_refresh"):
                with st.spinner("🔄 Actualizando datos desde la API..."):
                    resultado = obtener_resultados_latest()
                    if resultado:
                        st.session_state['resultados_investigacion'] = resultado
                        # invalidar PDF generado (ya no corresponde)
                        st.session_state.pop("pdf_resultados_bytes", None)
                        st.session_state.pop("pdf_resultados_ts", None)
                        st.success("✅ Resultados actualizados!")
                        st.rerun()
                    else:
                        st.warning("⚠️ No se pudieron obtener resultados actualizados. Verifica que el backend esté corriendo.")
    
    else:
        st.info("📭 No hay resultados disponibles aún. Inicia una investigación desde la sección de Investigación.")
        
        # Mostrar estado de las configuraciones
        st.markdown("### Estado de las Configuraciones")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.session_state.get('usuario_config'):
                st.success("✅ Usuario configurado")
            else:
                st.warning("⚠️ Usuario no configurado")
        
        with col2:
            if st.session_state.get('producto_config'):
                st.success("✅ Producto configurado")
            else:
                st.warning("⚠️ Producto no configurado")
        
        with col3:
            if st.session_state.get('investigacion_config'):
                st.success("✅ Investigación configurada")
            else:
                st.warning("⚠️ Investigación no configurada")
