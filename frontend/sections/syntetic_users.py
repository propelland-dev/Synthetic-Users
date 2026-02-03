import streamlit as st
import sys
from pathlib import Path
import json

# Agregar el directorio padre al path para importar config
sys.path.append(str(Path(__file__).parent.parent))
from utils import cargar_config, existe_config

ARQUETIPOS_PATH = Path(__file__).parent.parent / "configs" / "arquetipos.json"

def _cargar_arquetipos():
    try:
        with open(ARQUETIPOS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [a for a in data if isinstance(a, dict) and a.get("nombre")]
        return []
    except Exception:
        return []

def render_usuarios_sinteticos():
    st.markdown('<div class="section-title">👥 Configuración de Usuario Sintético</div>', unsafe_allow_html=True)
    
    st.markdown(r"""
    Define el usuario sintético a partir de **3 dimensiones**: comportamiento, necesidades y barreras.
    
    Puedes trabajar en dos modos:
    - **Single**: un solo usuario sintético
    - **Población**: una mezcla de arquetipos con un tamaño total \(N\)
    """)
    
    # Cargar configuración guardada si existe (auto)
    config_cargada = cargar_config("usuario") if existe_config("usuario") else None

    # Arquetipos
    arquetipos = _cargar_arquetipos()
    arquetipos_por_nombre = {a["nombre"]: a for a in arquetipos}
    opciones_arquetipo = ["Personalizado"] + list(arquetipos_por_nombre.keys())

    # Compatibilidad: cargar config legacy o v2
    saved_mode = None
    if isinstance(config_cargada, dict) and config_cargada.get("mode") in {"single", "population"}:
        saved_mode = config_cargada.get("mode")
    elif isinstance(config_cargada, dict) and "arquetipo" in config_cargada:
        saved_mode = "single"

    if "usuario_mode" not in st.session_state:
        st.session_state["usuario_mode"] = saved_mode or "single"

    st.markdown("### Modo")
    mode_label = st.radio(
        "Selecciona el modo de configuración",
        options=["Single", "Población"],
        index=0 if st.session_state["usuario_mode"] == "single" else 1,
        horizontal=True,
        key="usuario_mode_radio",
        help="Single: un usuario. Población: defines N y una mezcla por arquetipo.",
    )
    usuario_mode = "population" if mode_label == "Población" else "single"
    st.session_state["usuario_mode"] = usuario_mode

    # -------------------------
    # MODO: SINGLE
    # -------------------------
    if usuario_mode == "single":
        # Determinar defaults desde config guardada (legacy o v2)
        if isinstance(config_cargada, dict) and config_cargada.get("mode") == "single":
            single_saved = config_cargada.get("single") if isinstance(config_cargada.get("single"), dict) else {}
        else:
            single_saved = config_cargada or {}

        arquetipo_guardado = (single_saved or {}).get("arquetipo") if single_saved else None
        if arquetipo_guardado in opciones_arquetipo:
            arquetipo_default = arquetipo_guardado
        else:
            arquetipo_default = "Personalizado"

        if "usuario_arquetipo" not in st.session_state:
            st.session_state["usuario_arquetipo"] = arquetipo_default
        if "usuario_arquetipo_prev" not in st.session_state:
            st.session_state["usuario_arquetipo_prev"] = st.session_state["usuario_arquetipo"]

        st.markdown("### Arquetipo")
        arquetipo = st.selectbox(
            "Selecciona un arquetipo",
            options=opciones_arquetipo,
            index=opciones_arquetipo.index(st.session_state["usuario_arquetipo"]) if st.session_state["usuario_arquetipo"] in opciones_arquetipo else 0,
            help="Si eliges un arquetipo, se rellenan automáticamente las 3 cajas. Con 'Personalizado' lo defines tú.",
            key="usuario_arquetipo",
        )

        # Inicialización de campos (solo una vez por sesión)
        if "usuario_comportamiento" not in st.session_state:
            if arquetipo != "Personalizado" and arquetipo in arquetipos_por_nombre:
                st.session_state["usuario_comportamiento"] = arquetipos_por_nombre[arquetipo].get("comportamiento", "")
                st.session_state["usuario_necesidades"] = arquetipos_por_nombre[arquetipo].get("necesidades", "")
                st.session_state["usuario_barreras"] = arquetipos_por_nombre[arquetipo].get("barreras", "")
            else:
                st.session_state["usuario_comportamiento"] = (single_saved or {}).get("comportamiento", "") if single_saved else ""
                st.session_state["usuario_necesidades"] = (single_saved or {}).get("necesidades", "") if single_saved else ""
                st.session_state["usuario_barreras"] = (single_saved or {}).get("barreras", "") if single_saved else ""

        # Si cambia el arquetipo, auto-rellenar o limpiar
        if st.session_state.get("usuario_arquetipo_prev") != arquetipo:
            if arquetipo == "Personalizado":
                st.session_state["usuario_comportamiento"] = ""
                st.session_state["usuario_necesidades"] = ""
                st.session_state["usuario_barreras"] = ""
            else:
                data = arquetipos_por_nombre.get(arquetipo, {})
                st.session_state["usuario_comportamiento"] = data.get("comportamiento", "")
                st.session_state["usuario_necesidades"] = data.get("necesidades", "")
                st.session_state["usuario_barreras"] = data.get("barreras", "")
            st.session_state["usuario_arquetipo_prev"] = arquetipo

        st.markdown("### Comportamiento")
        st.text_area(
            "Cómo se comporta",
            key="usuario_comportamiento",
            height=140,
            placeholder="Describe cómo interactúa con el asistente / cómo usa la IA...",
        )

        st.markdown("### Necesidades")
        st.text_area(
            "Qué necesita del asistente",
            key="usuario_necesidades",
            height=140,
            placeholder="Qué espera, qué le ayuda, qué tipo de respuestas necesita...",
        )

        st.markdown("### Barreras")
        st.text_area(
            "Barreras típicas de adopción",
            key="usuario_barreras",
            height=140,
            placeholder="Qué le frena, qué le hace desconfiar, qué haría que abandone...",
        )

        # Mantener config en sesión siempre actualizada (se persistirá al cambiar de página)
        st.session_state["usuario_config"] = {
            "mode": "single",
            "single": {
                "arquetipo": arquetipo,
                "comportamiento": st.session_state.get("usuario_comportamiento", "") or "",
                "necesidades": st.session_state.get("usuario_necesidades", "") or "",
                "barreras": st.session_state.get("usuario_barreras", "") or "",
            },
        }

        # Acciones
        st.markdown("---")
        if st.button("🔄 Resetear", use_container_width=True):
            st.session_state["usuario_config"] = None
            st.session_state.pop("usuario_config_synced_backend", None)
            for k in [
                "usuario_mode",
                "usuario_mode_radio",
                "usuario_arquetipo",
                "usuario_arquetipo_prev",
                "usuario_comportamiento",
                "usuario_necesidades",
                "usuario_barreras",
            ]:
                st.session_state.pop(k, None)
            st.rerun()

        return

    # -------------------------
    # MODO: POBLACIÓN
    # -------------------------
    if isinstance(config_cargada, dict) and config_cargada.get("mode") == "population":
        pop_saved = config_cargada.get("population") if isinstance(config_cargada.get("population"), dict) else {}
        mix_saved = pop_saved.get("mix") if isinstance(pop_saved.get("mix"), list) else []
    else:
        pop_saved = {}
        mix_saved = []

    st.markdown("### Población")
    n_default = int(pop_saved.get("n", 10)) if isinstance(pop_saved.get("n"), int) else 10
    n = st.number_input("Tamaño de la población (N)", min_value=1, max_value=200, value=n_default, step=1, key="usuario_population_n")

    if "usuario_population_rows" not in st.session_state:
        # Normalizar filas guardadas
        rows = []
        for item in mix_saved:
            if not isinstance(item, dict):
                continue
            rows.append({
                "arquetipo": str(item.get("arquetipo", "Personalizado")),
                "count": int(item.get("count", 0)) if str(item.get("count", "")).isdigit() else int(item.get("count", 0) or 0),
                "comportamiento": str(item.get("comportamiento", "")),
                "necesidades": str(item.get("necesidades", "")),
                "barreras": str(item.get("barreras", "")),
            })
        # Si no hay filas, arrancar con una por defecto
        if not rows:
            rows = [{"arquetipo": "Personalizado", "count": 0, "comportamiento": "", "necesidades": "", "barreras": ""}]
        st.session_state["usuario_population_rows"] = rows

    def _add_population_row():
        st.session_state["usuario_population_rows"].append({
            "arquetipo": "Personalizado",
            "count": 0,
            "comportamiento": "",
            "necesidades": "",
            "barreras": "",
        })

    def _remove_population_row(idx: int):
        rows = st.session_state.get("usuario_population_rows", [])
        if 0 <= idx < len(rows):
            rows.pop(idx)
            st.session_state["usuario_population_rows"] = rows

    st.markdown("### Mezcla por arquetipo")
    st.caption("Añade arquetipos y asigna cuántos respondientes pertenecen a cada uno. Si la suma es menor que N, el resto se completará como 'Personalizado'.")

    total = 0
    rows = st.session_state.get("usuario_population_rows", [])
    for idx, row in enumerate(rows):
        col_a, col_b, col_c = st.columns([3, 2, 1])
        with col_a:
            arq_key = f"pop_arq_{idx}"
            current_arq = row.get("arquetipo", "Personalizado")
            chosen = st.selectbox(
                f"Arquetipo #{idx+1}",
                options=opciones_arquetipo,
                index=opciones_arquetipo.index(current_arq) if current_arq in opciones_arquetipo else 0,
                key=arq_key,
            )
            row["arquetipo"] = chosen
            # Si es un arquetipo predefinido, rellenar dimensiones automáticamente
            if chosen != "Personalizado" and chosen in arquetipos_por_nombre:
                row["comportamiento"] = arquetipos_por_nombre[chosen].get("comportamiento", "")
                row["necesidades"] = arquetipos_por_nombre[chosen].get("necesidades", "")
                row["barreras"] = arquetipos_por_nombre[chosen].get("barreras", "")
        with col_b:
            cnt_key = f"pop_cnt_{idx}"
            value_cnt = int(row.get("count", 0) or 0)
            cnt = st.slider(
                f"Cantidad #{idx+1}",
                min_value=0,
                max_value=int(n),
                value=min(value_cnt, int(n)),
                key=cnt_key,
            )
            row["count"] = int(cnt)
        with col_c:
            if st.button("🗑️", key=f"pop_del_{idx}", help="Eliminar fila"):
                _remove_population_row(idx)
                st.rerun()

        # Si es personalizado, permitir editar dimensiones
        if row["arquetipo"] == "Personalizado":
            with st.expander(f"Dimensiones (Personalizado #{idx+1})", expanded=False):
                row["comportamiento"] = st.text_area("Comportamiento", value=row.get("comportamiento", ""), key=f"pop_comp_{idx}", height=90)
                row["necesidades"] = st.text_area("Necesidades", value=row.get("necesidades", ""), key=f"pop_nec_{idx}", height=90)
                row["barreras"] = st.text_area("Barreras", value=row.get("barreras", ""), key=f"pop_bar_{idx}", height=90)

        total += int(row.get("count", 0) or 0)

    st.session_state["usuario_population_rows"] = rows

    col_add, col_status = st.columns([1, 3])
    with col_add:
        if st.button("➕ Añadir arquetipo", use_container_width=True):
            _add_population_row()
            st.rerun()

    with col_status:
        remaining = int(n) - int(total)
        if remaining < 0:
            st.error(f"❌ Has asignado {total} pero N={n}. Reduce cantidades.")
        elif remaining == 0:
            st.success(f"✅ Mezcla completa: {total}/{n}")
        else:
            st.info(f"ℹ️ Asignados: {total}/{n}. Resto: {remaining} (se completará como 'Personalizado').")
    
    # Mantener config en sesión siempre actualizada (se persistirá al cambiar de página)
    mix_out = []
    for r in rows:
        if int(r.get("count", 0) or 0) <= 0:
            continue
        mix_out.append({
            "arquetipo": r.get("arquetipo", "Personalizado"),
            "count": int(r.get("count", 0) or 0),
            "comportamiento": r.get("comportamiento", ""),
            "necesidades": r.get("necesidades", ""),
            "barreras": r.get("barreras", ""),
        })
    st.session_state["usuario_config"] = {
        "mode": "population",
        "population": {"n": int(n), "mix": mix_out},
    }

    # Acciones
    st.markdown("---")
    if st.button("🔄 Resetear", use_container_width=True):
        st.session_state["usuario_config"] = None
        st.session_state.pop("usuario_config_synced_backend", None)
        for k in [
            "usuario_mode",
            "usuario_mode_radio",
            "usuario_population_n",
            "usuario_population_rows",
        ]:
            st.session_state.pop(k, None)
        st.rerun()
