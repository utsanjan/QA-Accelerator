"""About page: what the tool does, how the app flows, and what each agent does."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.components.theme import page_header
from app.components.tooltips import register_tips, tip

_CSS = """
<style>
.about-lead { font-size:15px; line-height:1.65; color:var(--text); margin:4px 0 18px; max-width:880px; }
.about-lead strong { color:var(--on-primary-container,#d0eeff); }
.about-eyebrow { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.1em;
  color:var(--primary,#38bdf8); margin:0 0 6px; }
.about-agent-head { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:6px; }
.about-agent-name { font-size:18px; font-weight:700; color:var(--text); }
.about-badge { font-size:11px; font-weight:700; padding:3px 11px; border-radius:999px; letter-spacing:.02em;
  border:1px solid var(--outline-variant,#26333f); }
.about-badge.ai { color:var(--primary,#38bdf8); background:var(--primary-container,#0c4369); }
.about-badge.rule { color:var(--secondary,#4ade80); background:var(--secondary-container,#143d22); }
.about-role { color:var(--muted,#92a1b5); font-size:13.5px; margin:0 0 12px; line-height:1.55; }
.about-label { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.08em;
  color:var(--muted,#92a1b5); margin:12px 0 4px; }
.about-list { margin:0; padding-left:18px; color:var(--text); font-size:13.5px; line-height:1.6; }
.about-list li { margin:2px 0; }
.about-meta { color:var(--text); font-size:13.5px; line-height:1.55; margin:0; }
.about-meta code, .about-list code { font-size:12px; }

.about-flow { display:flex; flex-direction:column; gap:0; margin:6px 0 4px; }
.about-flow-step { display:flex; gap:14px; align-items:stretch; }
.about-flow-rail { display:flex; flex-direction:column; align-items:center; width:30px; flex-shrink:0; }
.about-flow-dot { width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-size:12px; font-weight:800; color:var(--primary,#38bdf8); background:var(--primary-container,#0c4369);
  border:2px solid var(--primary,#38bdf8); flex-shrink:0; }
.about-flow-dot.rule { color:var(--secondary,#4ade80); background:var(--secondary-container,#143d22);
  border-color:var(--secondary,#4ade80); }
.about-flow-line { flex:1; width:2px; background:var(--outline-variant,#26333f); margin:4px 0; min-height:14px; }
.about-flow-body { padding-bottom:16px; flex:1; }
.about-flow-title { font-size:15px; font-weight:700; color:var(--text); margin:3px 0 2px; }
.about-flow-text { font-size:13.5px; line-height:1.6; color:var(--muted,#92a1b5); margin:0; }
.about-flow-text strong { color:var(--text); font-weight:600; }

div[class*="st-key-about_agent_"] {
  background:var(--md-surface-container,#1a2330);
  border:1px solid var(--outline-variant,#26333f);
  border-radius:var(--shape-xl,24px);
  padding:20px 24px 16px;
  margin-bottom:6px;
}
div[class*="st-key-about_link_"] button {
  background:transparent !important; border:none !important; box-shadow:none !important;
  color:var(--primary,#38bdf8) !important; font-weight:700 !important; padding:4px 0 !important;
  min-height:0 !important; height:auto !important; justify-content:flex-start !important;
}
div[class*="st-key-about_link_"] button:hover { text-decoration:underline; background:transparent !important; }
div[class*="st-key-about_link_"] button p,
div[class*="st-key-about_link_"] button div { font-size:14px !important; font-weight:700 !important; color:var(--primary,#38bdf8) !important; margin:0 !important; }
div[class*="st-key-about_link_"] { width:fit-content !important; }

.about-credit {
  margin: 28px 0 4px;
  padding-top: 16px;
  border-top: 1px solid var(--outline-variant, #26333f);
  color: var(--muted, #92a1b5);
  font-size: 12.5px;
  letter-spacing: .02em;
  text-align: center;
  line-height: 1.5;
}
.about-credit strong { color: var(--text, #dde4ee); font-weight: 600; }
.about-heart {
  color: #f87171;
  font-size: 15px;
  line-height: 1;
  display: inline-block;
  vertical-align: -2px;
}
</style>
"""

# --------------------------------------------------------------------------- content

APP_STEPS: list[dict[str, str]] = [
    {
        "title": "Import",
        "page": "Import",
        "text": (
            "Bring the inputs in. Pick <strong>Azure DevOps</strong> (user stories by work item ID), "
            "<strong>File Upload</strong> (mapping document, optional requirement document and screenshots) or "
            "<strong>Manual Entry</strong> (type a story). Azure DevOps is optional, because a mapping document "
            "alone is enough to run the ETL workflow."
        ),
    },
    {
        "title": "Build Spec",
        "page": "Build ETL Spec",
        "text": (
            "Choose the input source (latest ADO import, uploaded files, sample files or an ETL spec JSON), the "
            "<strong>workflow mode</strong> and, optionally, a <strong>KPI logic document</strong>. "
            "<strong>Generate Draft</strong> runs the Requirement Analysis and Mapping Analysis agents and saves a "
            "draft that waits for review."
        ),
    },
    {
        "title": "Review",
        "page": "Review Draft",
        "text": (
            "Check what the agents produced before anything is approved: requirement analysis, mapping preview, the "
            "mapping output (downloadable as JSON or Excel), KPI results, the editable ETL spec JSON, and the "
            "gaps and assumptions they found. Save, delete, or proceed."
        ),
    },
    {
        "title": "Generate",
        "page": "Generate QA Pack",
        "text": (
            "Approve the draft and generate the QA pack. Choose functional test cases, SQL validation tests, and "
            "whether to execute the SQL on <strong>Azure Databricks</strong> (off by default). It runs in the "
            "background, so you can keep using the app and follow it in <strong>Background Tasks</strong>."
        ),
    },
    {
        "title": "Export",
        "page": "Results & Exports",
        "text": (
            "Preview the QA report and download the report and test-case Excel. Later, use <strong>Test Case "
            "Explorer</strong> to filter cases, <strong>Spec Library</strong> for approved specs and "
            "<strong>Run History</strong> for past runs."
        ),
    },
]

WORKFLOW_MODES = """
| Mode | When it is used | What gets generated |
|---|---|---|
| **functional** | A user story or requirement document with no mapping | Functional / UI test cases only |
| **etl** | A mapping document (Excel, CSV or Word STM) | Mapping-driven SQL validation tests and data test cases |
| **hybrid** | Both a story and a mapping | Functional test cases plus SQL validation |
| **auto** | Default on Build Spec | The app detects functional or ETL from the inputs |
"""

AGENTS: list[dict[str, Any]] = [
    {
        "id": "requirement",
        "name": "Requirement Analysis Agent",
        "kind": "ai",
        "role": "Turns a business requirement into structured facts the rest of the pipeline can rely on.",
        "how": [
            "Reads the BRD or requirement document, the imported Azure DevOps stories, or the manual story.",
            "Asks the Azure OpenAI model to extract source and target tables, primary key, load type, "
            "incremental or watermark column, transformation rules, business rules and not-null columns.",
            "Records what is missing or assumed instead of guessing. With no requirement at all, the mapping "
            "document becomes the source of truth.",
        ],
        "runs": "When a draft is built (Build Spec → Generate Draft, or Import → Manual Entry).",
        "output": "The <strong>Requirement Analysis Agent</strong> section on Review. It also feeds the Mapping Analysis "
        "and Test Case agents.",
        "page": "Review Draft",
        "needs_draft": True,
    },
    {
        "id": "mapping",
        "name": "Mapping Analysis Agent",
        "kind": "ai",
        "role": "Understands the source-to-target mapping and produces the ETL spec the QA pack is built on.",
        "how": [
            "Parses the mapping document (Excel, CSV, or Word STM tables with their pseudo code).",
            "For each target table, the model writes the mapping output: transformation logic, keys, rules and "
            "gaps. Rows are normalized into canonical mappings (<code>MAP-001</code>, …).",
            "A rule-based analysis classifies each transformation (DIRECT, STRING, LOOKUP, SCD, …), assigns "
            "validation rules <code>VR01–VR26</code>, scores risk and lists gaps.",
            "The model then drafts the ETL spec, which is validated against the spec schema.",
        ],
        "runs": "When an ETL or hybrid draft is built (Build Spec → Generate Draft).",
        "output": "<strong>Mapping Analysis Agent</strong> sections and downloads on Review and Generate "
        "(JSON or Excel), and the ETL spec JSON you can edit on Review.",
        "page": "Review Draft",
        "needs_draft": True,
    },
    {
        "id": "kpi",
        "name": "KPI SQL Agent",
        "kind": "ai",
        "role": "Rewrites developer KPI queries so they run on Azure Databricks and can be used as validation tests.",
        "how": [
            "Reads a KPI logic document (<code>.sql</code>, Excel, Word, PDF, text, Markdown or JSON).",
            "Sends the queries to the model in batches of 8, several batches at a time, and keeps the original "
            "order. Each query is rewritten as Databricks SQL <strong>SELECT</strong> only.",
            "Queries that still have unresolved placeholders, or that fail the safety check, are rejected with a "
            "reason instead of being run.",
        ],
        "runs": "In the background when you click <em>Process and Normalize SQL</em> on Build Spec (KPI Logic Document).",
        "output": "A normalized-queries table and an Excel export on Build Spec. The result is attached to the "
        "draft on <strong>Generate Draft</strong> and summarized on Review. A functional draft with a KPI document "
        "also gets SQL validation tests.",
        "page": "Build ETL Spec",
        "needs_draft": False,
    },
    {
        "id": "etl",
        "name": "ETL Agent",
        "kind": "rule",
        "role": "Plans test coverage before any SQL is written, and says honestly where evidence is missing.",
        "how": [
            "Checks the ETL spec and mapping analysis against ten validation categories: schema, "
            "source-target reconciliation, data quality, transformation, business rules, incremental load, SCD, "
            "negative and boundary, regression and lineage.",
            "Marks each category <strong>covered</strong> (with the evidence found) or <strong>gap</strong> (with "
            "what to provide). It never invents tables or rules, and uses no model.",
        ],
        "runs": "At the start of QA pack generation.",
        "output": "The coverage plan guides the SQL Agent, and the result is listed as <em>ETL Agent Coverage</em> in the "
        "QA report.",
        "page": "Results & Exports",
        "needs_draft": True,
    },
    {
        "id": "sql",
        "name": "SQL Agent",
        "kind": "ai",
        "role": "Writes the SELECT-only validation queries that check the data.",
        "how": [
            "Analyzes the approved spec and builds a validation plan, using the Mapping Analysis Agent's "
            "<code>mapping_id</code> + <code>rule_id</code> items (what to test) and the ETL Agent plan.",
            "The model writes the SQL (how to test it). Plan items that end up without SQL are reported as gaps.",
            "A safety check blocks everything except <code>SELECT</code> / <code>WITH … SELECT</code>. INSERT, "
            "UPDATE, DELETE, MERGE, DROP, TRUNCATE, ALTER, CREATE, GRANT, REVOKE and EXEC are rejected.",
        ],
        "runs": "During Generate QA Pack, when <em>Include SQL validation tests</em> is on.",
        "output": "SQL validation tests, a list of blocked queries, and the gaps and assumptions in the report.",
        "page": "Generate QA Pack",
        "needs_draft": True,
    },
    {
        "id": "testcase",
        "name": "Test Case Agent",
        "kind": "ai",
        "role": "Produces the structured test cases that testers actually execute.",
        "how": [
            "With requirement context, the model writes functional and UI test cases, using screenshot "
            "file names as UI context. It also produces scenario summaries and a requirement traceability matrix.",
            "Each approved SQL test becomes a data validation test case. Duplicates are merged by test ID.",
        ],
        "runs": "During Generate QA Pack (<em>Approve &amp; Generate QA Pack</em>).",
        "output": "Test cases in Results &amp; Exports and in <strong>Test Case Explorer</strong>, plus the Excel workbook.",
        "page": "Generate QA Pack",
        "needs_draft": True,
    },
    {
        "id": "reporting",
        "name": "Reporting Agent",
        "kind": "rule",
        "role": "Assembles the final QA pack with the evidence behind it.",
        "how": [
            "Builds a Markdown report: run summary, scope, analyst notes, missing information, ETL coverage, "
            "KPI normalization, mapping analysis (VR coverage and risk), blocked queries and the traceability matrix.",
            "Adds execution evidence from Databricks (PASS, FAIL, SKIPPED and others) when queries were executed.",
        ],
        "runs": "Last step of QA pack generation.",
        "output": "<strong>QA Report Preview · Reporting Agent</strong> on Results &amp; Exports, and the downloadable report.",
        "page": "Results & Exports",
        "needs_draft": True,
    },
]

PIPELINE: list[dict[str, str]] = [
    {
        "title": "Draft stage (Build Spec → Generate Draft)",
        "text": (
            "<strong>Requirement Analysis Agent</strong> reads the requirement. If a mapping is present, the "
            "<strong>Mapping Analysis Agent</strong> then writes the mapping output and drafts the ETL spec. If a KPI "
            "document was uploaded, the <strong>KPI SQL Agent</strong> has already normalized it in the background and its "
            "result is attached. The draft is saved as <em>pending review</em>."
        ),
        "kind": "ai",
    },
    {
        "title": "Review (you)",
        "text": "Nothing is approved automatically. You check the agents' output, edit the ETL spec if needed, and proceed.",
        "kind": "rule",
    },
    {
        "title": "Analyze spec",
        "text": (
            "The <strong>ETL Agent</strong> builds the coverage plan, and the model turns the spec and mapping plan "
            "into a validation plan with gaps and assumptions."
        ),
        "kind": "ai",
    },
    {
        "title": "Generate SQL tests",
        "text": "The <strong>SQL Agent</strong> writes SELECT-only queries for each plan item. Items it cannot cover are reported.",
        "kind": "ai",
    },
    {
        "title": "Safety check",
        "text": "Every query is validated. Anything that is not a pure SELECT is blocked and listed in the report.",
        "kind": "rule",
    },
    {
        "title": "Generate test cases",
        "text": (
            "The <strong>Test Case Agent</strong> writes functional / UI cases from the requirement and converts each "
            "approved SQL test into a data validation case."
        ),
        "kind": "ai",
    },
    {
        "title": "Execute on Azure Databricks (optional)",
        "text": (
            "Off by default. When on, approved queries run on the SQL warehouse. Queries are skipped when execution is "
            "disabled, credentials are placeholders, or placeholders remain unresolved."
        ),
        "kind": "rule",
    },
    {
        "title": "Format the QA report",
        "text": "The <strong>Reporting Agent</strong> assembles the Markdown pack and Excel outputs with the execution evidence.",
        "kind": "rule",
    },
]


# --------------------------------------------------------------------------- rendering


def _go(page: str) -> None:
    st.session_state["current_page"] = page
    st.rerun()


def _flow(items: list[dict[str, str]]) -> str:
    rows = []
    last = len(items) - 1
    for index, item in enumerate(items):
        dot_class = "rule" if item.get("kind") == "rule" else ""
        line = '<div class="about-flow-line"></div>' if index != last else ""
        rows.append(
            '<div class="about-flow-step">'
            f'<div class="about-flow-rail"><div class="about-flow-dot {dot_class}">{index + 1}</div>{line}</div>'
            '<div class="about-flow-body">'
            f'<div class="about-flow-title">{html.escape(item["title"])}</div>'
            f'<p class="about-flow-text">{item["text"]}</p>'
            "</div></div>"
        )
    return '<div class="about-flow">' + "".join(rows) + "</div>"


def _render_app_tab() -> None:
    st.markdown(
        '<p class="about-lead"><strong>QA Accelerator</strong> turns requirements and source-to-target mappings into a '
        "reviewed, exportable <strong>QA pack</strong> for ETL and data pipelines. A set of AI agents reads your inputs, "
        "drafts a spec and writes the validation SQL and test cases. A <strong>human review step</strong> sits between "
        "drafting and generation, and every SQL statement is checked to be read-only before it can run on "
        "<strong>Azure Databricks</strong>.</p>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="about-eyebrow">The workflow</div>', unsafe_allow_html=True)
    register_tips(
        {f"about_link_step_{index}": f"Opens: {step['page']}" for index, step in enumerate(APP_STEPS, start=1)}
    )
    for index, step in enumerate(APP_STEPS, start=1):
        text_col, link_col = st.columns([6, 1.3], vertical_alignment="center")
        text_col.markdown(
            '<div class="about-flow-step"><div class="about-flow-rail">'
            f'<div class="about-flow-dot">{index}</div></div>'
            f'<div class="about-flow-body"><div class="about-flow-title">{html.escape(step["title"])}</div>'
            f'<p class="about-flow-text">{step["text"]}</p></div></div>',
            unsafe_allow_html=True,
        )
        if link_col.button(f"Open {step['title']} →", key=f"about_link_step_{index}", type="tertiary"):
            _go(step["page"])

    st.markdown('<div class="about-eyebrow" style="margin-top:18px;">Workflow modes</div>', unsafe_allow_html=True)
    st.markdown(WORKFLOW_MODES)

    st.markdown('<div class="about-eyebrow" style="margin-top:18px;">Good to know</div>', unsafe_allow_html=True)
    st.markdown(
        "- **Background Tasks** (the bell in the top bar and the *Tasks* page) tracks long jobs such as KPI "
        "normalization and QA pack generation.\n"
        "- **Settings** shows the last connection check for Azure OpenAI, Azure DevOps and Azure Databricks. "
        "Checks run only when you press Recheck.\n"
        "- Generated reports and Excel files are saved under `output/`."
    )


def _render_agent_card(agent: dict[str, Any], has_draft: bool) -> None:
    badge_class = "ai" if agent["kind"] == "ai" else "rule"
    badge_text = "Uses Azure OpenAI" if agent["kind"] == "ai" else "Rule-based"
    badge_tip = (
        "Calls your Azure OpenAI deployment. Output is checked and shown for review."
        if agent["kind"] == "ai"
        else "Plain code, no model call. The same input always gives the same output."
    )
    how_items = "".join(f"<li>{item}</li>" for item in agent["how"])
    with st.container(border=True, key=f"about_agent_{agent['id']}"):
        st.markdown(
            f'<div class="about-agent-head"><span class="about-agent-name">{html.escape(agent["name"])}</span>'
            f'<span class="about-badge {badge_class}"{tip(badge_tip)}>{badge_text}</span></div>'
            f'<p class="about-role">{agent["role"]}</p>'
            f'<div class="about-label">How it works</div><ul class="about-list">{how_items}</ul>'
            f'<div class="about-label">When it runs</div><p class="about-meta">{agent["runs"]}</p>'
            f'<div class="about-label">What you get</div><p class="about-meta">{agent["output"]}</p>',
            unsafe_allow_html=True,
        )
        if st.button("Access it from here →", key=f"about_link_{agent['id']}", type="tertiary"):
            _go(agent["page"])
        if agent.get("needs_draft") and not has_draft:
            st.caption("Needs a draft first. Start from Import, then Build Spec.")


def _render_agents_tab() -> None:
    st.markdown(
        '<p class="about-lead">Seven agents, each with one job. Five call the Azure OpenAI model. The ETL Agent and '
        "Reporting Agent are rule-based, so they are deterministic and explain exactly what they used. Use the link on "
        "each card to open the part of the app where that agent works.</p>",
        unsafe_allow_html=True,
    )
    has_draft = bool(st.session_state.get("draft_id"))
    register_tips({f"about_link_{agent['id']}": f"Opens: {agent['page']}" for agent in AGENTS})
    for agent in AGENTS:
        _render_agent_card(agent, has_draft)


def _render_pipeline_tab() -> None:
    st.markdown(
        '<p class="about-lead">The agents hand work to each other in a fixed order. Blue steps use the Azure OpenAI '
        "model, green steps are rule-based or human. Steps 3 to 8 run in the background when you press "
        "<strong>Approve &amp; Generate QA Pack</strong>.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(_flow(PIPELINE), unsafe_allow_html=True)

    st.markdown('<div class="about-eyebrow" style="margin-top:6px;">Safety rules</div>', unsafe_allow_html=True)
    st.markdown(
        "- Only **SELECT** and **WITH … SELECT** statements are ever allowed.\n"
        "- Databricks execution is **off by default** and is skipped when credentials are placeholders.\n"
        "- Agents list gaps and assumptions rather than guessing, and they show up in Review and in the report.\n"
        "- Secrets stay in `.env` and are never shown in the UI."
    )


def render() -> None:
    page_header(
        "About QA Accelerator",
        "What the tool does, how the app flows, and how each agent works.",
        eyebrow="Help",
    )
    st.markdown(_CSS, unsafe_allow_html=True)

    tab_app, tab_agents, tab_pipeline = st.tabs(["How the app works", "Agents", "Agent workflow"])
    with tab_app:
        _render_app_tab()
    with tab_agents:
        _render_agents_tab()
    with tab_pipeline:
        _render_pipeline_tab()

    st.html(
        '<div class="about-credit">'
        'Built with <span class="about-heart" aria-hidden="true">❤</span> by '
        "<strong>Utsanjan Maity</strong>"
        "</div>"
    )
