import html as html_module
from datetime import datetime

import streamlit as st

from app.components.toast_loader import toast_loader
from src.health import get_last_live_status, pending_status, refresh_live_status


_STATUS_ACCENT = {
    "ready":     ("var(--secondary,#4ade80)",   "var(--secondary-container,#143d22)", "var(--card-pass-border,#166534)"),
    "attention": ("var(--warning,#fbbf24)",     "var(--warning-container,#3d2a07)",   "var(--card-warn-border,#854d0e)"),
    "error":     ("var(--error,#f87171)",       "var(--error-container,#5c1818)",     "var(--card-fail-border,#991b1b)"),
}

_CSS = """
<style>
.conn-grid {
  display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 1.25rem;
}
.conn-card {
  flex: 1 1 160px; min-width: 0;
  background: var(--md-surface-container,#1a2330);
  border: 1px solid var(--outline-variant,#26333f);
  border-radius: var(--shape-2xl,28px);
  padding: 18px 20px; position: relative; overflow: hidden;
  transition: transform 0.25s cubic-bezier(0.34,1.56,0.64,1),
              box-shadow 0.25s cubic-bezier(0.2,0,0,1);
}
.conn-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 32px rgba(0,0,0,0.4);
}
.conn-card .conn-label {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.09em; color: var(--muted,#92a1b5); margin-bottom: 10px;
}
.conn-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: var(--shape-full,999px);
  font-size: 12px; font-weight: 700; margin-bottom: 8px;
  border: 1px solid;
}
.conn-badge::before {
  content: ""; width: 7px; height: 7px; border-radius: 50%;
  background: currentColor;
}
.conn-detail {
  font-size: 12px; color: var(--muted,#92a1b5); font-family: monospace;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;
}
</style>
"""


def load_live_status() -> dict:
    """Return the stored result of the last check. Never contacts any service.

    ``checked_at`` is ``None`` and the cards show "Not checked" until the refresh
    button has been used at least once.
    """
    last = get_last_live_status()
    if last is not None:
        return last
    return {"data": pending_status(), "checked_at": None, "config_changed": False}


def render_connection_cards() -> None:
    live = load_live_status()
    statuses = live["data"]
    cards_html = ""
    for key, item in statuses.items():
        is_ready = item["status"] == "ready"
        state = "ready" if is_ready else ("error" if item["status"] == "error" else "attention")
        accent, bg, border = _STATUS_ACCENT.get(state, _STATUS_ACCENT["attention"])
        status_label = item.get("badge") or ("Ready" if is_ready else item["status"].title())
        status_label = html_module.escape(status_label)
        label  = html_module.escape(item["label"])
        detail = html_module.escape(item["detail"])
        tooltip = html_module.escape(item.get("info") or item["detail"], quote=True)
        cards_html += (
            f'<div class="conn-card" data-qa-tip="{tooltip}" style="border-left:3px solid {accent};">'
            f'<div class="conn-label">{label}</div>'
            f'<div class="conn-badge" style="color:{accent};background:{bg};border-color:{border}50;">'
            f'{status_label}</div>'
            f'<div class="conn-detail">{detail}</div></div>'
        )
    st.markdown(
        _CSS + f'<div class="conn-grid">{cards_html}</div>',
        unsafe_allow_html=True,
    )
    render_recheck_control(live, key="home_recheck_connections")


def _last_checked_caption(live: dict) -> str:
    checked_at = live.get("checked_at")
    if checked_at is None:
        return "Not checked yet. Use the refresh button to verify the connections."
    when = datetime.fromtimestamp(checked_at)
    stamp = when.strftime("%d %b %Y, %H:%M:%S")
    if live.get("config_changed"):
        return f"Last checked {stamp}. Configuration has changed since - refresh to re-verify."
    return f"Last checked {stamp}. Use the refresh button to check again."


def render_recheck_control(live: dict, *, key: str) -> None:
    """Show when the services were last checked and let the user re-run the checks."""
    caption_col, button_col = st.columns([4, 1], vertical_alignment="center")
    caption_col.caption(_last_checked_caption(live))
    if button_col.button(
        "Recheck",
        icon=":material/refresh:",
        key=key,
        type="secondary",
        help="Check connections now",
    ):
        with toast_loader(
            "Connection check — checking service connections...",
            done="Connection check — status updated.",
        ):
            refresh_live_status()
        st.rerun()
