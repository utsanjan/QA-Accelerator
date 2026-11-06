"""Capture agent logs in-process so the UI can show progress and failures."""

from __future__ import annotations

import itertools
import logging
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime

import streamlit as st

MAX_RECORDS = 600
OWN_LOGGER_ROOTS = {"src", "app", "qa"}
_HANDLER_TAG = "qa_accelerator_log_buffer"

_LOCK = threading.Lock()
_SEQUENCE = itertools.count(1)
_RECORDS: deque["LogLine"] = deque(maxlen=MAX_RECORDS)


@dataclass(frozen=True)
class LogLine:
    seq: int
    created: float
    level: str
    name: str
    message: str

    def format(self) -> str:
        stamp = datetime.fromtimestamp(self.created).strftime("%H:%M:%S")
        short_name = self.name.split(".")[-1]
        return f"{stamp}  {self.level:<7} {short_name}: {self.message}"


def _is_relevant(record: logging.LogRecord) -> bool:
    if record.levelno >= logging.WARNING:
        return True
    return record.name.split(".")[0] in OWN_LOGGER_ROOTS


class _BufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if not _is_relevant(record):
            return
        try:
            text = self.format(record)
        except Exception:  # never let logging break a run
            return
        line = LogLine(
            seq=next(_SEQUENCE),
            created=record.created,
            level=record.levelname,
            name=record.name,
            message=text,
        )
        with _LOCK:
            _RECORDS.append(line)


def install_log_capture(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    # Match by name, not isinstance: a module reload creates a new class object,
    # which would otherwise leave stale handlers attached to the root logger.
    for existing in list(root.handlers):
        if getattr(existing, "name", None) == _HANDLER_TAG:
            root.removeHandler(existing)
    handler = _BufferHandler()
    handler.set_name(_HANDLER_TAG)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(logging.DEBUG)
    root.addHandler(handler)
    if root.level == logging.NOTSET or root.level > level:
        root.setLevel(level)
    # Third-party INFO chatter is filtered by _is_relevant, but keep HTTP clients quiet anyway.
    for noisy in ("httpx", "httpcore", "urllib3", "openai", "azure"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def log_event(message: str, *, level: int = logging.INFO) -> None:
    logging.getLogger("app.progress").log(level, message)


def current_cursor() -> int:
    with _LOCK:
        return _RECORDS[-1].seq if _RECORDS else 0


def records_since(cursor: int) -> list[LogLine]:
    with _LOCK:
        return [line for line in _RECORDS if line.seq > cursor]


def recent_records(limit: int = 120, *, errors_only: bool = False) -> list[LogLine]:
    with _LOCK:
        lines = list(_RECORDS)
    if errors_only:
        lines = [line for line in lines if line.level in {"WARNING", "ERROR", "CRITICAL"}]
    return lines[-limit:]


def clear_records() -> None:
    with _LOCK:
        _RECORDS.clear()


def as_text(lines: list[LogLine]) -> str:
    return "\n".join(line.format() for line in lines)


_POPOVER_CSS = """
<style>
div[data-testid="stPopoverBody"] {
    min-width: 520px !important;
    max-width: 640px !important;
}
div[data-testid="stPopoverBody"] pre {
    font-size: 11px !important;
    line-height: 1.5 !important;
    max-height: 340px !important;
}
</style>
"""


def render_log_button(*, key_prefix: str = "runlog", label: str = "Activity log") -> None:
    """Small info button that opens the captured log in a floating panel."""
    st.markdown(_POPOVER_CSS, unsafe_allow_html=True)

    error_count = len(recent_records(limit=MAX_RECORDS, errors_only=True))
    button_label = f"{label} ({error_count} issue{'s' if error_count != 1 else ''})" if error_count else label

    with st.popover(button_label, use_container_width=True):
        errors_only = st.toggle("Errors only", value=False, key=f"{key_prefix}_errors_only")
        lines = recent_records(limit=150, errors_only=errors_only)
        if lines:
            st.code(as_text(lines), language="log")
        else:
            st.caption("Nothing logged yet. Run a step and reopen this panel.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Refresh", use_container_width=True, key=f"{key_prefix}_refresh"):
                st.rerun()
        with col2:
            if st.button("Clear", use_container_width=True, key=f"{key_prefix}_clear"):
                clear_records()
                st.rerun()
