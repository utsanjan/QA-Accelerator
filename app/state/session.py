from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from datetime import UTC, datetime
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
UPLOADS = ROOT / "uploads"
OUTPUT = ROOT / "output"
SAMPLES = ROOT / "samples"


def init_session() -> None:
    defaults: dict[str, Any] = {
        "current_page": "Home",
        "draft_id": "",
        "draft_spec_json": "",
        "latest_ado_import": None,
        "ado_work_item_ids": "",
        "uploaded_mapping_path": "",
        "uploaded_requirement_path": "",
        "saved_upload_spec_name": "",
        "build_input_source": "Uploaded files",
        "last_validation_result": None,
        "workflow_mode": "etl",
        "ui_context": "",
        "selected_run_id": "",
        "kpi_logic_normalized": None,
        "qa_generation_job": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    poll_qa_generation_job()
    from app.state.background_tasks import init_background_task_state

    init_background_task_state()


def set_validation_result(result: dict[str, Any]) -> None:
    st.session_state["last_validation_result"] = result
    st.session_state["selected_run_id"] = result.get("run_id", "")


def start_qa_generation(
    service,
    draft_id: str,
    *,
    execute_queries: bool,
    include_functional: bool,
    include_sql: bool,
) -> Future:
    job = st.session_state.get("qa_generation_job")
    if job and not job["future"].done():
        raise RuntimeError("A QA pack generation is already running.")

    executor = st.session_state.get("qa_generation_executor")
    if executor is None:
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="qa-generation")
        st.session_state["qa_generation_executor"] = executor

    future = executor.submit(
        service.approve_and_validate,
        draft_id,
        execute_queries=execute_queries,
        report_path=OUTPUT / "qa_validation_pack.md",
        test_cases_path=OUTPUT / "qa_test_cases.xlsx",
    )
    st.session_state["qa_generation_job"] = {
        "future": future,
        "draft_id": draft_id,
        "started_at": datetime.now(UTC).isoformat(),
        "include_functional": include_functional,
        "include_sql": include_sql,
    }
    return future


def get_qa_generation_job() -> dict[str, Any] | None:
    return st.session_state.get("qa_generation_job")


def clear_qa_generation_job() -> None:
    st.session_state.pop("qa_generation_job", None)


def poll_qa_generation_job() -> dict[str, Any] | None:
    job = st.session_state.get("qa_generation_job")
    if not job or not job["future"].done() or job.get("processed"):
        return job

    try:
        result = job["future"].result()
        validation = result["validation"]
        if not job["include_functional"]:
            validation["test_cases"] = [
                case
                for case in (validation.get("test_cases") or [])
                if case.get("test_type") == "Data Validation"
            ]
        if not job["include_sql"]:
            validation["tests"] = []
        set_validation_result(validation)
        job["status"] = "complete"
        if not job.get("completion_notified"):
            st.toast("QA pack generation completed.", icon="✅")
            job["completion_notified"] = True
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)
        if not job.get("completion_notified"):
            st.toast("QA pack generation failed. Open Background Tasks for details.", icon="⚠️")
            job["completion_notified"] = True
    job["processed"] = True
    return job


_PARSER_MODULES = (
    "src.parsers.tabular",
    "src.parsers.stm_extract",
    "src.parsers.excel_mapping_parser",
    "src.parsers.docx_mapping_parser",
    "src.parsers.mapping_file",
    "src.prompts.mapping_prompts",
    "src.agents.mapping_agent",
    "src.review.review_store",
    "src.services.qa_workflow",
)


def reload_mapping_stack() -> None:
    import importlib
    import sys

    for name in _PARSER_MODULES:
        module = sys.modules.get(name)
        if module is not None:
            importlib.reload(module)
    st.session_state.pop("qa_service", None)


def get_service():
    from src.parsers.mapping_file import install_mapping_parser
    from src.services.qa_workflow import QAWorkflowService

    install_mapping_parser()
    service = QAWorkflowService()
    st.session_state["qa_service"] = service
    return service
