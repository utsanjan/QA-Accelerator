"""Helpers for the app-wide themed hover tooltip (the script lives in ``theme.apply_theme``).

Three ways to give something a tooltip:

* ``tip("text")`` returns a ``data-qa-tip`` attribute for hand-written HTML.
* ``register_tips({...})`` attaches text to Streamlit widgets by their ``key``.
* ``help=`` on a Streamlit widget also works; its text is shown in the same style.

Anything truncated with an ellipsis shows its full text automatically.
"""

from __future__ import annotations

import html
import json
import re

import streamlit as st


def tip(text: str) -> str:
    """Attribute string to drop inside an HTML tag, e.g. ``f'<div{tip("Full name")}>'``."""
    if not text:
        return ""
    return f' data-qa-tip="{html.escape(str(text), quote=True)}"'


def widget_class_key(key: str) -> str:
    """Streamlit turns a widget key into the ``st-key-...`` CSS class with this rule."""
    return re.sub(r"[^a-zA-Z0-9_-]", "-", key)


def register_tips(tips: dict[str, str]) -> None:
    """Attach tooltip text to Streamlit widgets/containers by key. Renders nothing visible."""
    payload = {widget_class_key(key): text for key, text in tips.items() if text}
    if not payload:
        return
    data = html.escape(json.dumps(payload), quote=True)
    st.markdown(f'<div class="qa-tip-registry" data-tips="{data}"></div>', unsafe_allow_html=True)
