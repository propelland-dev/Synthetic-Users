import streamlit as st
from sections.syntetic_users import render_usuarios_sinteticos
from sections.product import render_producto
from sections.research import render_investigacion
from sections.results import render_resultados
from sections.config import render_config
from config import (
    verificar_backend,
    verificar_ollama,
    verificar_llm,
    enviar_usuario,
    enviar_producto,
    enviar_investigacion,
    generar_ficha_producto,
    iniciar_investigacion,
    iniciar_investigacion_stream,
    obtener_resultados_latest,
)
from utils import existe_config, cargar_config
from ui import inject_css
from autosave import autosave_section
from autosave import (
    build_usuario_config_from_state,
    build_producto_config_from_state,
    build_investigacion_config_from_state,
    build_system_config_from_state,
)

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Usuarios Sintéticos",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos (CSS global)
inject_css("assets/moeve.css")

# Helpers para query params (mantener compatibilidad)
def _get_query_params():
    try:
        # Streamlit moderno
        return st.query_params
    except Exception:
        return st.experimental_get_query_params()

def _get_current_section(default: str = "producto") -> str:
    params = _get_query_params()
    if isinstance(params, dict):
        raw = params.get("section", default)
        if isinstance(raw, list):
            raw = raw[0] if raw else default
        section = str(raw)
    else:
        section = str(getattr(params, "get", lambda _k, _d=None: default)("section", default))

    allowed = {"usuarios", "producto", "investigacion", "resultados", "config"}
    return section if section in allowed else default

def _set_current_section(section: str):
    st.session_state["section"] = section
    try:
        st.query_params["section"] = section
    except Exception:
        st.experimental_set_query_params(section=section)

def _nav_button(label: str, section: str, active: str):
    is_active = section == active
    # Primary para resaltar la sección activa
    clicked = st.sidebar.button(
        label,
        use_container_width=True,
        type="primary" if is_active else "secondary",
        key=f"nav_{section}",
    )
    if clicked and section != active:
        # Autosave the page we are leaving
        autosave_section(active)
        _set_current_section(section)
        st.rerun()

def _nav_button_disabled(label: str, reason: str = ""):
    st.sidebar.button(
        label,
        use_container_width=True,
        disabled=True,
        help=reason or None,
        key=f"nav_disabled_{label}",
    )

@st.cache_data(ttl=5)
def _get_statuses():
    backend = verificar_backend() or {"status": "disconnected"}
    # Detectar proveedor desde config del sistema (si existe)
    system_cfg = st.session_state.get("system_config")
    if not isinstance(system_cfg, dict):
        system_cfg = cargar_config("system") if existe_config("system") else {}

    llm_provider = str((system_cfg or {}).get("llm_provider") or "anythingllm").strip().lower()
    if llm_provider == "anythingllm":
        payload = {
            "llm_provider": "anythingllm",
            "anythingllm_base_url": (system_cfg or {}).get("anythingllm_base_url"),
            "anythingllm_api_key": (system_cfg or {}).get("anythingllm_api_key"),
            "anythingllm_workspace_slug": (system_cfg or {}).get("anythingllm_workspace_slug"),
            "anythingllm_mode": (system_cfg or {}).get("anythingllm_mode") or "chat",
        }
        llm = verificar_llm(payload) or {"status": "disconnected"}
    else:
        llm = verificar_ollama() or {"status": "disconnected"}
    return backend, llm

@st.cache_data(ttl=5)
def _get_latest_result_safe():
    try:
        return obtener_resultados_latest()
    except Exception:
        return None

def _is_complete_usuario(cfg: dict) -> bool:
    if not isinstance(cfg, dict):
        return False
    mode = cfg.get("mode")
    if mode == "single":
        single = cfg.get("single") if isinstance(cfg.get("single"), dict) else {}
        return all(isinstance(single.get(k), str) and single.get(k).strip() for k in ["arquetipo", "comportamiento", "necesidades", "barreras"])
    if mode == "population":
        pop = cfg.get("population") if isinstance(cfg.get("population"), dict) else {}
        n = pop.get("n")
        try:
            return int(n) >= 1
        except Exception:
            return False
    # Legacy (plano)
    return all(isinstance(cfg.get(k), str) and cfg.get(k).strip() for k in ["arquetipo", "comportamiento", "necesidades", "barreras"])

def _is_complete_producto(cfg: dict) -> bool:
    if not isinstance(cfg, dict):
        return False
    # Consideramos completo si hay una descripción canónica (ficha o input).
    desc = cfg.get("descripcion")
    if isinstance(desc, str) and desc.strip():
        return True
    # Compat/fallback: si aún no se construyó `descripcion` pero hay input, también vale.
    inp = cfg.get("descripcion_input")
    return isinstance(inp, str) and inp.strip() != ""

def _is_complete_investigacion(cfg: dict) -> bool:
    return isinstance(cfg, dict) and isinstance(cfg.get("descripcion"), str) and cfg.get("descripcion").strip() != ""

def _ensure_results_loaded():
    if st.session_state.get("resultados_investigacion"):
        return True
    latest = _get_latest_result_safe()
    if isinstance(latest, dict) and latest:
        st.session_state["resultados_investigacion"] = latest
        return True
    return False

def _run_investigacion_from_sidebar(current_section: str, run_slot):
    # 0) Autosave what user is editing right now (best effort)
    autosave_section(current_section)

    # 1) Build configs from current state (no need for per-page "Guardar")
    usuario_cfg = build_usuario_config_from_state()
    producto_cfg = build_producto_config_from_state()
    investigacion_cfg = build_investigacion_config_from_state()
    system_cfg = build_system_config_from_state()

    def _has_producto_data(cfg: dict) -> bool:
        if not isinstance(cfg, dict):
            return False
        for k in [
            "nombre_producto",
            "descripcion_input",
            "problema_a_resolver",
            "propuesta_valor",
            "funcionalidades_clave",
            "fuentes_a_ingestar",
            "observaciones",
            "riesgos",
            "dependencias",
        ]:
            v = cfg.get(k)
            if isinstance(v, str) and v.strip():
                return True
        return False

    # 1.5) Asegurar ficha de producto (si hay prompt configurado)
    try:
        if isinstance(system_cfg, dict) and system_cfg.get("prompt_ficha_producto") and _has_producto_data(producto_cfg):
            ficha_actual = (producto_cfg or {}).get("ficha_producto")
            if not isinstance(ficha_actual, str) or not ficha_actual.strip():
                ficha = generar_ficha_producto(producto_cfg, system_cfg)
                if isinstance(ficha, str) and ficha.strip():
                    producto_cfg["ficha_producto"] = ficha
                    producto_cfg["descripcion"] = ficha
    except Exception:
        # Si falla, continuamos con la descripción existente (fallback)
        pass

    # 2) Validate
    missing = []
    if not _is_complete_producto(producto_cfg):
        missing.append("Producto")
    if not _is_complete_investigacion(investigacion_cfg):
        missing.append("Investigación")
    if not _is_complete_usuario(usuario_cfg):
        missing.append("Usuario sintético")

    if missing:
        # Mensaje específico para producto (pedido)
        if "Producto" in missing:
            st.sidebar.error("Falta datos de producto.")
        else:
            st.sidebar.error(f"Completa: {', '.join(missing)}.")
        return

    with st.spinner("🔄 Ejecutando investigación..."):
        # 3) Persist local always (avoid stale configs)
        from utils import guardar_config
        guardar_config("usuario", usuario_cfg)
        # Guardar campos del producto y ficha en archivos separados
        producto_fields = dict(producto_cfg or {})
        ficha_val = str(producto_fields.pop("ficha_producto", "") or "").strip()
        # `producto_fields` debe guardar los inputs; no la ficha
        if isinstance(producto_fields.get("descripcion_input"), str):
            producto_fields["descripcion"] = str(producto_fields.get("descripcion_input") or "").strip()
        guardar_config("producto", producto_fields)
        existing_ficha = cargar_config("producto_ficha") if existe_config("producto_ficha") else {}
        existing_ficha = existing_ficha if isinstance(existing_ficha, dict) else {}
        merged = dict(existing_ficha)
        merged["ficha_producto"] = ficha_val
        merged.setdefault("generated_at", None)
        merged.setdefault("fields_hash", None)
        guardar_config("producto_ficha", merged)
        guardar_config("investigacion", investigacion_cfg)
        if system_cfg:
            guardar_config("system", system_cfg)

        # 4) Sync backend (best effort)
        r = enviar_usuario(usuario_cfg)
        if r:
            st.session_state["usuario_config_synced_backend"] = True
        r = enviar_producto(producto_cfg)
        if r:
            st.session_state["producto_config_synced_backend"] = True
        r = enviar_investigacion(investigacion_cfg)
        if r:
            st.session_state["investigacion_config_synced_backend"] = True

        # 5) Keep session consistent
        st.session_state["usuario_config"] = usuario_cfg
        st.session_state["producto_config"] = producto_cfg
        st.session_state["investigacion_config"] = investigacion_cfg
        if system_cfg:
            st.session_state["system_config"] = system_cfg

        # 6) Run (stream progress if available)
        status_box = run_slot

        def _short(text: str, max_len: int = 64) -> str:
            t = str(text or "").strip().replace("\n", " ")
            if len(t) <= max_len:
                return t
            return t[: max_len - 1].rstrip() + "…"

        # Single-line human status + animated progress bar
        current_line: str = ""
        last_user_i: int | None = None
        last_user_n: int | None = None
        progress_step: int | None = None
        progress_total: int | None = None

        def _set_run_ui(line: str, progress: float | None, running: bool = True):
            cls = "run-panel is-running" if running else "run-panel"
            safe_line = f"<div class='run-line'>{_short(line, 80)}</div>" if line else ""
            bar = ""
            if progress is not None:
                pct = max(0.0, min(1.0, float(progress)))
                bar = (
                    "<div class='run-bar'>"
                    f"<div class='run-bar-fill' style='width:{pct*100:.1f}%'></div>"
                    "</div>"
                )
            status_box.markdown(
                f"<div class='{cls}'>" + safe_line + bar + "</div>",
                unsafe_allow_html=True,
            )

        def _set_line(line: str):
            nonlocal current_line
            if not line:
                return
            current_line = line

        def _progress_for(step: int | None, total: int | None) -> float | None:
            if step is None or total is None:
                return None
            try:
                t = int(total)
                s = int(step)
            except Exception:
                return None
            if t <= 0:
                return None
            s = max(0, min(s, t))
            return float(s) / float(t)

        used_stream = False
        final_result = None

        try:
            for ev in iniciar_investigacion_stream(system_cfg or st.session_state.get("system_config")):
                used_stream = True
                if not isinstance(ev, dict):
                    continue
                if ev.get("event") == "error":
                    _set_line("Error")
                    _set_run_ui(current_line, None, running=False)
                    st.sidebar.error(f"❌ {ev.get('message') or 'Error'}")
                    return
                if ev.get("event") == "done":
                    final_result = ev.get("result")
                    break

                # Single-line dynamic status (prefer i/n)
                i = ev.get("i")
                n = ev.get("n")
                step_type = ev.get("step_type")
                event = ev.get("event")

                if i is not None and n is not None:
                    try:
                        i_i = int(i)
                        n_i = int(n)
                    except Exception:
                        i_i, n_i = None, None
                else:
                    i_i, n_i = None, None

                # Map backend events -> 3 clear phases + smooth progress (2 steps per user + analysis + done)
                if event in {"start", "planning", "plan_saved", "planning_done"}:
                    _set_line("Preparando investigación")
                    # Mostrar avance desde el primer evento (sin N aún)
                    if progress_total is None:
                        progress_total = 10
                    progress_step = 1
                elif event in {"respondent_start", "profile_start", "profile_done", "step_start", "step_done", "respondent_done"}:
                    if i_i and n_i:
                        last_user_i, last_user_n = i_i, n_i
                        _set_line(f"Consulta usuario {i_i}/{n_i}")
                        progress_total = (2 * n_i) + 2
                        if event == "profile_done":
                            progress_step = (2 * (i_i - 1)) + 1
                        elif event == "respondent_done":
                            progress_step = (2 * (i_i - 1)) + 2
                        elif progress_step is None:
                            progress_step = max(0, min((2 * (i_i - 1)) + 1, progress_total))
                elif event in {"synthesis_start", "synthesis_done"}:
                    _set_line("Generando análisis")
                    if last_user_n:
                        progress_total = (2 * int(last_user_n)) + 2
                        progress_step = (2 * int(last_user_n)) + 1
                else:
                    # Fallback: show short message if provided
                    msg = ev.get("message")
                    if isinstance(msg, str) and msg.strip():
                        _set_line(msg.strip())

                prog = _progress_for(progress_step, progress_total)
                _set_run_ui(current_line, prog, running=True)
        except Exception:
            used_stream = False

        if used_stream and isinstance(final_result, dict):
            _set_line("Completado")
            if last_user_n:
                progress_total = (2 * int(last_user_n)) + 2
                progress_step = progress_total
            prog = _progress_for(progress_step, progress_total)
            _set_run_ui(current_line, prog, running=False)
            st.session_state["resultados_investigacion"] = final_result
            st.session_state["section"] = "resultados"
            try:
                st.query_params["section"] = "resultados"
            except Exception:
                st.experimental_set_query_params(section="resultados")
            st.rerun()

        # Fallback: endpoint stream no disponible o falló -> modo legacy
        current_line = "Preparando investigación"
        _set_run_ui(current_line, 0.1, running=True)
        result = iniciar_investigacion(system_cfg or st.session_state.get("system_config"))
        if result and result.get("status") == "success":
            current_line = "Completado"
            _set_run_ui(current_line, 1.0, running=False)
            st.session_state["resultados_investigacion"] = result.get("resultados", {})
            st.session_state["section"] = "resultados"
            try:
                st.query_params["section"] = "resultados"
            except Exception:
                st.experimental_set_query_params(section="resultados")
            st.rerun()
        else:
            current_line = "Error"
            _set_run_ui(current_line, None, running=False)
            msg = (result or {}).get("detail") or "No se pudo iniciar la investigación."
            st.sidebar.error(f"❌ {msg}")

# Sidebar - Navegación
st.sidebar.title("🧭 Navegación")
st.sidebar.markdown("---")

# Sección actual (query param manda; permite navegación por links)
param_section = _get_current_section()
if st.session_state.get("section") != param_section:
    st.session_state["section"] = param_section
section_key = param_section

# Grupo principal
st.sidebar.markdown('<div class="nav-group-title">SECCIONES</div>', unsafe_allow_html=True)
_nav_button("📦 Producto", "producto", section_key)
_nav_button("🔎 Investigación", "investigacion", section_key)
_nav_button("👥 Usuario sintético", "usuarios", section_key)
has_results = _ensure_results_loaded()
if has_results:
    _nav_button("📊 Resultados", "resultados", section_key)
else:
    _nav_button_disabled("📊 Resultados", reason="Aún no hay resultados. Ejecuta una investigación para habilitar esta sección.")

st.sidebar.markdown("---")

# Acción global
st.sidebar.markdown('<div class="nav-group-title">ACCIÓN</div>', unsafe_allow_html=True)
clicked_run = st.sidebar.button("🚀 Iniciar investigación", type="primary", use_container_width=True)

# Reservar siempre el hueco (para que AJUSTES no "salte" cuando aparece el progreso)
# Debe ir DEBAJO del botón.
run_slot = st.sidebar.empty()
run_slot.markdown(
    "<div class='run-panel is-idle'>"
    "<div class='run-line'>&nbsp;</div>"
    "<div class='run-bar'><div class='run-bar-fill' style='width:0%'></div></div>"
    "</div>",
    unsafe_allow_html=True,
)

if clicked_run:
    _run_investigacion_from_sidebar(section_key, run_slot)

st.sidebar.markdown("---")

# AJUSTES (no pinned; estable por el hueco reservado del progreso)
st.sidebar.markdown('<div class="nav-group-title">AJUSTES</div>', unsafe_allow_html=True)
_nav_button("⚙️ Configuración", "config", section_key)

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
elif section_key == "config":
    render_config()

# Footer con estados (sticky)
backend_status, llm_status = _get_statuses()
backend_ok = backend_status.get("status") == "connected"
llm_ok = llm_status.get("status") == "connected"
llm_model = (
    llm_status.get("model")
    or llm_status.get("provider")
    or llm_status.get("base_url")
    or "N/A"
)

backend_state = "ON" if backend_ok else "OFF"

llm_state = "ON" if llm_ok else "OFF"

backend_pill_bg = "rgba(46, 204, 113, 0.18)" if backend_ok else "rgba(231, 76, 60, 0.16)"
backend_pill_border = "rgba(46, 204, 113, 0.35)" if backend_ok else "rgba(231, 76, 60, 0.32)"
backend_pill_text = "rgba(22, 110, 62, 0.95)" if backend_ok else "rgba(140, 32, 24, 0.95)"

llm_pill_bg = "rgba(46, 204, 113, 0.18)" if llm_ok else "rgba(231, 76, 60, 0.16)"
llm_pill_border = "rgba(46, 204, 113, 0.35)" if llm_ok else "rgba(231, 76, 60, 0.32)"
llm_pill_text = "rgba(22, 110, 62, 0.95)" if llm_ok else "rgba(140, 32, 24, 0.95)"

st.sidebar.markdown(
    f"""
    <div class="sidebar-footer">
      <div style="display:flex;flex-direction:row;flex-wrap:nowrap;align-items:center;justify-content:space-between;gap:12px;padding:0.65rem 0.75rem;margin:0.35rem 0;border-radius:12px;background:rgba(52, 152, 219, 0.08);border:1px solid rgba(52, 152, 219, 0.18);color:rgba(30,30,30,0.92);">
        <span style="font-size:0.95rem;font-weight:600;white-space:nowrap;color:rgba(30,30,30,0.92);">Backend</span>
        <span style="display:inline-flex;align-items:center;justify-content:center;padding:0.22rem 0.55rem;border-radius:999px;font-size:0.78rem;font-weight:700;letter-spacing:0.02em;white-space:nowrap;background:{backend_pill_bg};border:1px solid {backend_pill_border};color:{backend_pill_text};">{backend_state}</span>
      </div>

      <div title="{llm_model}" style="display:flex;flex-direction:row;flex-wrap:nowrap;align-items:center;justify-content:space-between;gap:12px;padding:0.65rem 0.75rem;margin:0.35rem 0;border-radius:12px;background:rgba(52, 152, 219, 0.08);border:1px solid rgba(52, 152, 219, 0.18);color:rgba(30,30,30,0.92);">
        <span style="font-size:0.95rem;font-weight:600;white-space:nowrap;color:rgba(30,30,30,0.92);">Modelo LLM</span>
        <span style="display:inline-flex;align-items:center;justify-content:center;padding:0.22rem 0.55rem;border-radius:999px;font-size:0.78rem;font-weight:700;letter-spacing:0.02em;white-space:nowrap;background:{llm_pill_bg};border:1px solid {llm_pill_border};color:{llm_pill_text};">{llm_state}</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)