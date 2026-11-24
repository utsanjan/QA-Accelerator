import json
import logging
from pathlib import Path

import streamlit as st

from app.components.file_upload import save_upload, ui_context_from_uploads
from app.components.kpi_logic_upload import render_kpi_logic_section
from app.components.progress_stepper import render_stepper
from app.components.theme import page_header
from app.components.toast_loader import toast_loader
from app.components.tooltips import register_tips
from app.state.kpi_job import kpi_job_running
from app.state.session import SAMPLES, UPLOADS, get_service
from src.parsers.document_parser import read_requirement_document
from src.utils.workflow_mode import detect_workflow_mode

LOGGER = logging.getLogger(__name__)


def _existing_file(value: str | Path | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_file() else None


def _saved_screenshot_names() -> list[str]:
    """File names of the screenshots saved on the Import page (kept inside ``ui_context``)."""
    context = st.session_state.get("ui_context", "") or ""
    return [line[2:].strip() for line in context.splitlines() if line.startswith("- ")]


def _render_loaded_inputs(mapping: Path | None, requirement: Path | None) -> None:
    """Show which files carried over from the Import page; uploads below replace them."""
    screenshots = _saved_screenshot_names()
    if not (mapping or requirement or screenshots):
        st.caption(
            "No files carried over from the Import page. Upload a mapping document below, "
            "or add files on Import first."
        )
        return
    items = []
    if mapping:
        items.append(f"Mapping: `{mapping.name}`")
    if requirement:
        items.append(f"Requirement: `{requirement.name}`")
    if screenshots:
        items.append(f"Screenshots: {len(screenshots)} ({', '.join(f'`{name}`' for name in screenshots[:3])}"
                     f"{', ...' if len(screenshots) > 3 else ''})")
    st.caption("Loaded from Import - " + " · ".join(items) + ". Upload below to replace any of them.")


def render() -> None:
    page_header("Build ETL Spec", "Generate a draft spec from a mapping document, optional stories, or uploaded files.")
    render_stepper("Build")

    service = get_service()
    latest_ado = st.session_state.get("latest_ado_import")
    uploaded_mapping = _existing_file(st.session_state.get("uploaded_mapping_path"))
    uploaded_requirement = _existing_file(st.session_state.get("uploaded_requirement_path"))

    # Smart default: a newly loaded ADO import becomes the selected source the first time
    # it is seen here. Without an import the page never sits on the empty ADO option.
    # Only react to the import appearing or disappearing, never to the user's own clicks.
    ado_id = str(latest_ado["import_id"]) if latest_ado else ""
    previous_ado_id = st.session_state.get("build_ado_seen_id", "")
    if latest_ado and previous_ado_id != ado_id:
        st.session_state["build_input_source"] = "Latest ADO import"
    elif not latest_ado and previous_ado_id and st.session_state.get("build_input_source") == "Latest ADO import":
        st.session_state["build_input_source"] = "Uploaded files"  # the import was cleared
    st.session_state["build_ado_seen_id"] = ado_id

    source_options = ["Latest ADO import", "Uploaded files", "Sample files", "ETL spec JSON"]
    if st.session_state.get("build_input_source") not in source_options:
        st.session_state["build_input_source"] = "Uploaded files"
    register_tips(
        {
            "build_input_source": (
                "Azure DevOps import is optional. Choose Uploaded files to run from a mapping document only."
            ),
            "build_workflow_mode": "Auto detects whether the story is UI/functional or ETL/data pipeline.",
        }
    )
    source = st.radio(
        "Input source",
        source_options,
        # Streamlit shows the first option when a keyed radio first appears on a later page
        # after its value was preset in session state, so pass the index explicitly.
        index=source_options.index(st.session_state["build_input_source"]),
        horizontal=True,
        key="build_input_source",
    )
    if source == "Uploaded files":
        _render_loaded_inputs(uploaded_mapping, uploaded_requirement)
    elif source == "Latest ADO import" and not latest_ado:
        st.info("No Azure DevOps import in this session. Import stories first, or use Uploaded files instead.")
        if st.button("Go to Import", key="build_go_to_import"):
            st.session_state["current_page"] = "Import"
            st.rerun()

    spec_name = st.text_input("Spec name (optional)")

    # Only show the inputs the chosen source actually uses.
    workflow_mode = "auto"
    screenshot_uploads = None
    mapping_upload = None
    requirement_upload = None
    json_upload = None

    if source == "Uploaded files" or (source == "Latest ADO import" and latest_ado):
        workflow_mode = st.selectbox(
            "Workflow mode",
            ["auto", "functional", "etl", "hybrid"],
            key="build_workflow_mode",
        )
        mapping_label = (
            "Mapping document (Excel, CSV, or Word STM)"
            if source == "Uploaded files"
            else "Mapping document (optional)"
        )
        mapping_upload = st.file_uploader(
            mapping_label,
            type=["xlsx", "xlsm", "csv", "docx"],
            key="build_mapping",
        )
        if source == "Uploaded files":
            requirement_upload = st.file_uploader(
                "Requirement document (optional)",
                type=["txt", "docx", "pdf"],
                key="build_requirement",
            )
        screenshot_uploads = st.file_uploader(
            "UI screenshots (optional)",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="build_screenshots",
        )
    elif source == "Sample files":
        st.info(
            "The bundled sample mapping workbook and sample BRD will be used. "
            "Nothing to upload - choose another source to use your own files."
        )
    elif source == "ETL spec JSON":
        json_upload = st.file_uploader("ETL spec JSON", type=["json"], key="build_json")

    st.divider()
    # No draft exists yet; the normalized result is attached to the new draft on "Generate Draft".
    render_kpi_logic_section(draft_id=None, key_prefix="build_kpi")

    st.divider()
    # The KPI result is attached when the draft is created, so wait for a running job to
    # finish. The background poll reruns the page on completion, which re-enables the button.
    kpi_running = kpi_job_running()
    if kpi_running:
        st.info(
            "KPI SQL Agent is still normalizing the KPI logic document. "
            "Generate Draft unlocks when it finishes so the results are attached to the draft."
        )
    no_ado_import = source == "Latest ADO import" and not latest_ado
    if st.button(
        "Generate Draft",
        type="primary",
        disabled=kpi_running or no_ado_import,
        help=(
            "Wait for the KPI job to finish." if kpi_running
            else "Import ADO stories first, or pick another input source." if no_ado_import
            else "Run the Requirement and Mapping Analysis agents and save a draft for review."
        ),
    ):
        try:
            ui_context = ui_context_from_uploads(screenshot_uploads) or st.session_state.get("ui_context", "")
            mode = None if workflow_mode == "auto" else workflow_mode

            progress, finished = "Building draft...", "Draft built."
            if source == "Uploaded files":
                mapping_name = mapping_upload.name if mapping_upload else (uploaded_mapping.name if uploaded_mapping else "")
                if mapping_name:
                    extract = "extracting STM tables and " if mapping_name.lower().endswith(".docx") else ""
                    progress = f"Mapping Analysis Agent — {extract}generating mapping output with Azure OpenAI..."
                    finished = "Mapping Analysis Agent — mapping output generated."
                elif workflow_mode in ("auto", "functional") and (requirement_upload or uploaded_requirement):
                    progress = "Requirement Analysis Agent — analyzing requirement document..."
                    finished = "Requirement Analysis Agent — analysis complete."

            with toast_loader(progress, done=finished):
                if source == "Latest ADO import":
                    if not latest_ado:
                        st.error(
                            "No Azure DevOps import in this session. "
                            "Choose Uploaded files and provide a mapping document, or import stories first."
                        )
                        st.stop()
                    mapping_path = save_upload(mapping_upload, UPLOADS) if mapping_upload else None
                    draft = service.build_draft_from_ado(
                        import_id=latest_ado["import_id"],
                        mapping_path=mapping_path,
                        spec_name=spec_name or None,
                        workflow_mode=mode,
                        ui_context=ui_context,
                    )
                elif source == "Uploaded files":
                    mapping_path = save_upload(mapping_upload, UPLOADS) if mapping_upload else uploaded_mapping
                    requirement_path = (
                        save_upload(requirement_upload, UPLOADS) if requirement_upload else uploaded_requirement
                    )
                    if requirement_upload and requirement_path:
                        st.session_state["uploaded_requirement_path"] = str(requirement_path)
                    if mapping_path:
                        if mapping_upload:
                            st.session_state["uploaded_mapping_path"] = str(mapping_path)
                        draft = service.build_draft_from_files(
                            mapping_path=mapping_path,
                            requirement_path=requirement_path,
                            spec_name=spec_name or st.session_state.get("saved_upload_spec_name") or mapping_path.stem,
                            ui_context=ui_context,
                        )
                    elif workflow_mode in ("auto", "functional"):
                        req_text = read_requirement_document(requirement_path) if requirement_path else ""
                        if not req_text.strip():
                            st.error(
                                "Upload a mapping document to run the ETL workflow. "
                                "Azure DevOps stories are optional."
                            )
                            st.stop()
                        draft = service.build_functional_draft(
                            requirement_text=req_text,
                            spec_name=spec_name or st.session_state.get("saved_upload_spec_name") or None,
                            ui_context=ui_context,
                        )
                    else:
                        st.error(
                            "Upload a mapping document (Excel, CSV, or Word STM). "
                            "An Azure DevOps import is not required."
                        )
                        st.stop()
                elif source == "Sample files":
                    draft = service.build_draft_from_files(
                        mapping_path=SAMPLES / "mappings" / "sample_mapping.xlsx",
                        requirement_path=SAMPLES / "requirements" / "sample_brd.txt",
                        spec_name=spec_name or "sample_demo",
                        ui_context=ui_context,
                    )
                else:
                    if json_upload is None:
                        st.error("Upload an ETL spec JSON file.")
                        st.stop()
                    json_path = save_upload(json_upload, UPLOADS)
                    draft = service.build_draft_from_json(json_path, spec_name=spec_name or None)

            draft_id = draft["draft_id"]
            kpi_normalized = st.session_state.get("kpi_logic_normalized")
            if kpi_normalized:
                draft = service.attach_kpi_logic_to_draft(draft_id, kpi_normalized)

            st.session_state["draft_id"] = draft_id
            st.session_state["draft_spec_json"] = service.pretty_json(draft.get("etl_spec_draft") or {})
            st.session_state["workflow_mode"] = draft.get("workflow_mode") or draft.get("source_files", {}).get(
                "workflow_mode", "etl"
            )
            st.session_state["current_page"] = "Review Draft"
            st.rerun()
        except Exception as exc:
            LOGGER.exception("Failed to generate ETL draft")
            st.error(str(exc))

    if latest_ado and source == "Latest ADO import":
        st.divider()
        st.subheader("Latest ADO Import Preview")
        stories_path = latest_ado.get("stories_json_path")
        if stories_path and Path(stories_path).exists():
            stories = json.loads(Path(stories_path).read_text(encoding="utf-8"))
            detected = detect_workflow_mode(
                requirement_text=Path(latest_ado["requirements_path"]).read_text(encoding="utf-8")
                if Path(latest_ado["requirements_path"]).exists()
                else "",
                user_stories=stories,
                has_mapping=bool(latest_ado.get("mapping_path")),
            )
            st.info(f"Detected workflow mode: **{detected}**")
