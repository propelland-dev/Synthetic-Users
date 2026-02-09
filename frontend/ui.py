from __future__ import annotations

from pathlib import Path

import streamlit as st


def inject_css(relative_path: str) -> None:
    """
    Inject a CSS file (relative to the `frontend/` directory) into Streamlit.

    Example:
        inject_css("assets/moeve.css")
    """
    css_path = Path(__file__).parent / relative_path
    css = css_path.read_text(encoding="utf-8")
    # Agregar timestamp para evitar cache
    import time
    timestamp = int(time.time())
    st.markdown(f"<style data-timestamp='{timestamp}'>\n{css}\n</style>", unsafe_allow_html=True)


# def render_moeve_header() -> None:
#     """
#     Renderiza el header principal de Moeve según el diseño Figma.
#     """
#     st.markdown("""
#     <div class="moeve-main-header">
#         <div class="moeve-brand">
#             <h1>moeve</h1>
#             <p class="subtitle">Sistema de usuarios sintéticos</p>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

