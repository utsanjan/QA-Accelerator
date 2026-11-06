from __future__ import annotations

import html

import streamlit as st

from app.components.theme import page_header
from app.state.background_tasks import (
    clear_completed_tasks,
    dismiss_task,
    get_tasks,
    retry_task,
    task_summary,
)
from app.components.background_tasks import _progress_bar, _status_chip, _task_icon


def render() -> None:
    page_header(
        "Background Tasks",
        "Monitor long-running operations, retry failures, and review completed work.",
    )
    with st.container(key="background-tasks-page"):
        tasks = get_tasks(include_dismissed=False)
        summary = task_summary(tasks)

        cols = st.columns(4)
        cols[0].metric("Running", summary["running"])
        cols[1].metric("Queued", summary["queued"])
        cols[2].metric("Completed", summary["completed"])
        cols[3].metric("Failed", summary["failed"])

        if summary["completed"]:
            if st.button("Clear completed", type="secondary"):
                clear_completed_tasks()
                st.rerun()

        if not tasks:
            st.info("You're all caught up — no background tasks in this session.")
            return

        for task in tasks:
            with st.container(border=True):
                head = st.columns([1, 6, 2])
                with head[0]:
                    st.markdown(
                        f'<div class="bg-task-leading page">{_task_icon(task.kind.value)}</div>',
                        unsafe_allow_html=True,
                    )
                with head[1]:
                    st.markdown(
                        f'<span class="bg-task-page-title">{html.escape(task.name)}</span> {_status_chip(task.status)}',
                        unsafe_allow_html=True,
                    )
                    st.caption(task.description)
                    st.caption(f"Updated · {task.started_at[:19] if task.started_at else '—'}")
                with head[2]:
                    pct = int(round(task.progress))
                    st.markdown(f"**{pct}%**" if task.status not in ("failed",) else "Failed")

                st.markdown(_progress_bar(task), unsafe_allow_html=True)

                actions = st.columns(4)
                if task.status == "failed":
                    if actions[0].button("Retry", key=f"page_retry_{task.id}"):
                        retry_task(task.id)
                        st.rerun()
                if task.status == "completed":
                    if actions[1].button("Dismiss", key=f"page_dismiss_{task.id}"):
                        dismiss_task(task.id)
                        st.rerun()
                if task.error:
                    st.error(task.error)
