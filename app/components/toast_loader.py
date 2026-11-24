from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Iterator

import streamlit as st
import streamlit.components.v1 as components

from app.state.background_tasks import record_notification

_PENDING_KEY = "_toast_loader_pending_dismiss"


def _show_toast(message: str, icon: str, *, persistent: bool = False) -> None:
    if persistent:
        try:
            st.toast(message, icon=icon, duration="infinite")
            return
        except TypeError:
            pass
    st.toast(message, icon=icon)


def _dismiss_script(messages: list[str]) -> None:
    """Close the toasts showing ``messages`` in the browser.

    Streamlit cannot remove or update a toast that was shown with an infinite
    duration, so the close button is clicked from the page instead. The script keeps
    retrying for a few seconds because the toast may not be mounted yet when a fast
    task finishes.
    """
    components.html(
        f"""
<script>
(function () {{
  const doc = window.parent.document;
  const wanted = new Set({json.dumps(messages)});
  let tries = 0;
  const sweep = () => {{
    doc.querySelectorAll('[data-testid="stToast"]').forEach((toast) => {{
      const text = toast.textContent || "";
      for (const message of wanted) {{
        if (text.includes(message)) {{
          const close = toast.querySelector('button[aria-label="Close"]');
          if (close) close.click();
          wanted.delete(message);
          break;
        }}
      }}
    }});
    if (wanted.size === 0 || ++tries > 50) window.clearInterval(timer);
  }};
  const timer = window.setInterval(sweep, 100);
  sweep();
}})();
</script>
        """,
        height=0,
        width=0,
    )


def _dismiss_loading_toast(message: str) -> None:
    _dismiss_script([message])
    # The caller often reruns the script right away, which can discard the script above
    # before it runs, so repeat it on the next run (see flush_pending_dismissals).
    pending = st.session_state.setdefault(_PENDING_KEY, [])
    if message not in pending:
        pending.append(message)


def flush_pending_dismissals() -> None:
    """Close loading toasts left behind by a run that ended in ``st.rerun()``.

    Call once per script run, before any new toast is shown.
    """
    pending = st.session_state.pop(_PENDING_KEY, None)
    if pending:
        _dismiss_script(list(pending))


@contextmanager
def toast_loader(message: str, *, done: str | None = None) -> Iterator[None]:
    """Show a progress message as a toast instead of an inline st.spinner.

    The toast stays visible while the wrapped block runs and is closed as soon as it
    finishes, followed by a short-lived toast with the outcome. The outcome is also
    saved to the Background Tasks bell dropdown.
    """
    title = message.rstrip(".…— ").split(" — ")[0].strip() or message
    started_at = datetime.now(UTC).isoformat()
    _show_toast(message, "⏳", persistent=True)
    try:
        yield
    except Exception as exc:
        _dismiss_loading_toast(message)
        st.toast("Something went wrong.", icon="⚠️")
        record_notification(
            title,
            "Failed. Review the error and try again.",
            status="failed",
            error=str(exc) or exc.__class__.__name__,
            started_at=started_at,
        )
        raise
    _dismiss_loading_toast(message)
    st.toast(done or "Done.", icon="✅")
    record_notification(title, done or "Done.", started_at=started_at)
