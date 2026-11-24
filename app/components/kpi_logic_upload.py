from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.components.file_upload import save_upload
from app.state.kpi_job import get_kpi_job, kpi_job_running, start_kpi_normalization
from app.state.session import UPLOADS, get_service
from src.exporters.kpi_exporter import kpi_normalization_excel_bytes


def _requirement_context() -> str:
    parts: list[str] = []
    latest = st.session_state.get("latest_ado_import")
    if latest and latest.get("requirements_path"):
        req_path = Path(latest["requirements_path"])
        if req_path.exists():
            parts.append(req_path.read_text(encoding="utf-8")[:4000])

    draft_id = st.session_state.get("draft_id", "")
    if draft_id:
        draft = get_service().review_store.get_draft(draft_id)
        if draft:
            req_path = (draft.get("source_files") or {}).get("requirements_path", "")
            if req_path and Path(req_path).exists():
                parts.append(Path(req_path).read_text(encoding="utf-8")[:4000])
    return "\n\n".join(parts)


def render_kpi_logic_section(*, draft_id: str | None = None, key_prefix: str = "kpi") -> None:
    """Upload a developer KPI logic document, normalize SQL for Databricks, and preview results."""
    service = get_service()
    st.subheader("KPI Logic Document")
    st.caption(
        "Upload developer SQL for UI KPI validation. Each query is reviewed and normalized "
        "to be runnable on Azure Databricks."
    )

    kpi_upload = st.file_uploader(
        "KPI Logic Document",
        type=["xlsx", "xlsm", "csv", "sql", "txt", "docx", "pdf", "md", "json"],
        key=f"{key_prefix}_file",
    )

    job = get_kpi_job()
    running = kpi_job_running()
    if running:
        st.info("KPI SQL Agent is normalizing SQL in the background. Track progress from the Background Tasks bell.")
    elif job and job.get("status") == "failed":
        st.error(f"KPI SQL Agent failed: {job.get('error', 'Unknown error')}")

    normalized = st.session_state.get("kpi_logic_normalized")
    if not normalized and draft_id:
        draft = service.review_store.get_draft(draft_id)
        if draft:
            normalized = service._load_kpi_normalization(draft.get("source_files") or {})

    with st.container(horizontal=True, gap="small", vertical_alignment="center"):
        process_clicked = st.button(
            "Process and Normalize SQL",
            help="KPI SQL Agent rewrites the uploaded queries as Databricks SELECT-only SQL. Runs in the background.",
            type="primary",
            key=f"{key_prefix}_process",
            disabled=running,
            width="content",
        )
        if normalized:
            export_name = Path(normalized.get("source_path") or "kpi_logic").stem
            st.download_button(
                "Export Excel",
                data=kpi_normalization_excel_bytes(normalized),
                file_name=f"{export_name}_normalized.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Download the normalized KPI queries as an Excel workbook.",
                key=f"{key_prefix}_export_excel",
                width="content",
            )

    if process_clicked:
        if kpi_upload is None:
            st.error("Upload a KPI logic document first.")
            return
        try:
            saved_path = save_upload(kpi_upload, UPLOADS / "kpi_logic")
            start_kpi_normalization(
                service,
                saved_path,
                requirement_context=_requirement_context(),
                draft_id=draft_id,
            )
        except Exception as exc:
            st.error(str(exc))
        else:
            st.toast("KPI SQL Agent started. Track it in Background Tasks.", icon="⏳")
            st.rerun()

    if not normalized:
        return

    _render_kpi_results(normalized)


def render_kpi_summary(
    normalized: dict | None,
    *,
    key_prefix: str = "kpi_summary",
    source_path: str = "",
) -> None:
    """Read-only summary of a normalized KPI logic document (used on the Review page)."""
    if not normalized:
        return

    st.subheader("KPI Logic Document")
    name = Path(source_path or normalized.get("source_path") or "kpi_logic").name
    st.caption(f"Attached on Build Spec: `{name}`")
    st.download_button(
        "Export Excel",
        data=kpi_normalization_excel_bytes(normalized),
        file_name=f"{Path(name).stem}_normalized.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Download the normalized KPI queries as an Excel workbook.",
        key=f"{key_prefix}_export_excel",
    )
    _render_kpi_results(normalized)


def _render_kpi_results(normalized: dict) -> None:
    runnable = normalized.get("runnable_count", 0)
    total = normalized.get("total_count", 0)
    rejected = normalized.get("rejected_queries") or []

    col1, col2, col3 = st.columns(3)
    col1.metric("Total KPI Queries", total)
    col2.metric("Databricks-Ready", runnable)
    col3.metric("Rejected / Blocked", len(rejected))

    if normalized.get("global_notes"):
        with st.expander("Normalization notes"):
            for note in normalized["global_notes"]:
                st.markdown(f"- {note}")

    queries = normalized.get("queries") or []
    if queries:
        with st.expander("Normalized SQL preview", expanded=False):
            for entry in queries:
                status = "Ready" if entry.get("runnable") else "Blocked"
                st.markdown(f"**{entry.get('kpi_id', '')} — {entry.get('kpi_name', '')}** ({status})")
                if entry.get("fixes_applied"):
                    st.caption("Fixes: " + "; ".join(entry["fixes_applied"]))
                if entry.get("issues_remaining"):
                    st.warning("; ".join(entry["issues_remaining"]))
                sql = entry.get("normalized_sql") or entry.get("original_sql") or ""
                if sql:
                    st.code(sql, language="sql")

    if rejected:
        with st.expander("Rejected queries"):
            for item in rejected:
                st.markdown(f"- {item}")
