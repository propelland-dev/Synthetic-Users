import streamlit as st
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Agregar el directorio padre al path para importar config
sys.path.append(str(Path(__file__).parent.parent))
from config import obtener_resultados_latest, obtener_respondiente_details, refinar_texto
from utils import cargar_config, existe_config, limpiar_respuesta_llm


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
    
    # 1. Eliminar bloques <think>...</think> completamente y manejar tags huérfanos
    html = re.sub(r'<think>.*?</think>', '', html, flags=re.DOTALL | re.IGNORECASE)
    if '</think>' in html:
        html = html.split('</think>')[-1]
    if '<think>' in html.lower():
        html = html.split('<think>')[0]
    
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


def _build_result_pdf_bytes(resultados: dict, refined_main: Optional[str] = None, refined_steps: Optional[Dict[str, str]] = None) -> bytes:
    # Import local para que el módulo solo sea necesario cuando se usa.
    from fpdf import FPDF, HTMLMixin
    import markdown as md

    ts = resultados.get("timestamp") or datetime.now().isoformat()
    usuario = resultados.get("usuario") or {}
    producto = resultados.get("producto") or {}
    investigacion = resultados.get("investigacion") or {}
    # Usar versión refinada si existe, si no la original (limpia de tags)
    resultado_texto = refined_main if refined_main else resultados.get("resultado") or ""
    resultado_id = resultados.get("resultado_id") or ""
    respondents_meta = resultados.get("respondents") or []

    class PDF(FPDF, HTMLMixin):
        def header(self):
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, "Informe de Investigación de Usuarios Sintéticos", 0, 0, "L")
            self.cell(0, 10, ts[:10], 0, 1, "R")
            self.line(10, 18, 200, 18)
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", 0, 0, "C")

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def mc(txt: str, h: float, size: int, style: str = "", align: str = "L", color=(0, 0, 0)):
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", style, size=size)
        pdf.set_text_color(*color)
        safe = _to_latin1_safe(_break_long_tokens(txt))
        pdf.multi_cell(0, h, safe, align=align)

    # Título Principal
    mc("Informe de Hallazgos", h=12, size=20, style="B", align="C", color=(31, 73, 125))
    pdf.ln(5)

    # Datos Generales
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(pdf.l_margin, pdf.get_y(), 190, 25, "F")
    
    # Calcular Mix para el PDF
    if usuario.get("mode") == "population":
        counts = {}
        for r in respondents_meta:
            if isinstance(r, dict):
                a = r.get("arquetipo") or "Personalizado"
                counts[a] = counts.get(a, 0) + 1
        mix_details = ", ".join(f"{v} {k}" for k, v in counts.items())
        mix_text = f"{len(respondents_meta)} ({mix_details})"
    else:
        mix_text = "1 (Usuario único)"

    pdf.set_y(pdf.get_y() + 2)
    mc(f"Producto: {producto.get('nombre_producto', 'N/A')}", h=6, size=11, style="B")
    mc(f"Población de estudio: {mix_text}", h=6, size=10)
    mc(f"Tipo de investigación: {investigacion.get('estilo_investigacion', 'N/A')}", h=6, size=10)
    
    pdf.ln(10)

    # --- SECCIÓN: SÍNTESIS GLOBAL ---
    mc("1. Síntesis y Resumen de Hallazgos", h=8, size=14, style="B", color=(31, 73, 125))
    pdf.line(pdf.l_margin, pdf.get_y(), 60, pdf.get_y())
    pdf.ln(4)

    # Renderizar Markdown -> HTML (fpdf2 HTMLMixin)
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(0, 0, 0)
    
    texto_final = limpiar_respuesta_llm(str(resultado_texto or ""))
    md_input = _break_long_tokens(texto_final.strip())
    html = md.markdown(md_input, extensions=["extra"])
    html = _clean_html_for_fpdf(html)
    html = _to_latin1_safe(html)
    
    try:
        pdf.write_html(html)
    except Exception:
        pdf.ln(5)
        pdf.multi_cell(0, 5, _to_latin1_safe(texto_final))

    # --- SECCIÓN: DETALLE POR RESPONDIENTE ---
    if respondents_meta:
        pdf.add_page()
        mc("2. Detalle por Respondiente", h=8, size=14, style="B", color=(31, 73, 125))
        pdf.line(pdf.l_margin, pdf.get_y(), 60, pdf.get_y())
        pdf.ln(5)

        for i, resp_meta in enumerate(respondents_meta):
            resp_id = resp_meta.get("respondent_id")
            if not resp_id or not resultado_id:
                continue
            
            # Obtener detalles del respondiente
            detalles = obtener_respondiente_details(resultado_id, resp_id)
            if not detalles:
                continue

            # Subtítulo de respondiente
            mc(f"Respondiente {i+1}: {detalles.get('usuario_nombre', 'N/A')} ({resp_meta.get('arquetipo', 'N/A')})", 
               h=8, size=12, style="B", color=(50, 50, 50))
            pdf.ln(2)

            # Perfil demográfico
            pb = detalles.get("perfil_basico", {})
            demo_text = f"Edad: {pb.get('edad', 'N/A')} | Género: {pb.get('genero', 'N/A')} | Profesión: {pb.get('profesion', 'N/A')} | Adopción: {pb.get('adopcion_tecnologica', 'N/A')}"
            mc(demo_text, h=5, size=9, style="I")
            pdf.ln(2)

            # Perfil psicológico
            mc("Perfil Psicológico:", h=6, size=10, style="B")
            perfil_limpio = limpiar_respuesta_llm(detalles.get("perfil_generado", ""))
            mc(perfil_limpio, h=5, size=9)
            pdf.ln(4)

            # Participación
            for idx_step, step in enumerate(detalles.get("steps", [])):
                stype = step.get("type", "Paso").capitalize()
                mc(f"Resultado de {stype}:", h=6, size=10, style="B")
                
                # Buscar si hay versión refinada para este paso
                step_refine_key = f"refinado_{resultado_id}_{resp_id}_{idx_step}"
                if refined_steps and step_refine_key in refined_steps:
                    part_limpia = refined_steps[step_refine_key]
                else:
                    participacion_texto = step.get("respuestas") or step.get("transcripcion") or ""
                    part_limpia = limpiar_respuesta_llm(participacion_texto)
                
                # Para evitar PDFs demasiado largos si hay mucha basura, limitamos o limpiamos
                mc(part_limpia, h=5, size=9)
                pdf.ln(3)

            pdf.ln(5)
            # Línea divisoria entre respondientes
            if i < len(respondents_meta) - 1:
                pdf.set_draw_color(200, 200, 200)
                pdf.line(pdf.l_margin, pdf.get_y(), 200 - pdf.l_margin, pdf.get_y())
                pdf.ln(5)
                pdf.set_draw_color(0, 0, 0)

    # Salida final
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
        
        # Sistema de refinado manual para el resultado principal
        resultado_texto = resultados.get("resultado", "")
        
        # Recuperar estado de refinado si existe
        refinado_key = f"refinado_main_{resultados.get('resultado_id', 'none')}"
        if refinado_key not in st.session_state:
            st.session_state[refinado_key] = limpiar_respuesta_llm(resultado_texto)
            
        col_res1, col_res2 = st.columns([4, 1])
        with col_res2:
            if st.button("✨ Refinar con IA", key="refine_main_btn"):
                system_config = cargar_config("system")
                with st.spinner("Refinando análisis..."):
                    refined = refinar_texto(resultado_texto, system_config)
                    if refined:
                        st.session_state[refinado_key] = refined
                        st.success("Refinado!")
                        st.rerun()
                    else:
                        st.error("Error al refinar")
        
        with col_res1:
            st.markdown(st.session_state[refinado_key] or "_(Sin resultado)_")

        # Artefactos por respondiente (Navegador de perfiles)
        respondents_meta = resultados.get("respondents")
        if isinstance(respondents_meta, list) and respondents_meta:
            st.markdown("---")
            with st.expander("### Navegador de Respondientes", expanded=False):
                st.caption("Selecciona un usuario para ver su perfil detallado y su participación individual.")
                
                # Crear etiquetas amigables para el selectbox
                # Ejemplo: "Respondiente 1 (Preocupado)"
                resp_options = []
                for i, r in enumerate(respondents_meta):
                    label = f"Usuario {i+1} ({r.get('arquetipo', 'Personalizado')})"
                    resp_options.append(label)
                
                selected_label = st.selectbox("Seleccionar usuario", options=resp_options, key="select_respondent")
                selected_idx = resp_options.index(selected_label)
                selected_meta = respondents_meta[selected_idx]
                
                # Botón para cargar detalles
                resultado_id = resultados.get("resultado_id")
                respondent_id = selected_meta.get("respondent_id")
                
                if resultado_id and respondent_id:
                    # Cachear en session_state para evitar llamadas repetidas
                    cache_key = f"details_{resultado_id}_{respondent_id}"
                    if cache_key not in st.session_state:
                        with st.spinner(f"Cargando detalles de {selected_label}..."):
                            details = obtener_respondiente_details(resultado_id, respondent_id)
                            st.session_state[cache_key] = details
                    
                    detalles = st.session_state.get(cache_key)
                    
                    if detalles:
                        col_p1, col_p2 = st.columns([1, 2])
                        
                        with col_p1:
                            st.markdown("#### Datos Demográficos")
                            pb = detalles.get("perfil_basico", {})
                            st.write(f"**Edad:** {pb.get('edad', 'N/A')}")
                            st.write(f"**Género:** {pb.get('genero', 'N/A')}")
                            st.write(f"**Profesión:** {pb.get('profesion', 'N/A')}")
                            st.write(f"**Adopción:** {pb.get('adopcion_tecnologica', 'N/A')}")
                            
                            with st.expander("Ver dimensiones base", expanded=False):
                                st.markdown("**Comportamiento**")
                                st.caption(pb.get("comportamiento", ""))
                                st.markdown("**Necesidades**")
                                st.caption(pb.get("necesidades", ""))
                                st.markdown("**Barreras**")
                                st.caption(pb.get("barreras", ""))
                        
                        with col_p2:
                            st.markdown("#### Perfil Psicológico")
                            perfil_texto = detalles.get("perfil_generado", "_(Sin perfil generado)_")
                            perfil_limpio = limpiar_respuesta_llm(perfil_texto)
                            st.markdown(perfil_limpio)
                        
                        st.markdown("#### Participación (Entrevista/Cuestionario)")
                        steps = detalles.get("steps", [])
                        if not steps:
                            st.info("Este usuario no tiene pasos de investigación registrados.")
                        else:
                            for idx_step, step in enumerate(steps):
                                stype = step.get("type", "Paso")
                                with st.expander(f"Ver {stype.capitalize()}", expanded=True):
                                    participacion_texto = step.get("respuestas") or step.get("transcripcion") or ""
                                    
                                    # Estado de refinado para este paso
                                    step_refine_key = f"refinado_{resultado_id}_{respondent_id}_{idx_step}"
                                    if step_refine_key not in st.session_state:
                                        st.session_state[step_refine_key] = limpiar_respuesta_llm(participacion_texto)
                                    
                                    col_step1, col_step2 = st.columns([5, 1])
                                    with col_step2:
                                        if st.button("✨ Refinar", key=f"btn_refine_{step_refine_key}"):
                                            system_config = cargar_config("system")
                                            with st.spinner("Limpiando..."):
                                                refined = refinar_texto(participacion_texto, system_config)
                                                if refined:
                                                    st.session_state[step_refine_key] = refined
                                                    st.success("Refinado!")
                                                    st.rerun()
                                                else:
                                                    st.error("Error")
                                    
                                    with col_step1:
                                        st.markdown(st.session_state[step_refine_key] or "_(Sin contenido)_")
                    else:
                        st.error("No se pudieron cargar los detalles de este respondiente.")

        # Exportar PDF
        st.markdown("---")
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("Generar PDF", key="results_generate_pdf"):
                try:
                    # Recopilar todos los textos refinados de la sesión
                    refinado_main = st.session_state.get(f"refinado_main_{resultados.get('resultado_id', 'none')}")
                    
                    # Recopilar refinados de steps (todos los que empiecen por 'refinado_')
                    refined_steps = {k: v for k, v in st.session_state.items() if k.startswith("refinado_") and k != f"refinado_main_{resultados.get('resultado_id', 'none')}"}
                    
                    pdf_bytes = _build_result_pdf_bytes(resultados, refined_main=refinado_main, refined_steps=refined_steps)
                    st.session_state["pdf_resultados_bytes"] = pdf_bytes
                    st.session_state["pdf_resultados_ts"] = resultados.get("timestamp") or ""
                    st.success("✅ PDF generado. Ya puedes descargarlo.")
                except Exception as e:
                    st.warning(f"No se pudo generar el PDF: {e}")
                    import traceback
                    st.error(traceback.format_exc())

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
