import streamlit as st
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar config
sys.path.append(str(Path(__file__).parent.parent))
from datetime import datetime
import hashlib
import json
from utils import cargar_config, existe_config, guardar_config
from config import generar_ficha_producto

def _fields_snapshot(
    producto_tipo: str,
    nombre_producto: str,
    descripcion_input: str,
    problema_a_resolver: str,
    propuesta_valor: str,
    funcionalidades_clave: str,
    canal_soporte: str,
    productos_sustitutivos: str,
    fuentes_a_ingestar: str,
    observaciones: str,
    riesgos: str,
    dependencias: str,
    url: str,
) -> dict:
    # Nota: por ahora no incluimos adjuntos en el hash.
    return {
        "producto_tipo": str(producto_tipo or ""),
        "nombre_producto": str(nombre_producto or ""),
        "descripcion_input": str(descripcion_input or ""),
        "problema_a_resolver": str(problema_a_resolver or ""),
        "propuesta_valor": str(propuesta_valor or ""),
        "funcionalidades_clave": str(funcionalidades_clave or ""),
        "canal_soporte": str(canal_soporte or ""),
        "productos_sustitutivos": str(productos_sustitutivos or ""),
        "fuentes_a_ingestar": str(fuentes_a_ingestar or ""),
        "observaciones": str(observaciones or ""),
        "riesgos": str(riesgos or ""),
        "dependencias": str(dependencias or ""),
        "url": str(url or ""),
    }


def _hash_fields(fields: dict) -> str:
    payload = json.dumps(fields or {}, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def render_producto():
    st.markdown('<div class="section-title"><span class="material-symbols-outlined">inventory_2</span>Configuración del Producto</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Describe el producto/servicio o experiencia que quieres evaluar.
    """)
    
    # Cargar configuración guardada si existe (campos + ficha)
    config_cargada = cargar_config("producto") if existe_config("producto") else None
    config_cargada = config_cargada if isinstance(config_cargada, dict) else {}
    ficha_cargada = cargar_config("producto_ficha") if existe_config("producto_ficha") else None
    ficha_cargada = ficha_cargada if isinstance(ficha_cargada, dict) else {}

    # Tipo de producto
    st.markdown("### Tipo de producto")
    if "producto_tipo" not in st.session_state:
        st.session_state["producto_tipo"] = config_cargada.get("producto_tipo", "nuevo") or "nuevo"

    tipo_label = st.radio(
        "¿Es un producto nuevo o un producto existente?",
        options=["Producto nuevo", "Producto existente"],
        index=0 if st.session_state["producto_tipo"] != "existente" else 1,
        horizontal=True,
        key="producto_tipo_radio",
    )
    producto_tipo = "existente" if tipo_label == "Producto existente" else "nuevo"
    st.session_state["producto_tipo"] = producto_tipo

    # Campos comunes (guiados)
    st.markdown("### Parámetros (guiados)")
    #st.caption("Puedes rellenar solo la descripción si lo prefieres; la ficha se generará igualmente.")

    if "producto_nombre" not in st.session_state:
        st.session_state["producto_nombre"] = config_cargada.get("nombre_producto", "") or ""
    if "producto_descripcion_input" not in st.session_state:
        # Compatibilidad: si antes solo existía `descripcion`, úsalo como input libre
        st.session_state["producto_descripcion_input"] = config_cargada.get("descripcion_input") or config_cargada.get("descripcion") or ""
    if "producto_problema" not in st.session_state:
        st.session_state["producto_problema"] = config_cargada.get("problema_a_resolver", "") or ""
    if "producto_propuesta" not in st.session_state:
        st.session_state["producto_propuesta"] = config_cargada.get("propuesta_valor", "") or ""
    if "producto_funcionalidades" not in st.session_state:
        st.session_state["producto_funcionalidades"] = config_cargada.get("funcionalidades_clave", "") or ""
    if "producto_canal_soporte" not in st.session_state:
        st.session_state["producto_canal_soporte"] = config_cargada.get("canal_soporte", "") or ""
    if "producto_sustitutivos" not in st.session_state:
        st.session_state["producto_sustitutivos"] = config_cargada.get("productos_sustitutivos", "") or ""
    if "producto_fuentes_ingestar" not in st.session_state:
        st.session_state["producto_fuentes_ingestar"] = config_cargada.get("fuentes_a_ingestar", "") or ""
    if "producto_observaciones" not in st.session_state:
        st.session_state["producto_observaciones"] = config_cargada.get("observaciones", "") or ""
    if "producto_riesgos" not in st.session_state:
        st.session_state["producto_riesgos"] = config_cargada.get("riesgos", "") or ""
    if "producto_dependencias" not in st.session_state:
        st.session_state["producto_dependencias"] = config_cargada.get("dependencias", "") or ""
    # Mantener session_state alineado con el archivo de ficha:
    # - si no existe en sesión, cargar
    # - si existe vacío pero el archivo tiene ficha, cargar
    ficha_archivo = str(ficha_cargada.get("ficha_producto") or "")
    if "producto_ficha" not in st.session_state:
        st.session_state["producto_ficha"] = ficha_archivo
    else:
        if (not str(st.session_state.get("producto_ficha") or "").strip()) and ficha_archivo.strip():
            st.session_state["producto_ficha"] = ficha_archivo

    col_a, col_b = st.columns([2, 3])
    with col_a:
        st.text_input("Nombre", key="producto_nombre", placeholder="Ej.: Moeve Assistant")
    with col_b:
        st.text_area(
            "Descripción",
            key="producto_descripcion_input",
            height=110,
            placeholder="Describe el producto con el detalle que tengas disponible (puede ser lo único que rellenes).",
        )

    with st.expander("Value / Problema", expanded=True):
        st.text_area("Problema a resolver", key="producto_problema", height=110)
        st.text_area("Propuesta de valor", key="producto_propuesta", height=110)

    with st.expander("Producto / Operación", expanded=False):
        st.text_area("Funcionalidades clave", key="producto_funcionalidades", height=110)
        st.text_area("Canal de soporte", key="producto_canal_soporte", height=90, placeholder="Ej.: call center, app, email, WhatsApp...")
        st.text_area("Productos sustitutivos", key="producto_sustitutivos", height=90)

    with st.expander("Datos / Ingesta", expanded=False):
        st.text_area(
            "Fuentes a ingestar",
            key="producto_fuentes_ingestar",
            height=110,
            placeholder="URLs, nombres de documentos, repositorios, FAQs, etc.",
        )

    with st.expander("Gestión", expanded=False):
        st.text_area("Observaciones", key="producto_observaciones", height=90)
        st.text_area("Riesgos", key="producto_riesgos", height=90)
        st.text_area("Dependencias", key="producto_dependencias", height=90)

    # Adjuntos (siempre visibles; habilitados solo si es existente)
    documentos_meta = []
    fotos_meta = []
    url = ""
    is_existente = producto_tipo == "existente"
    with st.expander("Adjuntos", expanded=False):
        if "producto_url" not in st.session_state:
            st.session_state["producto_url"] = config_cargada.get("url", "") or ""

        st.caption("Solo se habilitan si el producto es **existente**.")
        url = st.text_input(
            "URL",
            key="producto_url",
            placeholder="https://...",
            disabled=not is_existente,
        )

        #st.caption("Nota: por ahora guardamos solo metadatos (nombre/tamaño). La ingesta real se implementa después.")

        def _uploader(label: str, key: str, type_):
            # Compatibilidad: `disabled` está en streamlit moderno; si no, evitamos romper
            try:
                return st.file_uploader(
                    label,
                    type=type_,
                    accept_multiple_files=True,
                    key=key,
                    disabled=not is_existente,
                )
            except TypeError:
                if not is_existente:
                    st.info("Disponible cuando selecciones “Producto existente”.")
                    return []
                return st.file_uploader(label, type=type_, accept_multiple_files=True, key=key)

        docs = _uploader("Adjuntar documento(s)", "producto_docs", None)
        pics = _uploader("Adjuntar foto(s)", "producto_fotos", ["png", "jpg", "jpeg", "webp"])

        def _meta(files):
            out = []
            for f in files or []:
                out.append(
                    {
                        "name": getattr(f, "name", ""),
                        "type": getattr(f, "type", ""),
                        "size": getattr(f, "size", None),
                    }
                )
            return out

        if is_existente:
            documentos_meta = _meta(docs)
            fotos_meta = _meta(pics)

    # Indicador: ficha desactualizada (mostrar SIEMPRE que haya ficha)
    current_fields = _fields_snapshot(
        producto_tipo=producto_tipo,
        nombre_producto=st.session_state.get("producto_nombre") or "",
        descripcion_input=st.session_state.get("producto_descripcion_input") or "",
        problema_a_resolver=st.session_state.get("producto_problema") or "",
        propuesta_valor=st.session_state.get("producto_propuesta") or "",
        funcionalidades_clave=st.session_state.get("producto_funcionalidades") or "",
        canal_soporte=st.session_state.get("producto_canal_soporte") or "",
        productos_sustitutivos=st.session_state.get("producto_sustitutivos") or "",
        fuentes_a_ingestar=st.session_state.get("producto_fuentes_ingestar") or "",
        observaciones=st.session_state.get("producto_observaciones") or "",
        riesgos=st.session_state.get("producto_riesgos") or "",
        dependencias=st.session_state.get("producto_dependencias") or "",
        url=st.session_state.get("producto_url") or "",
    )
    current_hash = _hash_fields(current_fields)
    ficha_text = str(st.session_state.get("producto_ficha") or "").strip()
    last_hash = str(ficha_cargada.get("fields_hash") or "").strip()
    generated_at = ficha_cargada.get("generated_at")

    if ficha_text:
        # Mostrar el estado cerca y claro
        st.markdown("### Estado de la ficha")
        if last_hash and last_hash != current_hash:
            st.warning("🟠 Ficha desactualizada. Has cambiado campos desde la última generación.")
        elif not last_hash:
            st.info("ℹ️ Hay ficha guardada, pero aún no se registra su estado (hash). Regénérala una vez para activar el aviso de desactualización.")
        else:
            st.success("🟢 Ficha actualizada.")
        if generated_at:
            st.caption(f"Última generación: {generated_at}")

    # Acción: generar ficha
    st.markdown("---")
    col_gen, col_info = st.columns([1, 2])
    with col_gen:
        clicked = st.button("Generar/Actualizar ficha", key="producto_generar_ficha")
    with col_info:
        st.caption("La ficha se usará como contexto del producto en la investigación.")

    if clicked:
        system_cfg = st.session_state.get("system_config")
        if not isinstance(system_cfg, dict):
            system_cfg = cargar_config("system") if existe_config("system") else {}
        if not isinstance(system_cfg, dict):
            system_cfg = {}
        if not system_cfg.get("prompt_ficha_producto"):
            st.error("Falta `prompt_ficha_producto`. Ve a Configuración y guarda la configuración del sistema.")
        else:
            producto_cfg_for_llm = {
                "producto_tipo": producto_tipo,
                "nombre_producto": st.session_state.get("producto_nombre") or "",
                "descripcion_input": st.session_state.get("producto_descripcion_input") or "",
                "problema_a_resolver": st.session_state.get("producto_problema") or "",
                "propuesta_valor": st.session_state.get("producto_propuesta") or "",
                "funcionalidades_clave": st.session_state.get("producto_funcionalidades") or "",
                "canal_soporte": st.session_state.get("producto_canal_soporte") or "",
                "productos_sustitutivos": st.session_state.get("producto_sustitutivos") or "",
                "fuentes_a_ingestar": st.session_state.get("producto_fuentes_ingestar") or "",
                "observaciones": st.session_state.get("producto_observaciones") or "",
                "riesgos": st.session_state.get("producto_riesgos") or "",
                "dependencias": st.session_state.get("producto_dependencias") or "",
                "url": st.session_state.get("producto_url") if producto_tipo == "existente" else "",
                "documentos": documentos_meta,
                "fotos": fotos_meta,
                # `descripcion` canónica se setea al guardar, aquí no hace falta
                "descripcion": st.session_state.get("producto_descripcion_input") or "",
            }
            with st.spinner("Generando ficha..."):
                ficha = generar_ficha_producto(producto_cfg_for_llm, system_cfg)
            if ficha is None:
                st.error("No se pudo generar la ficha (revisa conexión con el LLM).")
            else:
                st.session_state["producto_ficha"] = ficha
                # Persistir ficha en archivo separado inmediatamente
                guardar_config(
                    "producto_ficha",
                    {
                        "ficha_producto": ficha,
                        "generated_at": datetime.now().isoformat(),
                        "fields_hash": current_hash,
                    },
                )

    # Mantener config en sesión siempre actualizada (se persistirá al cambiar de página)
    # Por defecto, si no hay ficha, usamos la descripción input como `descripcion` canónica.
    descripcion_canonica = (st.session_state.get("producto_ficha") or "").strip() or (st.session_state.get("producto_descripcion_input") or "")
    st.session_state["producto_config"] = {
        "producto_tipo": producto_tipo,
        "nombre_producto": (st.session_state.get("producto_nombre") or "").strip() or None,
        "descripcion_input": st.session_state.get("producto_descripcion_input") or "",
        "problema_a_resolver": st.session_state.get("producto_problema") or "",
        "propuesta_valor": st.session_state.get("producto_propuesta") or "",
        "funcionalidades_clave": st.session_state.get("producto_funcionalidades") or "",
        "canal_soporte": st.session_state.get("producto_canal_soporte") or "",
        "productos_sustitutivos": st.session_state.get("producto_sustitutivos") or "",
        "fuentes_a_ingestar": st.session_state.get("producto_fuentes_ingestar") or "",
        "observaciones": st.session_state.get("producto_observaciones") or "",
        "riesgos": st.session_state.get("producto_riesgos") or "",
        "dependencias": st.session_state.get("producto_dependencias") or "",
        "url": st.session_state.get("producto_url") if producto_tipo == "existente" else None,
        "documentos": documentos_meta or None,
        "fotos": fotos_meta or None,
        "ficha_producto": (st.session_state.get("producto_ficha") or "").strip() or None,
        # Campo canónico usado por la investigación
        "descripcion": str(descripcion_canonica or "").strip(),
    }
    # Limpiar Nones para no ensuciar JSON
    st.session_state["producto_config"] = {k: v for k, v in st.session_state["producto_config"].items() if v is not None}

    with st.expander("Vista previa de la ficha", expanded=False):
        st.markdown(st.session_state["producto_config"].get("descripcion") or "_(vacío)_")
    
    # Acciones
    st.markdown("---")
    with st.expander("🧹 Limpiar producto", expanded=False):
        st.caption("Limpia los campos y la ficha guardados (último estado).")
        if st.button("Limpiar campos y ficha", type="secondary", key="producto_clear_all"):
            guardar_config(
                "producto",
                {
                    "producto_tipo": "nuevo",
                    "nombre_producto": "",
                    "descripcion_input": "",
                    "problema_a_resolver": "",
                    "propuesta_valor": "",
                    "funcionalidades_clave": "",
                    "canal_soporte": "",
                    "productos_sustitutivos": "",
                    "fuentes_a_ingestar": "",
                    "observaciones": "",
                    "riesgos": "",
                    "dependencias": "",
                    "url": "",
                    "documentos": [],
                    "fotos": [],
                    "descripcion": "",
                },
            )
            guardar_config("producto_ficha", {"ficha_producto": "", "generated_at": None})
            for k in [
                "producto_tipo",
                "producto_tipo_radio",
                "producto_nombre",
                "producto_descripcion_input",
                "producto_problema",
                "producto_propuesta",
                "producto_funcionalidades",
                "producto_canal_soporte",
                "producto_sustitutivos",
                "producto_fuentes_ingestar",
                "producto_observaciones",
                "producto_riesgos",
                "producto_dependencias",
                "producto_url",
                "producto_docs",
                "producto_fotos",
                "producto_ficha",
                "producto_config",
            ]:
                st.session_state.pop(k, None)
            st.rerun()

    if st.button("Resetear", key="producto_reset"):
        for k in [
            "producto_tipo",
            "producto_tipo_radio",
            "producto_nombre",
            "producto_descripcion_input",
            "producto_problema",
            "producto_propuesta",
            "producto_funcionalidades",
            "producto_canal_soporte",
            "producto_sustitutivos",
            "producto_fuentes_ingestar",
            "producto_observaciones",
            "producto_riesgos",
            "producto_dependencias",
            "producto_url",
            "producto_docs",
            "producto_fotos",
            "producto_ficha",
        ]:
            st.session_state.pop(k, None)
        st.session_state.pop("producto_config", None)
        st.session_state.pop("producto_config_synced_backend", None)
        st.rerun()
