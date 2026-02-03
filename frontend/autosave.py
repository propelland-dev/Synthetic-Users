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
        return {"mode": "population", "population": {"n": int(n), "mix": mix_out}}

    # mode == single
    arquetipo = st.session_state.get("usuario_arquetipo") or "Personalizado"
    comportamiento = st.session_state.get("usuario_comportamiento") or ""
    necesidades = st.session_state.get("usuario_necesidades") or ""
    barreras = st.session_state.get("usuario_barreras") or ""
    return {
        "mode": "single",
        "single": {
            "arquetipo": str(arquetipo),
            "comportamiento": str(comportamiento),
            "necesidades": str(necesidades),
            "barreras": str(barreras),
        },
    }


def build_producto_config_from_state() -> Dict[str, Any]:
    existing = st.session_state.get("producto_config")
    if isinstance(existing, dict):
        return dict(existing)

    local = _load_local("producto")
    if local:
        return dict(local)

    descripcion = st.session_state.get("producto_descripcion")
    return {"descripcion": str(descripcion or "")}


def build_investigacion_config_from_state() -> Dict[str, Any]:
    existing = st.session_state.get("investigacion_config")
    if isinstance(existing, dict):
        return dict(existing)

    local = _load_local("investigacion")
    if local:
        return dict(local)

    descripcion = st.session_state.get("investigacion_descripcion")
    return {"descripcion": str(descripcion or "")}


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
    prompt_investigacion = st.session_state.get("system_prompt_investigacion")

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
    if isinstance(prompt_investigacion, str):
        cfg["prompt_investigacion"] = prompt_investigacion

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
        guardar_config("producto", cfg)
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

