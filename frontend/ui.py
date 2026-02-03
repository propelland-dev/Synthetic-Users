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
    st.markdown(f"<style>\n{css}\n</style>", unsafe_allow_html=True)

