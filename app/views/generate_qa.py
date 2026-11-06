import logging

import streamlit as st

from app.components.mapping_analysis import render_mapping_downloads
from app.components.progress_stepper import render_stepper
from app.components.run_log import render_log_button
from app.components.theme import page_header
from app.state.session import get_qa_generation_job, get_service, set_validation_result, start_qa_generation

logger = logging.getLogger(__name__)


def render() -> None:
    page_header("Generate QA Pack", "Approve the draft and generate functional and SQL validation test cases.")
    render_stepper("Generate")

    service = get_service()
    draft_id = st.session_state.get("draft_id", "")

    if not draft_id:
        st.warning("No draft selected. Review a draft first.")
        return

    draft = service.review_store.get_draft(draft_id)
    if not draft:
        st.error("Draft not found.")
        return

    source_files = draft.get("source_files") or {}
    workflow_mode = source_files.get("workflow_mode", "etl")
    has_kpi_logic = bool(source_files.get("kpi_logic_normalized_path"))
    st.info(f"Generating QA pack for **{source_files.get('spec_name', 'QA Pack')}** ({workflow_mode})")

    include_functional = st.checkbox("Include functional test cases", value=True)
    default_sql = workflow_mode != "functional" or has_kpi_logic
    include_sql = st.checkbox("Include SQL validation tests", value=default_sql)
    execute_on_adb = st.checkbox("Execute SQL on Azure Databricks", value=False)

    if workflow_mode == "functional" and not has_kpi_logic:
        include_sql = False
        st.caption("SQL validation is skipped for functional-only stories without a KPI logic document.")
    elif has_kpi_logic:
        st.caption(
            "KPI logic document attached — normalized Databricks SQL tests will be included "
            "alongside functional test cases."
        )

    render_mapping_downloads(draft, key_prefix="generate_mapping")

    job = get_qa_generation_job()
    if job and not job["future"].done():
        st.info("QA pack generation is running in the background. You can use the sidebar to visit another page.")

    if st.button(
        "Approve & Generate QA Pack",
        type="primary",
        disabled=bool(job and not job["future"].done()),
    ):
        try:
            if workflow_mode != "functional":
                import json

                edited = json.loads(st.session_state.get("draft_spec_json") or "{}")
                if service._is_complete_etl_spec(edited):
                    service.update_draft(draft_id, edited)

            start_qa_generation(
                service,
                draft_id,
                execute_queries=execute_on_adb and include_sql,
                include_functional=include_functional,
                include_sql=include_sql,
            )
            st.success("QA pack generation started in the background.")
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))
        except Exception as exc:
            logger.exception("Could not start QA pack generation")
            st.error(str(exc))
            st.caption("Open the activity log below for the full traceback.")
            render_log_button(key_prefix="generate_error_log", label="Activity log")

    job = get_qa_generation_job()
    if job and job["future"].done() and not job.get("processed"):
        try:
            result = job["future"].result()
            validation = result["validation"]
            if not include_functional:
                validation["test_cases"] = [
                    case
                    for case in (validation.get("test_cases") or [])
                    if case.get("test_type") == "Data Validation"
                ]
            if not include_sql:
                validation["tests"] = []

            set_validation_result(validation)
            job["processed"] = True
            st.success("QA pack generated successfully.")
            st.session_state["current_page"] = "Results & Exports"
            st.rerun()
        except PermissionError:
            logger.exception("QA pack generation blocked by a locked output file")
            st.error(
                "Could not write output files. Close `output/qa_test_cases.xlsx` in Excel "
                "if it is open, then try again."
            )
        except Exception as exc:
            logger.exception("QA pack generation failed")
            st.error(str(exc))
            st.caption("Open the activity log below for the full traceback.")
            render_log_button(key_prefix="generate_error_log", label="Activity log")

    if st.session_state.get("last_validation_result"):
        result = st.session_state["last_validation_result"]
        st.divider()
        st.subheader("Last Run Summary")
        cols = st.columns(4)
        cols[0].metric("SQL Tests", len(result.get("tests") or []))
        cols[1].metric("Test Cases", len(result.get("test_cases") or []))
        cols[2].metric("Run ID", (result.get("run_id") or "")[:8])
        summary = result.get("execution_summary") or {}
        cols[3].metric("ADB Status", ", ".join(f"{k}:{v}" for k, v in summary.items()) or "Not run")
