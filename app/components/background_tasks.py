from __future__ import annotations

from datetime import datetime
import html
import json

import streamlit as st
import streamlit.components.v1 as components

from app.state.background_tasks import (
    ICON_BY_KIND,
    BackgroundTask,
    active_task_count,
    clear_completed_tasks,
    dismiss_task,
    get_tasks,
    init_background_task_state,
    retry_task,
    sync_qa_generation_task,
    task_summary,
    tick_demo_task_progress,
    toggle_task_expanded,
)
from app.state.session import poll_qa_generation_job


def _format_timestamp(value: str) -> str:
    if not value:
        return "Just now"
    try:
        dt = datetime.fromisoformat(value).astimezone()
        return dt.strftime("%b %d · %H:%M")
    except (TypeError, ValueError):
        return "Unknown"


def _progress_bar(task: BackgroundTask) -> str:
    pct = max(0, min(100, int(round(task.progress))))
    status = task.status
    if status == "completed":
        return (
            f'<div class="bg-task-progress track completed" role="progressbar" '
            f'aria-valuenow="100" aria-valuemin="0" aria-valuemax="100">'
            f'<div class="bg-task-progress-fill" style="width:100%;background:var(--secondary)"></div>'
            f"</div>"
        )
    if status == "failed":
        return (
            f'<div class="bg-task-progress track failed" role="progressbar" '
            f'aria-valuenow="{pct}" aria-valuemin="0" aria-valuemax="100">'
            f'<div class="bg-task-progress-fill" style="width:{pct}%;background:var(--error)"></div>'
            f"</div>"
        )
    if status == "queued":
        return (
            '<div class="bg-task-progress track queued" role="progressbar" '
            'aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">'
            '<div class="bg-task-progress-fill" style="width:0%;background:var(--outline)"></div>'
            "</div>"
        )
    indeterminate = task.indeterminate or (status == "running" and pct <= 0)
    if indeterminate:
        return (
            '<div class="bg-task-progress track running indeterminate" role="progressbar" '
            'aria-busy="true" aria-valuemin="0" aria-valuemax="100">'
            '<div class="bg-task-progress-fill indeterminate-bar" style="background:var(--primary)"></div>'
            "</div>"
        )
    return (
        f'<div class="bg-task-progress track running" role="progressbar" '
        f'aria-valuenow="{pct}" aria-valuemin="0" aria-valuemax="100">'
        f'<div class="bg-task-progress-fill shimmer" style="width:{pct}%;background:var(--primary)"></div>'
        f"</div>"
    )


def _status_chip(status: str) -> str:
    labels = {
        "running": "Running",
        "completed": "Completed",
        "failed": "Failed",
        "queued": "Queued",
    }
    return (
        f'<span class="bg-task-status-chip {html.escape(status)}">'
        f"{html.escape(labels.get(status, status.title()))}</span>"
    )


def _task_icon(kind_value: str) -> str:
    from app.state.background_tasks import TaskKind

    try:
        kind = TaskKind(kind_value)
    except ValueError:
        kind = TaskKind.GENERIC
    symbol = ICON_BY_KIND.get(kind, "pending_actions")
    return f'<span class="material-symbols-rounded bg-task-leading-icon" aria-hidden="true">{symbol}</span>'


def _task_item_html(task: BackgroundTask, *, expanded: bool) -> str:
    pct = max(0, min(100, int(round(task.progress))))
    trailing = "—" if task.status == "queued" else f"{pct}%"
    if task.status == "completed":
        trailing = (
            '<span class="material-symbols-rounded bg-task-trail-check" aria-hidden="true">'
            "check_circle</span>"
        )
    elif task.status == "failed":
        trailing = (
            '<span class="material-symbols-rounded bg-task-trail-error" aria-hidden="true">'
            "error</span>"
        )

    expanded_block = ""
    if expanded:
        meta_lines = [
            f"<div><strong>Started</strong> {_format_timestamp(task.started_at)}</div>",
            f"<div><strong>Updated</strong> {_format_timestamp(task.updated_at)}</div>",
        ]
        if task.error:
            meta_lines.append(f'<div class="bg-task-error-text">{html.escape(task.error)}</div>')
        if task.metadata:
            meta_lines.append(
                f"<div><strong>Details</strong> {html.escape(json.dumps(task.metadata, default=str))}</div>"
            )
        expanded_block = f'<div class="bg-task-expanded">{"".join(meta_lines)}</div>'

    return (
        f'<article class="bg-task-item status-{html.escape(task.status)}" data-task-id="{html.escape(task.id)}">'
        f'<div class="bg-task-item-row">'
        f'<div class="bg-task-leading">{_task_icon(task.kind.value)}</div>'
        f'<div class="bg-task-body">'
        f'<div class="bg-task-title-row">'
        f'<h3 class="bg-task-name">{html.escape(task.name)}</h3>'
        f"{_status_chip(task.status)}"
        f"</div>"
        f'<p class="bg-task-desc">{html.escape(task.description)}</p>'
        f'<p class="bg-task-time">Updated {_format_timestamp(task.updated_at)}</p>'
        f"{_progress_bar(task)}"
        f"</div>"
        f'<div class="bg-task-trailing">{trailing}</div>'
        f"</div>"
        f"{expanded_block}"
        f"</article>"
    )


def _panel_html(
    tasks: list[BackgroundTask],
    *,
    expanded_id: str,
    summary: dict[str, int],
    running_label: str,
    include_items: bool = True,
) -> str:
    if not tasks:
        return (
            '<div class="bg-task-panel empty" role="dialog" aria-label="Background Tasks">'
            '<div class="bg-task-panel-inner">'
            '<header class="bg-task-header">'
            '<div class="bg-task-header-text">'
            '<div class="bg-task-title">Background Tasks</div>'
            '<button type="button" class="bg-task-html-close" aria-label="Close Background Tasks">'
            '<span class="material-symbols-rounded" aria-hidden="true">close</span>'
            "</button>"
            "<p>Monitor your ongoing operations</p>"
            "</div>"
            "</header>"
            '<div class="bg-task-empty">'
            '<span class="material-symbols-rounded bg-task-empty-icon" aria-hidden="true">task_alt</span>'
            "<h3>You're all caught up</h3>"
            "<p>There are no background tasks running right now.</p>"
            "</div>"
            "</div></div>"
        )

    items = "".join(_task_item_html(t, expanded=t.id == expanded_id) for t in tasks)
    task_list = f'<div class="bg-task-list" tabindex="0">{items}</div>' if include_items else ""
    return (
        f'<div class="bg-task-panel" role="dialog" aria-label="Background Tasks" aria-modal="true">'
        f'<div class="bg-task-panel-inner">'
        f'<header class="bg-task-header">'
        f'<div class="bg-task-header-text">'
        f'<div class="bg-task-title">Background Tasks</div>'
        f'<button type="button" class="bg-task-html-close" aria-label="Close Background Tasks">'
        f'<span class="material-symbols-rounded" aria-hidden="true">close</span>'
        f"</button>"
        f"<p>Monitor your ongoing operations</p>"
        f'<p class="bg-task-live">{html.escape(running_label)}</p>'
        f"</div>"
        f"</header>"
        f'<div class="bg-task-summary">'
        f'<span><i class="dot running"></i> Active <strong>{summary["running"] + summary["queued"]}</strong></span>'
        f'<span><i class="dot completed"></i> Completed <strong>{summary["completed"]}</strong></span>'
        f'<span><i class="dot failed"></i> Failed <strong>{summary["failed"]}</strong></span>'
        f"</div>"
        f'<div class="bg-task-divider"></div>'
        f"{task_list}"
        f"</div></div>"
    )


def _bind_panel_scripts() -> None:
    components.html(
        """
<script>
(function () {
  const doc = window.parent.document;
  if (doc.__bgTaskCenterBound) return;
  doc.__bgTaskCenterBound = true;

  const clickOutside = (event) => {
    const panel = doc.querySelector(".st-key-bg-task-panel .bg-task-panel");
    if (!panel) return;
    if (event.target.closest(".bg-task-html-close")) return;
    if (event.target.closest(".st-key-bg-task-center-root")) return;
    const closer = doc.querySelector(".st-key-bg_task_close_outside button");
    if (closer) closer.click();
  };

  const onKey = (event) => {
    if (event.key !== "Escape") return;
    const panel = doc.querySelector(".st-key-bg-task-panel .bg-task-panel");
    if (!panel) return;
    const closer = doc.querySelector(".st-key-bg_task_close_outside button");
    if (closer) closer.click();
  };

  doc.addEventListener("click", (event) => {
    const close = event.target.closest(".bg-task-html-close");
    if (!close) return;
    const closer = doc.querySelector(".st-key-bg_task_close_outside button");
    if (closer) closer.click();
  });

  doc.addEventListener("click", clickOutside, true);
  doc.addEventListener("keydown", onKey);
})();
</script>
        """,
        height=0,
        width=0,
    )


def _remove_legacy_progress_toast() -> None:
    components.html(
        """
<script>
(function () {
  const doc = window.parent.document;
  doc.querySelectorAll("#qa-progress-toast, .bg-progress-toast").forEach((node) => node.remove());
})();
</script>
        """,
        height=0,
        width=0,
    )


@st.fragment(run_every="1s")
def poll() -> None:
    poll_qa_generation_job()
    sync_qa_generation_task()
    tick_demo_task_progress()


def _should_live_refresh() -> bool:
    tasks = get_tasks()
    return bool(st.session_state.get("bg_task_panel_open")) or active_task_count(tasks) > 0


@st.fragment(run_every="1s")
def _render_live_panel() -> None:
    _render_center()


def render() -> None:
    init_background_task_state()
    sync_qa_generation_task()
    _remove_legacy_progress_toast()
    if _should_live_refresh():
        _render_live_panel()
    else:
        _render_center()


def _render_center() -> None:
    init_background_task_state()
    tasks = get_tasks()
    summary = task_summary(tasks)
    active = active_task_count(tasks)
    panel_open = bool(st.session_state.get("bg_task_panel_open"))
    expanded_id = st.session_state.get("bg_task_expanded_id") or ""

    running_label = (
        f"{active} task{'s' if active != 1 else ''} running"
        if active
        else "No active tasks"
    )

    root_class = "bg-task-center-root is-open" if panel_open else "bg-task-center-root"
    badge_pulse = " pulse" if summary["running"] > 0 else ""
    badge_html = ""
    if active > 0:
        badge_html = f'<span class="bg-task-badge{badge_pulse}" aria-label="{active} active tasks">{active}</span>'

    with st.container(key="bg-task-center-root"):
        st.markdown(
            f'<div class="{root_class}" aria-live="polite">{badge_html}</div>',
            unsafe_allow_html=True,
        )

        if st.button(
            " ",
            key="bg_task_bell",
            help="Background Tasks",
            type="secondary",
        ):
            st.session_state["bg_task_panel_open"] = not panel_open
            st.rerun()

        if st.button("close", key="bg_task_close_outside"):
            st.session_state["bg_task_panel_open"] = False
            st.rerun()

    if panel_open:
        with st.container(key="bg-task-panel"):
            if st.button(" ", key="bg_task_close_header", type="tertiary"):
                st.session_state["bg_task_panel_open"] = False
                st.rerun()
            st.markdown(
                _panel_html(
                    tasks,
                    expanded_id=expanded_id,
                    summary=summary,
                    running_label=running_label,
                    include_items=False,
                ),
                unsafe_allow_html=True,
            )
            with st.container(key="bg-task-list"):
                for task in tasks:
                    with st.container(key=f"bg-task-card-{task.id}"):
                        st.markdown(
                            _task_item_html(task, expanded=task.id == expanded_id),
                            unsafe_allow_html=True,
                        )
                        _render_task_actions([task])
            _render_panel_footer(summary)

    _bind_panel_scripts()


def _render_task_actions(tasks: list[BackgroundTask]) -> None:
    if not tasks:
        return
    for task in tasks:
        cols = st.columns([4, 1, 1, 1], gap="small")
        with cols[0]:
            if st.button(
                "Details",
                key=f"bg_task_expand_{task.id}",
                type="tertiary",
            ):
                toggle_task_expanded(task.id)
                st.rerun()
        with cols[1]:
            if task.status == "failed" and st.button(
                "Retry",
                key=f"bg_task_retry_{task.id}",
                type="secondary",
            ):
                retry_task(task.id)
                st.rerun()
        with cols[2]:
            if task.status == "completed" and st.button(
                "Dismiss",
                key=f"bg_task_dismiss_{task.id}",
                type="secondary",
            ):
                dismiss_task(task.id)
                st.rerun()
        with cols[3]:
            if task.status != "running":
                continue
            confirm_key = f"bg_task_confirm_cancel_{task.id}"
            if st.session_state.get(confirm_key):
                if st.button("Confirm", key=f"bg_task_confirm_{task.id}", type="primary"):
                    if task.source == "live" and task.id == "qa-pack-generation":
                        from app.state.session import clear_qa_generation_job

                        clear_qa_generation_job()
                    dismiss_task(task.id)
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
            elif st.button("Cancel", key=f"bg_task_cancel_{task.id}", type="secondary"):
                st.session_state[confirm_key] = True
                st.rerun()


def _render_panel_footer(summary: dict[str, int]) -> None:
    with st.container(key="bg-task-footer"):
        st.markdown('<div class="bg-task-footer-divider"></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if summary["completed"] and st.button(
                "Clear completed",
                key="bg_task_clear_completed",
                type="tertiary",
            ):
                clear_completed_tasks()
                st.rerun()
        with c3:
            if st.button("View all tasks", key="bg_task_view_all", type="primary"):
                st.session_state["bg_task_panel_open"] = False
                st.session_state["current_page"] = "Background Tasks"
                st.rerun()
