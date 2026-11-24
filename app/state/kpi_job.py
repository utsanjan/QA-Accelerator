from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st

from app.state.background_tasks import (
    BackgroundTask,
    TaskKind,
    _estimate_qa_progress,
    upsert_task,
)

KPI_TASK_PREFIX = "kpi-normalization-"
_JOB_KEY = "kpi_normalization_job"
_EXECUTOR_KEY = "kpi_normalization_executor"
_TASK_NAME = "KPI SQL Agent"


def is_kpi_task(task_id: str) -> bool:
    return task_id.startswith(KPI_TASK_PREFIX)


def get_kpi_job() -> dict[str, Any] | None:
    return st.session_state.get(_JOB_KEY)


def kpi_job_running() -> bool:
    job = get_kpi_job()
    return bool(job and not job["future"].done())


def clear_kpi_job() -> None:
    st.session_state.pop(_JOB_KEY, None)


def start_kpi_normalization(
    service,
    path: Path,
    *,
    requirement_context: str,
    draft_id: str | None,
) -> Future:
    """Run KPI normalization on a worker thread so progress is visible in the task bell."""
    if kpi_job_running():
        raise RuntimeError("A KPI normalization is already running.")

    executor = st.session_state.get(_EXECUTOR_KEY)
    if executor is None:
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kpi-normalization")
        st.session_state[_EXECUTOR_KEY] = executor

    future = executor.submit(
        service.process_kpi_logic_document,
        path,
        requirement_context=requirement_context,
    )
    job = {
        "future": future,
        "task_id": f"{KPI_TASK_PREFIX}{uuid4().hex}",
        "source_name": path.name,
        "draft_id": draft_id or "",
        "started_at": datetime.now(UTC).isoformat(),
    }
    st.session_state[_JOB_KEY] = job
    _upsert(job, status="running", description=f"Parsing and normalizing {path.name}")
    return future


def _upsert(
    job: dict[str, Any],
    *,
    status: str,
    description: str,
    progress: float | None = None,
    error: str = "",
) -> None:
    if progress is None:
        progress = 100.0 if status in ("completed", "failed") else 0.0
    upsert_task(
        BackgroundTask(
            id=job["task_id"],
            name=_TASK_NAME,
            description=description,
            status=status,  # type: ignore[arg-type]
            progress=progress,
            kind=TaskKind.DATASET,
            started_at=job["started_at"],
            updated_at=datetime.now(UTC).isoformat(),
            error=error,
            source="live",
            metadata={"file": job["source_name"]},
        )
    )


def sync_kpi_normalization_task() -> bool:
    """Update the bell entry and collect the result. Returns True when a job just finished."""
    job = get_kpi_job()
    if not job:
        return False

    future = job["future"]
    if not future.done():
        _upsert(
            job,
            status="running",
            description=f"Parsing and normalizing {job['source_name']}",
            progress=_estimate_qa_progress(job["started_at"]),
        )
        return False

    if job.get("processed"):
        return False
    job["processed"] = True

    try:
        normalized = future.result()
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc) or exc.__class__.__name__
        _upsert(
            job,
            status="failed",
            description="Normalization failed. Review the error and retry.",
            error=job["error"],
        )
        st.toast("KPI SQL Agent failed. Open Background Tasks for details.", icon="⚠️")
        return True

    st.session_state["kpi_logic_normalized"] = normalized
    job["status"] = "complete"
    draft_id = job.get("draft_id")
    if draft_id:
        try:
            from app.state.session import get_service

            get_service().attach_kpi_logic_to_draft(draft_id, normalized)
        except Exception as exc:
            st.toast(f"Normalized, but could not attach to the draft: {exc}", icon="⚠️")
    _upsert(
        job,
        status="completed",
        description=(
            f"Normalized {normalized.get('runnable_count', 0)} of "
            f"{normalized.get('total_count', 0)} KPI queries for Databricks."
        ),
    )
    st.toast("KPI SQL Agent completed normalization.", icon="✅")
    return True
