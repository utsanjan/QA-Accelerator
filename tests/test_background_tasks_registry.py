from __future__ import annotations

from app.state.background_tasks import (
    BackgroundTask,
    TaskKind,
    active_task_count,
    clear_completed_tasks,
    dismiss_task,
    get_tasks,
    task_summary,
    upsert_task,
)


class _FakeSession(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def test_task_summary_and_dismiss(monkeypatch):
    import app.state.background_tasks as mod
    import streamlit as st

    fake = _FakeSession(
        {
            "background_tasks": [
                BackgroundTask(
                    id="t1",
                    name="A",
                    description="d",
                    status="completed",
                    progress=100,
                    kind=TaskKind.GENERIC,
                    source="live",
                ).to_dict()
            ],
            "background_tasks_dismissed": set(),
            "background_tasks_include_demo": False,
            "bg_task_panel_open": False,
            "bg_task_expanded_id": "",
        }
    )
    monkeypatch.setattr(st, "session_state", fake, raising=False)
    tasks = get_tasks(include_demo=False)
    assert len(tasks) == 1
    assert task_summary(tasks)["completed"] == 1
    dismiss_task("t1")
    assert "t1" in fake["background_tasks_dismissed"]


def test_upsert_replaces_existing(monkeypatch):
    import streamlit as st

    fake = _FakeSession(
        {
            "background_tasks": [],
            "background_tasks_dismissed": set(),
            "background_tasks_include_demo": False,
            "bg_task_panel_open": False,
            "bg_task_expanded_id": "",
        }
    )
    monkeypatch.setattr(st, "session_state", fake, raising=False)
    upsert_task(
        BackgroundTask(
            id="x",
            name="One",
            description="",
            status="running",
            progress=10,
            source="live",
        )
    )
    upsert_task(
        BackgroundTask(
            id="x",
            name="One",
            description="",
            status="running",
            progress=40,
            source="live",
        )
    )
    tasks = get_tasks(include_demo=False)
    assert len(tasks) == 1
    assert tasks[0].progress == 40
    assert active_task_count(tasks) == 1


def test_clear_completed(monkeypatch):
    import streamlit as st

    fake = _FakeSession(
        {
            "background_tasks": [
                BackgroundTask(
                    id="done",
                    name="Done",
                    description="",
                    status="completed",
                    progress=100,
                    source="live",
                ).to_dict(),
                BackgroundTask(
                    id="run",
                    name="Run",
                    description="",
                    status="running",
                    progress=5,
                    source="live",
                ).to_dict(),
            ],
            "background_tasks_dismissed": set(),
            "background_tasks_include_demo": False,
            "bg_task_panel_open": False,
            "bg_task_expanded_id": "",
        }
    )
    monkeypatch.setattr(st, "session_state", fake, raising=False)
    clear_completed_tasks()
    tasks = get_tasks(include_demo=False)
    assert len(tasks) == 1
    assert tasks[0].id == "run"
