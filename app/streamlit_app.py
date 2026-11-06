import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from venv_bootstrap import ensure_project_venv

ensure_project_venv(ROOT)

import streamlit as st

st.set_page_config(
    page_title="ETL QA Accelerator",
    page_icon=str(ROOT / "assets" / "favicon.svg"),
    layout="wide",
    initial_sidebar_state="expanded",
)

_WATCHED_DIRS = (ROOT / "src", ROOT / "app")
_THIS_MODULE = __name__


def _source_fingerprint() -> tuple[int, float]:
    """Cheap change detector across the project's Python sources."""
    count = 0
    newest = 0.0
    for directory in _WATCHED_DIRS:
        for path in directory.rglob("*.py"):
            try:
                newest = max(newest, path.stat().st_mtime)
            except OSError:
                continue
            count += 1
    return count, newest


def _purge_project_modules() -> None:
    """Drop cached project modules so the next import picks up edited source.

    Streamlit reruns the entrypoint but keeps `sys.modules`, so editing a module
    that the entrypoint does not re-import leaves the old code running.
    """
    for name in list(sys.modules):
        if name == _THIS_MODULE:
            continue
        root = name.split(".")[0]
        if root in {"src", "app"}:
            del sys.modules[name]


_fingerprint = _source_fingerprint()
if st.session_state.get("_source_fingerprint") != _fingerprint:
    st.session_state["_source_fingerprint"] = _fingerprint
    _purge_project_modules()
    st.session_state.pop("qa_service", None)

from app.components.run_log import install_log_capture, render_log_button
from app.components.background_tasks import poll as poll_background_tasks
from app.components.background_tasks import render as render_background_tasks
from app.components.sidebar import render_sidebar
from app.components.theme import apply_theme
from app.state.session import get_service, init_session
from app.views import PAGES

install_log_capture()

apply_theme()
init_session()
with st.spinner("Starting QA workspace..."):
    get_service()

with st.sidebar:
    page = render_sidebar()
    render_log_button(key_prefix="sidebar_log")

poll_background_tasks()
render_background_tasks()
PAGES[page]()
