from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
import math

import streamlit as st

TaskStatus = Literal["running", "completed", "failed", "queued"]


class TaskKind(str, Enum):
    QA_PACK = "qa_pack"
    REPORT = "report"
    UPLOAD = "upload"
    DATASET = "dataset"
    NOTIFY = "notify"
    GENERIC = "generic"


ICON_BY_KIND: dict[TaskKind, str] = {
    TaskKind.QA_PACK: "fact_check",
    TaskKind.REPORT: "description",
    TaskKind.UPLOAD: "cloud_upload",
    TaskKind.DATASET: "database",
    TaskKind.NOTIFY: "schedule",
    TaskKind.GENERIC: "pending_actions",
}


@dataclass
class BackgroundTask:
    id: str
    name: str
    description: str
    status: TaskStatus
    progress: float
    kind: TaskKind = TaskKind.GENERIC
    started_at: str = ""
    updated_at: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    indeterminate: bool = False
    source: Literal["live", "demo"] = "live"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackgroundTask:
        kind = data.get("kind", TaskKind.GENERIC.value)
        if isinstance(kind, str):
            kind = TaskKind(kind)
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data["description"]),
            status=data["status"],
            progress=float(data.get("progress") or 0),
            kind=kind,
            started_at=str(data.get("started_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            error=str(data.get("error") or ""),
            metadata=dict(data.get("metadata") or {}),
            indeterminate=bool(data.get("indeterminate")),
            source=data.get("source", "live"),
        )


QA_TASK_ID = "qa-pack-generation"

_DEMO_TASKS: list[BackgroundTask] = [
    BackgroundTask(
        id="demo-generating-report",
        name="Generating Report",
        description="Compiling report data and generating charts.",
        status="running",
        progress=65,
        kind=TaskKind.REPORT,
        source="demo",
    ),
    BackgroundTask(
        id="demo-uploading-files",
        name="Uploading Files",
        description="Uploading 12 files to cloud storage.",
        status="running",
        progress=32,
        kind=TaskKind.UPLOAD,
        source="demo",
    ),
    BackgroundTask(
        id="demo-processing-dataset",
        name="Processing Dataset",
        description="Dataset successfully processed.",
        status="completed",
        progress=100,
        kind=TaskKind.DATASET,
        source="demo",
    ),
    BackgroundTask(
        id="demo-sending-notifications",
        name="Sending Notifications",
        description="Waiting for available processing capacity.",
        status="queued",
        progress=0,
        kind=TaskKind.NOTIFY,
        source="demo",
    ),
]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def init_background_task_state() -> None:
    defaults: dict[str, Any] = {
        "background_tasks": [],
        "background_tasks_dismissed": set(),
        "background_tasks_include_demo": False,
        "bg_task_panel_open": False,
        "bg_task_expanded_id": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    st.session_state["background_tasks_include_demo"] = False
    st.session_state["background_tasks"] = [
        item
        for item in _tasks_raw()
        if item.get("source", "live") != "demo"
    ]


def _tasks_raw() -> list[dict[str, Any]]:
    return list(st.session_state.get("background_tasks") or [])


def _save_tasks(tasks: list[BackgroundTask]) -> None:
    st.session_state["background_tasks"] = [t.to_dict() for t in tasks]


def get_tasks(*, include_demo: bool = True, include_dismissed: bool = False) -> list[BackgroundTask]:
    init_background_task_state()
    dismissed = st.session_state.get("background_tasks_dismissed") or set()
    tasks = [BackgroundTask.from_dict(item) for item in _tasks_raw()]
    by_id = {t.id: t for t in tasks}

    show_demo = include_demo and st.session_state.get("background_tasks_include_demo", False)
    has_live = any(t.source == "live" and t.status in ("running", "queued") for t in tasks)
    if show_demo and not has_live:
        for demo in _DEMO_TASKS:
            if demo.id not in by_id and demo.id not in dismissed:
                by_id[demo.id] = demo

    visible = []
    for task in by_id.values():
        if not include_dismissed and task.id in dismissed:
            continue
        if has_live and task.source == "demo":
            continue
        visible.append(task)

    order = {"running": 0, "queued": 1, "failed": 2, "completed": 3}
    visible.sort(key=lambda t: (order.get(t.status, 9), t.name.lower()))
    return visible


def task_summary(tasks: list[BackgroundTask]) -> dict[str, int]:
    return {
        "running": sum(1 for t in tasks if t.status == "running"),
        "queued": sum(1 for t in tasks if t.status == "queued"),
        "completed": sum(1 for t in tasks if t.status == "completed"),
        "failed": sum(1 for t in tasks if t.status == "failed"),
    }


def active_task_count(tasks: list[BackgroundTask]) -> int:
    return sum(1 for t in tasks if t.status in ("running", "queued"))


def dismiss_task(task_id: str) -> None:
    init_background_task_state()
    dismissed = set(st.session_state.get("background_tasks_dismissed") or set())
    dismissed.add(task_id)
    st.session_state["background_tasks_dismissed"] = dismissed
    tasks = [t for t in _tasks_raw() if t.get("id") != task_id]
    st.session_state["background_tasks"] = tasks


def clear_completed_tasks() -> None:
    init_background_task_state()
    dismissed = set(st.session_state.get("background_tasks_dismissed") or set())
    for task in get_tasks(include_dismissed=True):
        if task.status == "completed":
            dismissed.add(task.id)
    st.session_state["background_tasks_dismissed"] = dismissed
    st.session_state["background_tasks"] = [
        item for item in _tasks_raw() if BackgroundTask.from_dict(item).status != "completed"
    ]


def upsert_task(task: BackgroundTask) -> None:
    init_background_task_state()
    tasks = [BackgroundTask.from_dict(item) for item in _tasks_raw()]
    replaced = False
    for index, existing in enumerate(tasks):
        if existing.id == task.id:
            tasks[index] = task
            replaced = True
            break
    if not replaced:
        tasks.append(task)
    _save_tasks(tasks)


def _estimate_qa_progress(started_at: str) -> float:
    try:
        started = datetime.fromisoformat(started_at)
        elapsed = (datetime.now(UTC) - started.astimezone(UTC)).total_seconds()
    except (TypeError, ValueError):
        elapsed = 0.0
    # Smooth approach to 92% while waiting on the worker.
    return min(92.0, 12.0 + 80.0 * (1 - math.exp(-elapsed / 120.0)))


def sync_qa_generation_task() -> None:
    from app.state.session import get_qa_generation_job

    job = get_qa_generation_job()
    if not job:
        return

    started = job.get("started_at") or _now_iso()
    updated = _now_iso()
    future = job["future"]

    if not future.done():
        task = BackgroundTask(
            id=QA_TASK_ID,
            name="Generating QA Pack",
            description="Running SQL validation, safety checks, and test case generation.",
            status="running",
            progress=_estimate_qa_progress(started),
            kind=TaskKind.QA_PACK,
            started_at=started,
            updated_at=updated,
            indeterminate=False,
            source="live",
            metadata={
                "draft_id": job.get("draft_id", ""),
                "include_sql": job.get("include_sql", True),
                "include_functional": job.get("include_functional", True),
            },
        )
        upsert_task(task)
        return

    if job.get("status") == "failed":
        upsert_task(
            BackgroundTask(
                id=QA_TASK_ID,
                name="Generating QA Pack",
                description="Generation failed. Review the error and retry from Generate.",
                status="failed",
                progress=100,
                kind=TaskKind.QA_PACK,
                started_at=started,
                updated_at=updated,
                error=str(job.get("error") or "Unknown error"),
                source="live",
            )
        )
        return

    result = st.session_state.get("last_validation_result") or {}
    sql_n = len(result.get("tests") or [])
    tc_n = len(result.get("test_cases") or [])
    upsert_task(
        BackgroundTask(
            id=QA_TASK_ID,
            name="Generating QA Pack",
            description=f"QA pack ready · {sql_n} SQL tests · {tc_n} test cases",
            status="completed",
            progress=100,
            kind=TaskKind.QA_PACK,
            started_at=started,
            updated_at=updated,
            source="live",
        )
    )


def tick_demo_task_progress() -> None:
    from app.state.session import get_qa_generation_job

    job = get_qa_generation_job()
    if job and not job["future"].done():
        return
    if not st.session_state.get("background_tasks_include_demo", False):
        return
    tasks = [BackgroundTask.from_dict(item) for item in _tasks_raw()]
    changed = False
    for task in tasks:
        if task.source != "demo" or task.status != "running":
            continue
        task.progress = min(99.0, task.progress + 2.5)
        task.updated_at = _now_iso()
        changed = True
    if changed:
        _save_tasks(tasks)

    # Seed demo tasks into storage once so progress can tick.
    if not any(t.source == "demo" for t in tasks):
        seeded = []
        for demo in _DEMO_TASKS:
            copy = BackgroundTask.from_dict(demo.to_dict())
            if not copy.started_at:
                copy.started_at = _now_iso()
            copy.updated_at = _now_iso()
            seeded.append(copy)
        _save_tasks(seeded + tasks)


def retry_task(task_id: str) -> None:
    if task_id == QA_TASK_ID:
        from app.state.session import clear_qa_generation_job

        clear_qa_generation_job()
        dismiss_task(task_id)
        st.session_state["current_page"] = "Generate QA Pack"
        return
    dismiss_task(task_id)


def toggle_task_expanded(task_id: str) -> None:
    current = st.session_state.get("bg_task_expanded_id") or ""
    st.session_state["bg_task_expanded_id"] = "" if current == task_id else task_id
