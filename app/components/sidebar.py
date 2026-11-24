from __future__ import annotations

import html

import streamlit as st

from app.components.tooltips import register_tips, tip

NAV_GROUPS: dict[str, list[tuple[str, str, str]]] = {
    "Workflow": [
        ("Home", "Home", "Dashboard and quick actions"),
        ("Import", "Import", "Mapping, ADO, or manual entry"),
        ("Build ETL Spec", "Build Spec", "Create draft spec"),
        ("Review Draft", "Review", "Edit before approval"),
        ("Generate QA Pack", "Generate", "Run Test Case Agent"),
        ("Results & Exports", "Exports", "Download outputs"),
    ],
    "Explore": [
        ("Test Case Explorer", "Test Cases", "Filter and inspect cases"),
        ("Spec Library", "Spec Library", "Approved ETL specs"),
        ("Run History", "History", "Past QA runs"),
    ],
    "System": [
        ("Background Tasks", "Tasks", "Monitor background jobs"),
        ("Settings", "Settings", "Connections and health"),
        ("About", "About", "Agents and how it works"),
    ],
}

_MODE_HINTS = {
    "functional": "functional: requirement-driven test cases only.",
    "etl": "etl: mapping-driven SQL validation and data test cases.",
    "hybrid": "hybrid: functional test cases plus SQL validation.",
    "auto": "auto: the app decides from the inputs.",
}


def render_sidebar() -> str:
    from app.views import PAGES

    page_names = list(PAGES.keys())
    current = st.session_state.get("current_page", "Home")
    if current not in page_names:
        current = "Home"
        st.session_state["current_page"] = current

    st.html(
        f"""
        <div class="sidebar-brand">
          <div class="sidebar-brand-icon" role="img" aria-label="ETL QA Accelerator"></div>
          <div class="sidebar-brand-text">
            <div class="sidebar-brand-eyebrow">QA Platform</div>
            <div class="sidebar-brand-title">Accelerator</div>
          </div>
          <span class="sidebar-collapse-slot" role="button" tabindex="0" aria-label="Collapse sidebar" data-qa-tip="Collapse sidebar"></span>
        </div>
        <div class="sidebar-tagline">From stories and mappings to a QA pack</div>
        """
    )

    register_tips(
        {
            f"nav_{page_name}": hint
            for items in NAV_GROUPS.values()
            for page_name, _label, hint in items
        }
    )

    for group_index, (group_name, items) in enumerate(NAV_GROUPS.items()):
        head_class = "sb-group-head" + (" sb-group-head-split" if group_index else "")
        st.html(f'<div class="{head_class}">{html.escape(group_name)}</div>')
        for page_name, short_label, _hint in items:
            if page_name not in PAGES:
                continue
            is_active = page_name == current
            if st.button(
                short_label,
                key=f"nav_{page_name}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["current_page"] = page_name
                st.rerun()

    page = st.session_state.get("current_page", current)
    draft_id = st.session_state.get("draft_id", "")
    workflow_mode = st.session_state.get("workflow_mode", "etl")
    last = st.session_state.get("last_validation_result") or {}
    generation_job = st.session_state.get("qa_generation_job")

    status_bits: list[str] = []
    if draft_id:
        status_bits.append(
            f'<div class="sidebar-status-row"{tip("Draft ID: " + draft_id)}><span>Draft</span>'
            f"<code>{html.escape(draft_id[:8])}…</code></div>"
        )
        mode_hint = _MODE_HINTS.get(str(workflow_mode), f"Workflow mode: {workflow_mode}")
        status_bits.append(
            f'<div class="sidebar-status-row"{tip(mode_hint)}><span>Mode</span>'
            f"<strong>{html.escape(str(workflow_mode))}</strong></div>"
        )
    if last.get("run_id"):
        status_bits.append(
            f'<div class="sidebar-status-row"{tip("Run ID: " + str(last["run_id"]))}><span>Last run</span>'
            f"<code>{html.escape(str(last['run_id'])[:8])}</code></div>"
        )
    if last.get("test_cases"):
        status_bits.append(
            f'<div class="sidebar-status-row"{tip("Test cases in the latest QA pack")}><span>Test cases</span>'
            f"<strong>{len(last['test_cases'])}</strong></div>"
        )
    if generation_job:
        if not generation_job["future"].done():
            job_status = "Running in background"
        elif generation_job.get("status") == "failed":
            job_status = "Failed"
        else:
            job_status = "Ready to review"
        status_bits.append(
            '<div class="sidebar-status-row"><span>QA pack</span>'
            f"<strong>{html.escape(job_status)}</strong></div>"
        )

    st.html('<div class="sb-session-sep" role="separator"></div>')
    if status_bits:
        st.html(
            '<div class="sidebar-section-label">Session</div>'
            f'<div class="sidebar-status-card">{"".join(status_bits)}</div>'
        )
    else:
        st.html(
            f'<div class="sidebar-session-compact"'
            f'{tip("No draft yet. Build one from Import, then Build Spec.")}>'
            "No draft yet</div>"
        )

    st.html('<div class="sidebar-footer">Insight Studio · ETL QA · v1.0</div>')

    return page
