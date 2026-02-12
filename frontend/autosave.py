from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from utils import cargar_config, existe_config, guardar_config


def _load_local(tipo: str) -> Dict[str, Any]:
    if not existe_config(tipo):
        return {}
    cfg = cargar_config(tipo)
    return dict(cfg) if isinstance(cfg, dict) else {}


def build_usuario_config_from_state() -> Dict[str, Any]:
    """
    Build the Usuario config from current Streamlit state.
    Always returns the new v2 schema:
      - {"mode": "single", "single": {...}}
      - {"mode": "population", "population": {...}}
    """
    # If already built, trust it
    existing = st.session_state.get("usuario_config")
    if isinstance(existing, dict) and existing.get("mode") in {"single", "population"}:
        return dict(existing)

    local = _load_local("usuario")
    if isinstance(local, dict) and local.get("mode") in {"single", "population"}:
        return dict(local)

    mode = st.session_state.get("usuario_mode") or "single"
    mode = "population" if str(mode).lower() == "population" else "single"

    if mode == "population":
        n = st.session_state.get("usuario_population_n")
        rows = st.session_state.get("usuario_population_rows")
        if not isinstance(n, int):
            try:
                n = int(n)
            except Exception:
                n = 10
        if not isinstance(rows, list):
            rows = []

        mix_out = []
        total = 0
        for r in rows:
            if not isinstance(r, dict):
                continue
            count = r.get("count", 0)
            try:
                count = int(count)
            except Exception:
                count = 0
            if count <= 0:
                continue
            total += count
            mix_out.append(
                {
                    "arquetipo": str(r.get("arquetipo", "Personalizado")),
                    "count": count,
                    "comportamiento": str(r.get("comportamiento", "") or ""),
                    "necesidades": str(r.get("necesidades", "") or ""),
                    "barreras": str(r.get("barreras", "") or ""),
                }
            )

        # If user over-allocates we still persist what they have (UI already shows error),
        # but we do not "fix" it silently.
        demografia = None
        if st.session_state.get("usuario_demo_enabled"):
            age_range = st.session_state.get("usuario_edad_range") or (25, 55)
            try:
                lo = int(age_range[0])
                hi = int(age_range[1])
            except Exception:
                lo, hi = 25, 55
            if hi < lo:
                lo, hi = hi, lo
            try:
                rh = float(st.session_state.get("usuario_ratio_hombres") or 0.5)
            except Exception:
                rh = 0.5
            rh = max(0.0, min(1.0, rh))
            demografia = {"edad_min": lo, "edad_max": hi, "ratio_hombres": rh}

            adopcion = st.session_state.get("usuario_population_adopcion")
            if adopcion and adopcion != "(Aleatorio)":
                demografia["adopcion_tecnologica"] = adopcion
            profesion = st.session_state.get("usuario_population_profesion")
            if profesion and profesion != "(Aleatorio)":
                demografia["profesion"] = profesion

        return {"mode": "population", "population": {"n": int(n), "mix": mix_out, "demografia": demografia}}

    # mode == single
    arquetipo = st.session_state.get("usuario_arquetipo") or "Personalizado"
    comportamiento = st.session_state.get("usuario_comportamiento") or ""
    necesidades = st.session_state.get("usuario_necesidades") or ""
    barreras = st.session_state.get("usuario_barreras") or ""
    
    single_config = {
        "arquetipo": str(arquetipo),
        "comportamiento": str(comportamiento),
        "necesidades": str(necesidades),
        "barreras": str(barreras),
    }

    if st.session_state.get("usuario_single_demo_enabled"):
        single_config["edad"] = st.session_state.get("usuario_single_edad")
        single_config["genero"] = st.session_state.get("usuario_single_genero")
        single_config["adopcion_tecnologica"] = st.session_state.get("usuario_single_adopcion")
        single_config["profesion"] = st.session_state.get("usuario_single_profesion")

    return {
        "mode": "single",
        "single": single_config,
    }


def build_producto_config_from_state() -> Dict[str, Any]:
    existing = st.session_state.get("producto_config")
    if isinstance(existing, dict):
        return dict(existing)

    local_fields = _load_local("producto")
    local_ficha = _load_local("producto_ficha")
    if local_fields:
        cfg = dict(local_fields)
        # Asegurar que `descripcion` represente el input si no hay ficha
        if not (isinstance(cfg.get("descripcion"), str) and str(cfg.get("descripcion")).strip()):
            if isinstance(cfg.get("descripcion_input"), str):
                cfg["descripcion"] = str(cfg.get("descripcion_input") or "").strip()

        ficha = ""
        if isinstance(local_ficha, dict):
            ficha = str(local_ficha.get("ficha_producto") or "").strip()
        if ficha:
            # Si hay ficha persistida, el `descripcion` canónico para investigación es la ficha
            cfg["ficha_producto"] = ficha
            cfg["descripcion"] = ficha
        return cfg

    # Nuevo esquema guiado (con fallback a descripción input)
    producto_tipo = st.session_state.get("producto_tipo") or "nuevo"
    nombre = (st.session_state.get("producto_nombre") or "").strip()
    descripcion_input = str(st.session_state.get("producto_descripcion_input") or "")
    ficha = str(st.session_state.get("producto_ficha") or "").strip()

    descripcion_canonica = ficha or descripcion_input
    cfg: Dict[str, Any] = {
        "producto_tipo": str(producto_tipo),
        "descripcion_input": descripcion_input,
        "problema_a_resolver": str(st.session_state.get("producto_problema") or ""),
        "propuesta_valor": str(st.session_state.get("producto_propuesta") or ""),
        "funcionalidades_clave": str(st.session_state.get("producto_funcionalidades") or ""),
        "canal_soporte": str(st.session_state.get("producto_canal_soporte") or ""),
        "productos_sustitutivos": str(st.session_state.get("producto_sustitutivos") or ""),
        "fuentes_a_ingestar": str(st.session_state.get("producto_fuentes_ingestar") or ""),
        "observaciones": str(st.session_state.get("producto_observaciones") or ""),
        "riesgos": str(st.session_state.get("producto_riesgos") or ""),
        "dependencias": str(st.session_state.get("producto_dependencias") or ""),
        "ficha_producto": ficha or None,
        "descripcion": str(descripcion_canonica or "").strip(),
    }
    if nombre:
        cfg["nombre_producto"] = nombre
    if str(producto_tipo).strip().lower() == "existente":
        url = str(st.session_state.get("producto_url") or "").strip()
        if url:
            cfg["url"] = url
        # Los adjuntos son metadatos temporales; si no existen, omitimos
        docs = st.session_state.get("producto_docs")
        fotos = st.session_state.get("producto_fotos")
        # No es trivial serializar UploadedFile; la UI ya guarda metadatos en `producto_config`.
        # Aquí no persistimos binarios.
    # Limpiar None
    return {k: v for k, v in cfg.items() if v is not None}


def build_investigacion_config_from_state() -> Dict[str, Any]:
    existing = st.session_state.get("investigacion_config")
    if isinstance(existing, dict):
        return dict(existing)

    local = _load_local("investigacion")
    if local:
        return dict(local)

    estilo = st.session_state.get("investigacion_estilo") or ""
    descripcion = st.session_state.get("investigacion_descripcion") or ""
    objetivo = st.session_state.get("investigacion_objetivo") or ""
    preguntas = st.session_state.get("investigacion_preguntas") or ""
    
    cfg: Dict[str, Any] = {
        "descripcion": str(descripcion),
        "objetivo": str(objetivo),
        "preguntas": str(preguntas),
    }
    if isinstance(estilo, str) and estilo.strip():
        cfg["estilo_investigacion"] = estilo.strip()
    return cfg


def build_system_config_from_state() -> Dict[str, Any]:
    existing = st.session_state.get("system_config")
    if isinstance(existing, dict):
        return dict(existing)

    local = _load_local("system")

    llm_provider = st.session_state.get("system_llm_provider")
    temperatura = st.session_state.get("system_temperatura")
    max_tokens = st.session_state.get("system_max_tokens")
    modelo_path = st.session_state.get("system_modelo_path")
    prompt_perfil = st.session_state.get("system_prompt_perfil")
    prompt_sintesis = st.session_state.get("system_prompt_sintesis")
    prompt_ficha_producto = st.session_state.get("system_prompt_ficha_producto")

    cfg = dict(local or {})
    if isinstance(llm_provider, str):
        cfg["llm_provider"] = llm_provider
    if temperatura is not None:
        try:
            cfg["temperatura"] = float(temperatura)
        except Exception:
            pass
    if max_tokens is not None:
        try:
            cfg["max_tokens"] = int(max_tokens)
        except Exception:
            pass
    if isinstance(modelo_path, str):
        cfg["modelo_path"] = modelo_path
    if isinstance(prompt_perfil, str):
        cfg["prompt_perfil"] = prompt_perfil
    if isinstance(prompt_sintesis, str):
        cfg["prompt_sintesis"] = prompt_sintesis
    if isinstance(prompt_ficha_producto, str):
        cfg["prompt_ficha_producto"] = prompt_ficha_producto

    # AnythingLLM optional fields
    for k in [
        "system_anythingllm_base_url",
        "system_anythingllm_api_key",
        "system_anythingllm_workspace_slug",
        "system_anythingllm_mode",
    ]:
        v = st.session_state.get(k)
        if v is None:
            continue
        cfg[k.replace("system_", "")] = v

    return {k: v for k, v in cfg.items() if v is not None}


def autosave_section(section: str) -> None:
    """
    Persist the current section's config locally (frontend/configs/*).
    This is called when navigating away from a page.
    """
    section = str(section or "").strip().lower()
    if section == "usuarios":
        cfg = build_usuario_config_from_state()
        st.session_state["usuario_config"] = cfg
        guardar_config("usuario", cfg)
        return
    if section == "producto":
        cfg = build_producto_config_from_state()
        st.session_state["producto_config"] = cfg

        # Guardar campos (sin ficha) y ficha en archivos separados
        fields_cfg = dict(cfg)
        ficha_value = str(fields_cfg.pop("ficha_producto", "") or "").strip()
        # El archivo de campos debe reflejar los inputs, no la ficha antigua.
        if isinstance(fields_cfg.get("descripcion_input"), str):
            fields_cfg["descripcion"] = str(fields_cfg.get("descripcion_input") or "").strip()
        guardar_config("producto", fields_cfg)
        # No machacar metadatos (generated_at/fields_hash) al autosave.
        existing_ficha = cargar_config("producto_ficha") if existe_config("producto_ficha") else {}
        existing_ficha = existing_ficha if isinstance(existing_ficha, dict) else {}
        merged = dict(existing_ficha)
        merged["ficha_producto"] = ficha_value
        merged.setdefault("generated_at", None)
        merged.setdefault("fields_hash", None)
        guardar_config("producto_ficha", merged)
        return
    if section == "investigacion":
        cfg = build_investigacion_config_from_state()
        st.session_state["investigacion_config"] = cfg
        guardar_config("investigacion", cfg)
        return
    if section == "config":
        cfg = build_system_config_from_state()
        st.session_state["system_config"] = cfg
        guardar_config("system", cfg)
        return

