# QA Accelerator — Product Requirements Document

**AI-Powered ETL and Functional QA Accelerator**

| Item | Detail |
|---|---|
| Document type | Product Requirements Document (functional, UI/UX, data, integration and non-functional) |
| Product | QA Accelerator (also shown in the UI as "Insight Studio · ETL QA · v1.0") |
| Version | 1.0 |
| Date | 20 November 2026 |
| Status | Baseline of the implemented product, with recommended enhancements listed in Section 16 |
| Platform | Web application (Streamlit), Python 3.11 or later (tested on 3.14), Windows PowerShell setup scripts |

---

## 1. Introduction

### 1.1 Purpose

This document defines the requirements of the QA Accelerator. It describes what the product does, who uses it, how users move through it, what every screen looks like and how it behaves, what data it consumes and produces, and the quality attributes it must meet. It is intended to be shared with product owners, QA leads, data engineers, developers, UX designers, testers and stakeholders who need a single reference for the whole product.

### 1.2 Product summary

The QA Accelerator turns project inputs (Azure DevOps user stories, requirement documents, source-to-target mapping documents, UI screenshots and developer KPI SQL) into a reviewable draft and then into a complete QA pack. The QA pack contains functional test cases, read-only Azure Databricks SQL validation tests, a traceability matrix, a coverage matrix, a Markdown QA report and an Excel workbook. Large language model (LLM) agents running on Azure OpenAI do the analysis and generation. A human reviews and approves the draft before anything is generated.

### 1.3 Scope

In scope:

- Importing inputs from Azure DevOps, uploaded files and manual entry.
- Parsing mapping documents in Excel, CSV and Word (STM) formats.
- Building and reviewing an ETL specification draft.
- Mapping analysis with the validation rule library VR01 to VR26, risk scoring and gap detection.
- Normalizing developer KPI SQL into Databricks-safe SELECT statements.
- Generating functional test cases, SQL validation tests and supporting artifacts.
- Optionally executing the SQL on Azure Databricks and reporting pass or fail.
- Exporting results (Markdown, Excel, JSON, ZIP).
- A spec library, run history, background task center, notifications, settings and health checks.
- A command-line interface as an optional secondary entry point.

Out of scope:

- Writing to any Databricks table. The product is strictly read-only on data.
- Authentication, user management and role-based access control (the application is a single-user workspace).
- Executing functional (UI) test cases automatically. Functional cases are produced for manual or later automated execution.
- Pushing test cases back to Azure DevOps Test Plans.

### 1.4 Intended audience

| Audience | Use of this document |
|---|---|
| Product owner, stakeholders | Understand scope, value and acceptance criteria |
| QA lead, QA engineers | Understand the workflow, generated artifacts and review points |
| Data engineers | Understand mapping inputs, SQL safety rules and Databricks execution |
| Developers | Understand functional behavior, data contracts and non-functional targets |
| UX designers | Understand the design system, screens, states and interaction rules |

### 1.5 Definitions and abbreviations

| Term | Meaning |
|---|---|
| ADB | Azure Databricks |
| ADO | Azure DevOps |
| ETL | Extract, transform, load |
| STM | Source-to-target mapping (Word document tables) |
| Draft | A reviewable, saved working copy of the ETL spec, mapping analysis and context before approval |
| ETL spec | Structured definition of source table, target table, primary key, load type, column mappings, rules and notes |
| QA pack | The set of outputs of one run: test cases, SQL tests, report, Excel, artifacts |
| VR rule | One of 26 column-level or load-level validation rules (VR01 to VR26) |
| RTM | Requirement traceability matrix |
| KPI logic document | Developer-supplied SQL used to validate UI KPI values |
| Workflow mode | functional, etl or hybrid; decides what is generated |
| Toast | A short, temporary on-screen message |
| Bell | The notification and background-task icon at the top right of every page |

---

## 2. Product Overview

### 2.1 Problem statement

QA teams working on data platforms and portal applications spend a large amount of time reading requirements and mapping sheets, designing test cases, writing validation SQL by hand, checking developer KPI SQL, and compiling reports. The work is repetitive, error-prone and hard to trace back to requirements. Mapping documents are often incomplete, which causes late discovery of gaps.

### 2.2 Objectives

| ID | Objective |
|---|---|
| OBJ-1 | Reduce the time to produce a complete, traceable QA pack from days to minutes. |
| OBJ-2 | Detect gaps and risks in mappings and requirements before testing starts. |
| OBJ-3 | Produce SQL validation tests that are safe (read-only) and traceable to mapping rules. |
| OBJ-4 | Produce execution-ready functional test cases with measurable expected results. |
| OBJ-5 | Keep the human in control: every draft is reviewed and approved before generation. |
| OBJ-6 | Give clear status, progress and notifications for long-running AI operations. |
| OBJ-7 | Deliver outputs in formats QA teams already use (Excel, Markdown, JSON, ZIP). |

### 2.3 Key capabilities

1. Multi-source intake: Azure DevOps stories, requirement documents (TXT, DOCX, PDF), mapping documents (XLSX, XLSM, CSV, DOCX STM), UI screenshots, manual stories, JSON ETL specs, KPI logic documents.
2. Automatic workflow-mode detection (functional, etl, hybrid) with manual override.
3. LLM-assisted mapping output: transformations, keys, rules, per-entity analysis.
4. Mapping analysis with canonical IDs (MAP-001 and so on), VR01 to VR26 assignment, risk levels and gap lists.
5. KPI SQL normalization to Databricks SELECT-only SQL, with fixes, issues and rejection reasons.
6. SQL safety gate and optional live execution on Azure Databricks.
7. Functional test case generation with requirement traceability, coverage and automation recommendations.
8. Rich exports and a run history.
9. Background processing with a notification bell, toasts and an activity log.

### 2.4 System context

```
 Users (QA / Data / Product)
        |
        v
 Streamlit Web UI  (app/)  <------>  Workflow service (src/services)
        |                                   |
        |                    +--------------+----------------+
        |                    |              |                |
        v                    v              v                v
  Local storage       Azure OpenAI    Azure DevOps     Azure Databricks
  (drafts, runs,      (agents, LLM    (work items,     (SELECT-only
   specs, uploads,     JSON output)    attachments)     execution)
   imports, output)
```

### 2.5 Assumptions and constraints

- An Azure OpenAI deployment (default model name gpt-5.1) is mandatory. Nothing is generated without it.
- Azure DevOps and Azure Databricks are optional and depend on the chosen workflow.
- The application runs on a single machine for a single user or a small trusted team; state is kept in the browser session and in local folders.
- The product never invents requirements. When information is missing it reports a gap or assumption instead.
- Generated Excel and Markdown files overwrite the previous pack; they are not time-stamped.
- Operating environment: Windows with PowerShell (setup scripts), Python 3.11+, a modern Chromium-based browser.

---

## 3. Users and Personas

| Persona | Goals | Typical journey |
|---|---|---|
| QA Lead | Fast, traceable test coverage; visibility of risk and gaps | Import stories, review gaps, approve, generate, export report |
| QA Engineer (functional) | Execution-ready manual test cases from stories and screenshots | Manual entry or ADO import, upload screenshots, generate, explore test cases |
| QA Engineer (data / ETL) | SQL validation per mapping rule | Upload mapping, review mapping analysis, generate SQL tests, run on Databricks |
| Data Engineer | Check mapping quality and KPI SQL | Upload mapping and KPI SQL, review normalization and rejections, export normalized KPI Excel |
| Product Owner / Stakeholder | Evidence of coverage | Open Results and Exports, read the report and traceability matrix |

---

## 4. End-to-End Workflow

### 4.1 Primary workflow

The left sidebar and the on-page stepper present five stages:

| Stage | Page | Outcome |
|---|---|---|
| 1. Import | Import | Stories, documents, mapping and optional KPI document are captured |
| 2. Build | Build ETL Spec | A draft is created (ETL spec, mapping analysis, requirement summary) |
| 3. Review | Review Draft | Human reviews gaps, edits the ETL spec JSON, attaches KPI logic |
| 4. Generate | Generate QA Pack | Draft is approved; agents generate tests and artifacts in the background |
| 5. Export | Results and Exports | Reports, Excel, JSON and ZIP are previewed and downloaded |

Supporting pages: Home, Test Case Explorer, Spec Library, Run History, Background Tasks, Settings.

### 4.2 Input paths

| Path | Description |
|---|---|
| A. Azure DevOps (typical) | Import user stories by work item ID, optional mapping attachment, then build a draft from the latest import |
| B. Files only | Upload requirement document, mapping document and screenshots; build a draft directly |
| C. Manual story | Enter title, description, acceptance criteria and business rules; creates a functional draft |
| D. Sample demo | One-click sample draft using bundled sample BRD and mapping |
| E. JSON spec | Upload an existing ETL spec JSON to create a draft |

### 4.3 Workflow modes

| Mode | Trigger | Generated outputs |
|---|---|---|
| functional | UI or story work without a usable mapping | Functional/UI test cases, RTM, coverage and automation artifacts. SQL tests are skipped unless a KPI document is attached |
| etl | Mapping and data pipeline requirements | ETL spec, mapping analysis (VR rules, risk, gaps), SQL validation tests, structured data test cases |
| hybrid | UI story plus mapping or KPI SQL | Functional cases plus SQL tests (mapping and/or KPI) |

Automatic detection (user can override on Build ETL Spec):

- ETL keywords: etl, source table, target table, staging, data warehouse, incremental load, mapping, pipeline.
- UI keywords: ui, screen, button, login, portal, dashboard, insight studio, page, form, dropdown, modal, navigation, wireframe, mockup.
- Source and target tables found, or a mapping present with ETL keywords: etl (hybrid if UI keywords are also present).
- UI keywords or user stories present: functional.
- Mapping only: etl. Nothing else: functional.
- A functional draft with an attached KPI document is promoted to hybrid at generation time.

### 4.4 Workflow state diagram

```
Import --> Build --> Draft (pending_review) --> Review --> Approve --> Generate
                                  |                                       |
                                  +--> Delete                             +--> Results / Exports
                                                                          +--> Run History
Approved ETL specs --> Spec Library --> Re-run validation --> Results
```

---

## 5. Functional Requirements

Priority key: **M** = must have (implemented baseline), **S** = should have, **C** = could have.

### 5.1 Home dashboard (FR-HOM)

| ID | Requirement | Pri |
|---|---|---|
| FR-HOM-01 | The Home page shall show a connection card for Azure OpenAI, Azure DevOps and Azure Databricks, each with a status badge (Ready, Missing, Error) and a detail line (deployment name, org/project, or workspace host; or a hint to configure `.env`). | M |
| FR-HOM-02 | The page shall show four summary cards: Pending Drafts, Recent Runs, Approved Specs and Last Run Tests. | M |
| FR-HOM-03 | The page shall provide quick actions: Go to Import, Run Sample Demo, View Latest Results. | M |
| FR-HOM-04 | Run Sample Demo shall build a draft from the bundled sample mapping and BRD, store it in the session and open Review Draft. | M |
| FR-HOM-05 | The page shall list up to five recent runs (spec name, run time, number of tests) or an empty-state message. | M |
| FR-HOM-06 | When a QA pack exists in the session the page shall show a Latest QA Pack section with the download buttons. | M |

### 5.2 Import (FR-IMP)

The Import page has three tabs (Azure DevOps, File Upload, Manual Entry). The KPI Logic Document lives on Build ETL Spec.

**Azure DevOps tab**

| ID | Requirement | Pri |
|---|---|---|
| FR-IMP-01 | The user may override organization and project; blank values fall back to `.env`. | M |
| FR-IMP-02 | The user shall enter one or more comma-separated work item IDs. An empty field shall not reuse a previous import and shall produce the error "Enter one or more Work Item IDs. An empty field does not reuse a previous story." | M |
| FR-IMP-03 | Test Connection shall call Azure DevOps and report "Connected to organization/project" or the error text. | M |
| FR-IMP-04 | Import User Stories shall fetch the work items (title, description, acceptance criteria, state, tags, area path, iteration path, type), strip HTML, and save a requirements text file, a stories JSON file and import metadata under `imports/ado/<import-id>/`, plus a `latest.json` pointer. | M |
| FR-IMP-05 | If a story has a mapping attachment (.xlsx, .xlsm, .csv, .docx) it shall be downloaded with the import. | M |
| FR-IMP-06 | Imported stories shall be shown as expandable story cards. Each card has a remove (✕) control that deletes that story from the import and rewrites the saved files and metadata. | M |
| FR-IMP-07 | The page shall offer Download Requirements (.txt), Download Stories JSON, and Build Draft from this Import (navigates to Build ETL Spec with the source set to Latest ADO import). | M |
| FR-IMP-08 | Start new import shall clear the loaded import and the work item field. A previously saved import on disk shall be loadable through Load last saved import. | M |
| FR-IMP-09 | When no explicit work item IDs are supplied, the importer shall query by project, work item types, area path and iteration path (excluding Removed items) and limit the result to the configured maximum number of stories (default 25). | S |

**File Upload tab**

| ID | Requirement | Pri |
|---|---|---|
| FR-IMP-10 | The user may upload a requirement document (TXT, DOCX, PDF; optional), a mapping document (XLSX, XLSM, CSV, DOCX STM) and UI screenshots or mockups (PNG, JPG, JPEG, WEBP; optional, multiple). | M |
| FR-IMP-11 | The user may enter a spec name. | M |
| FR-IMP-12 | Save & continue to Build Spec shall save the files, remember their paths, spec name and UI context in the session, select Uploaded files as the Build ETL Spec input source and open Build ETL Spec. It shall not build a draft. If neither a mapping nor a requirement document was uploaded it shall show "Upload a mapping document to run the ETL workflow, or a requirement document for a functional story." | M |
| FR-IMP-13 | The draft is built on Build ETL Spec (FR-BLD), which is also where any normalized KPI result is attached to it. | M |
| FR-IMP-14 | Screenshot file names shall be recorded as UI context and passed to the test case agent. | M |

**Manual Entry tab**

| ID | Requirement | Pri |
|---|---|---|
| FR-IMP-15 | The user shall provide a story title, description, acceptance criteria, business rules (one per line), optional screenshots and an optional spec name. | M |
| FR-IMP-16 | Create Functional Draft shall create a functional draft, attach KPI results if present and open Review Draft. | M |

### 5.3 Build ETL Spec (FR-BLD)

| ID | Requirement | Pri |
|---|---|---|
| FR-BLD-01 | The page shall show the workflow stepper (step 2) and an Input source selector: Latest ADO import, Uploaded files, Sample files, ETL spec JSON. The selector defaults to Latest ADO import when an import is loaded (the first time that import is seen) and to Uploaded files otherwise; the page shall never rest on Latest ADO import when no import exists. | M |
| FR-BLD-02 | The page shall show a spec name (optional) and only the inputs the selected source uses: Uploaded files - workflow mode, mapping document, optional requirement document, optional UI screenshots; Latest ADO import - workflow mode, optional mapping document, optional UI screenshots; Sample files - a note that the bundled samples are used; ETL spec JSON - the JSON uploader. | M |
| FR-BLD-03 | The page shall show the KPI Logic Document section above the Generate Draft button, matching the real workflow order (KPI logic is prepared before the draft is generated). | M |
| FR-BLD-04 | Generate Draft shall build the draft according to the selected source and mode, show a loading toast while working, and open Review Draft on success. | M |
| FR-BLD-05 | If Latest ADO import is selected without an import, the page shall show a clear error and instruct the user to upload a mapping or import stories. | M |
| FR-BLD-06 | For Uploaded files the page shall list the files carried over from the Import page (mapping, requirement, screenshots); a new upload on this page replaces the corresponding file. | S |
| FR-BLD-07 | When the source is the latest ADO import, a preview shall show the detected workflow mode. | S |
| FR-BLD-08 | Errors during draft generation shall be logged and shown inline without losing the entered inputs. | M |

### 5.4 Draft creation logic (FR-DRF)

| ID | Requirement | Pri |
|---|---|---|
| FR-DRF-01 | A draft shall be stored as a JSON file in `review/drafts/<draft-id>.json` with status `pending_review` and contain: ETL spec draft, requirement summary, mapping rows, mapping analysis, canonical mappings, entity logic, STM entities, LLM mapping output, source files, missing information and assumptions. | M |
| FR-DRF-02 | For ETL and hybrid sources the service shall: parse the mapping, ask the LLM per target table for mapping output, compute mapping analysis, build canonical mappings, and ask the Mapping Agent to produce the ETL spec. | M |
| FR-DRF-03 | A functional draft shall store an empty ETL spec by design. | M |
| FR-DRF-04 | When the requirement document is blank the Requirement Agent shall return a "mapping document only" summary and the assumption that the mapping document is the source of truth. | M |
| FR-DRF-05 | The system shall tolerate a failure of the LLM for one table by recording "LLM mapping output failed for <table>" in missing information and continuing with the parsed rows. | M |
| FR-DRF-06 | Mapping files that the application cannot read shall produce a clear unsupported-format message that lists the accepted formats (Excel, CSV, Word STM). | M |

### 5.5 Mapping document support (FR-MAP)

| ID | Requirement | Pri |
|---|---|---|
| FR-MAP-01 | Excel and CSV mappings shall use the CoE template headers: Source Database, Source Schema, Source Table, Source Column, Source Data Type, Transformation, Target Database, Target Schema, Target Table, Target Column, Target Data Type, Business Rule, Nullable, Primary Key, Notes. Header names are flexible through an alias table (for example Source Table, SOURCE_TABLE, Src Table). | M |
| FR-MAP-02 | The minimum required columns are Source Column and Target Column. Blank table cells inherit the most recent non-blank value. | M |
| FR-MAP-03 | Word STM documents shall be accepted. The parser shall read Heading 2 entity sections under the "Source to Target Mapping (STM) and Pseudo Code" chapter, read STM tables (Target Column; Source Column / Logic; Source Table(s); Original Source), keep pseudo-code per entity, skip architecture tables (environments, lakehouses, tech stack, orchestrators), and write a normalized Excel next to the Word file. | M |
| FR-MAP-04 | The system shall optionally enrich mappings with platform metadata (data types, primary keys, nullability) from a JSON file referenced by `FABRIC_METADATA_PATH`. | C |
| FR-MAP-05 | A script shall be able to export a mapping workbook from live Unity Catalog (Summary, Mapping, Inventory, Gaps sheets). | C |
| FR-MAP-06 | A mapping template and samples shall be bundled (`samples/templates/mapping_template.xlsx`, sample mapping XLSX and DOCX). | M |

### 5.6 Mapping analysis engine (FR-ANL)

| ID | Requirement | Pri |
|---|---|---|
| FR-ANL-01 | Each column mapping shall receive a canonical ID (MAP-001, MAP-002, and so on). | M |
| FR-ANL-02 | Each transformation shall be classified: DIRECT, STRING_TRANSFORMATION, DATE_TRANSFORMATION, DEFAULT_VALUE, CONDITIONAL, FILTER, CALCULATION, DATATYPE_CONVERSION, LOOKUP, JOIN, AGGREGATION, SCD, COMPLEX_SQL. | M |
| FR-ANL-03 | Each mapping shall be assigned validation rules from the VR01 to VR26 library according to its type, nullability, key flag, data types and business rule text (Appendix A). | M |
| FR-ANL-04 | Load-level rules shall be added by load type: full (VR20), snapshot (VR20), incremental (VR21), CDC (VR22). | M |
| FR-ANL-05 | Each mapping shall receive a risk level: Low, Medium, High, Very High (Appendix B). A mapping requires review when its risk is High or Very High or it has any gap. | M |
| FR-ANL-06 | Gaps shall be detected: missing source or target table or column, missing transformation, missing join condition, missing business rule, missing data types, data type family mismatch, reduced length or precision, complex transformation, and missing incremental or CDC criteria. | M |
| FR-ANL-07 | The analysis shall report totals: number of mappings, high-risk count, gap count, and a requires-review flag. | M |
| FR-ANL-08 | The ETL test plan shall assess ten coverage categories as covered or gap, with evidence or the missing input (Appendix C). | M |

### 5.7 Review Draft (FR-REV)

| ID | Requirement | Pri |
|---|---|---|
| FR-REV-01 | The page shall show the workflow stepper (step 3) and a selector Load pending draft listing pending drafts as "<first 8 chars>... \| <spec name>". | M |
| FR-REV-02 | If no draft is selected the page shall show a warning "No draft selected. Import or build a draft first."; if the draft is missing it shall show "Draft not found." | M |
| FR-REV-03 | An info banner shall show the workflow mode and the full draft ID. | M |
| FR-REV-04 | The page shall show Requirement Analysis (summary and business rules) and a collapsible Gaps and Assumptions panel (missing information as warnings, assumptions as a list, or a success message when none). | M |
| FR-REV-05 | User stories associated with the draft shall be shown as expandable cards. | M |
| FR-REV-06 | For etl and hybrid drafts the page shall show an editable ETL Spec JSON text area (320 px high) whose content persists in the session. | M |
| FR-REV-07 | For Word STM drafts the page shall show an STM summary: entity, mapping row and load-logic counts, an entity table, a per-entity mapping preview filter, pseudo-code expanders and a normalized Excel download. For other drafts it shall show a Mapping Preview of the first 20 rows. | M |
| FR-REV-08 | The page shall show LLM mapping output (entity primary keys and up to 20 transformation rules). | S |
| FR-REV-09 | The page shall show Mapping Analysis: metrics (Mappings, High risk, Gaps), a warning when review is required, a table (Mapping ID, Source, Target, Type, Logic, Risk, Rules, Gaps, Review) and the load-type rules. | M |
| FR-REV-10 | A Download control shall offer the mapping output as JSON or Excel. | M |
| FR-REV-11 | For functional drafts the page shall show a Functional QA Draft explanation instead of the ETL sections. | M |
| FR-REV-12 | The KPI Logic Document section shall be available on this page, and the path of an attached KPI document shall be displayed. | M |
| FR-REV-13 | Save Draft shall store the edited ETL spec only when it is a complete spec (source table, target table and primary key present) and shall show "Draft saved." or the error. | M |
| FR-REV-14 | Delete Draft shall remove the draft file, clear the session draft and show "Draft deleted." | M |
| FR-REV-15 | Proceed to Generate shall navigate to Generate QA Pack. | M |

### 5.8 KPI logic normalization (FR-KPI)

| ID | Requirement | Pri |
|---|---|---|
| FR-KPI-01 | The KPI Logic Document section shall accept XLSX, XLSM, CSV, SQL, TXT, DOCX, PDF, MD and JSON. It is shown on Import, Build ETL Spec and Review Draft. | M |
| FR-KPI-02 | The parser shall extract KPI entries (kpi_id, kpi_name, module, sql_query, expected_result, priority, source row). Excel/CSV use flexible headers; SQL files use `-- KPI: <name>` blocks or SELECT blocks; text documents use `KPI: <name>` followed by SQL or fall back to SELECT/WITH blocks. | M |
| FR-KPI-03 | Process and Normalize SQL for Databricks shall require an uploaded file and otherwise show "Upload a KPI logic document first." | M |
| FR-KPI-04 | Normalization shall run as a background job. The button shall be disabled while a job runs and an information message shall point to the Background Tasks bell. | M |
| FR-KPI-05 | Queries shall be sent to the KPI SQL Agent in batches of 8. Batches shall run concurrently (default 4 workers, configurable by `KPI_NORMALIZATION_WORKERS`) and the original order shall be preserved. | M |
| FR-KPI-06 | The agent shall rewrite each query to a single read-only Databricks SQL statement (SELECT or WITH ... SELECT), preserve kpi_id, module and original SQL, apply catalog and schema context, record fixes applied, record issues remaining and set a runnable flag. | M |
| FR-KPI-07 | A query shall be rejected (counted as Rejected / Blocked) when: the agent marks it not runnable; it has no SQL; it fails the SELECT-only safety check; or unresolved `${...}` placeholders remain in the normalized SQL. | M |
| FR-KPI-08 | Placeholders shall be resolved only when a safe default is stated in the requirement or runtime context. Otherwise the query is rejected with an explanation. | M |
| FR-KPI-09 | Results shall show three metric tiles: Total KPI Queries, Databricks-Ready, Rejected / Blocked; an expander of normalization notes; a Normalized SQL preview (status, fixes, remaining issues, SQL code); and a Rejected queries list. | M |
| FR-KPI-10 | The normalization result shall be saved to `uploads/kpi_logic/` (raw JSON and normalized JSON) and attached to the draft. Ready queries become KPI Data Validation tests in the QA pack. | M |
| FR-KPI-11 | An Export normalized KPI document (.xlsx) button shall appear on the same row as the process button once results exist. The workbook shall contain: Summary, Normalized KPI SQL (KPI ID, KPI Name, Module, Status, Original SQL, Normalized SQL, Fixes Applied, Issues Remaining), Rejected Queries and Normalization Notes (the last two only when there is content). | M |
| FR-KPI-12 | While the job runs, the Background Tasks bell shall show an entry "Normalizing KPI SQL" with an estimated progress bar; on completion it shall show the "Normalized X of Y KPI queries" summary, and on failure the error. A toast shall confirm completion or failure. | M |
| FR-KPI-13 | The user may cancel the task from the bell; the result of a cancelled job is discarded. | S |

### 5.9 Generate QA Pack (FR-GEN)

| ID | Requirement | Pri |
|---|---|---|
| FR-GEN-01 | The page shall show the stepper (step 4) and an info line "Generating QA pack for <spec name> (<mode>)". If no draft exists it shall warn "No draft selected. Review a draft first." | M |
| FR-GEN-02 | The page shall offer three options: Include functional test cases (default on), Include SQL validation tests (default on for etl/hybrid or when KPI logic is attached; forced off for functional drafts without KPI logic) and Execute SQL on Azure Databricks (default off). | M |
| FR-GEN-03 | A caption shall explain skipped SQL for functional-only drafts, or that KPI SQL will be included when a KPI document is attached. | M |
| FR-GEN-04 | The mapping output download shall be available on this page. | S |
| FR-GEN-05 | Approve and Generate QA Pack shall persist any edited ETL spec, approve the draft (saving a complete spec to the Spec Library) and start generation in a background thread. | M |
| FR-GEN-06 | Only one generation may run at a time. The button shall be disabled while a job runs and an information message shall say the user may visit other pages. | M |
| FR-GEN-07 | When generation finishes, the result shall be stored in the session and the app shall navigate to Results and Exports. A completion toast shall appear even if the user is on another page. | M |
| FR-GEN-08 | If the Excel output is locked, the page shall show "Could not write output files. Close output/qa_test_cases.xlsx in Excel if it is open, then try again." | M |
| FR-GEN-09 | Other errors shall be shown with a pointer to the Activity log, which shall be available as a button. | M |
| FR-GEN-10 | A Last Run Summary shall show SQL Tests, Test Cases, Run ID (first 8 characters) and ADB Status. | M |

### 5.10 QA generation pipeline (FR-PIP)

| ID | Requirement | Pri |
|---|---|---|
| FR-PIP-01 | For ETL specs the pipeline shall execute: analyze_spec, generate_sql_tests, safety_check, generate_test_cases, execute_on_adb, format_qa_report. | M |
| FR-PIP-02 | analyze_spec shall build the ETL category plan, produce analyst notes, missing information, assumptions and a validation plan. | M |
| FR-PIP-03 | generate_sql_tests shall build a deterministic SQL test plan (mapping ID plus rule ID, templated SQL), ask the LLM to complete the highest-priority items (up to 40) and merge both; plan items without SQL shall be reported as uncovered. | M |
| FR-PIP-04 | Every SQL test shall be safety-checked (Section 5.12) before use; blocked statements shall be listed in the report. | M |
| FR-PIP-05 | Functional test cases shall be generated when requirement context exists (stories, requirement text, UI context). ETL structured test cases shall be created from approved SQL tests and merged without duplicate IDs. | M |
| FR-PIP-06 | Functional-mode drafts shall run a reduced pipeline: functional test cases, optional KPI SQL tests (safety-checked), execution, and report. | M |
| FR-PIP-07 | KPI SQL tests shall be merged into the QA pack as test cases of type "KPI Data Validation" with requirement ID = KPI ID. | M |
| FR-PIP-08 | A run shall receive a unique run ID, and shall be logged to `runs/<run-id>.json` and, for ETL specs, to the metadata database. | M |
| FR-PIP-09 | The functional and SQL checkboxes shall filter the final result (functional off keeps only Data Validation cases; SQL off clears SQL tests). | M |

### 5.11 Functional test case generation (FR-TC)

| ID | Requirement | Pri |
|---|---|---|
| FR-TC-01 | Test cases shall be based only on supplied inputs; unknown names and behaviors shall be listed as missing information, never invented. | M |
| FR-TC-02 | Applicable categories shall include Positive, Negative, Boundary, UI, Validation, Accessibility, Error Handling, Security, Integration, Regression, Smoke, Edge Cases and End-to-End. | M |
| FR-TC-03 | Each test case shall contain: test case ID (format TC-MODULE-001), requirement ID, module, feature, scenario, description, preconditions, test data, priority (High/Medium/Low), severity (Critical/Major/Minor/Trivial), test type, positive or negative, automation candidate and reason, and execution steps. | M |
| FR-TC-04 | Each test case shall have at least three steps (smoke tests may have fewer). Each step shall have a step number, a user action, a specific measurable expected result, and empty actual result and status fields for the tester. | M |
| FR-TC-05 | The agent shall also return: scenario summary, requirement traceability matrix with honest coverage status, test coverage matrix counts, automation recommendations, missing information and assumptions. | M |
| FR-TC-06 | Counts in the coverage matrix and IDs in the artifacts shall be consistent with the generated test cases. | M |
| FR-TC-07 | Screenshot file names and any textual references shall be used as UI context; the agent shall state its limitation when screens are not readable. | M |

### 5.12 SQL generation, safety and execution (FR-SQL)

| ID | Requirement | Pri |
|---|---|---|
| FR-SQL-01 | Generated SQL shall be Databricks SQL, use fully qualified tables with the configured catalog, source schema and target schema, and be read-only. | M |
| FR-SQL-02 | Only statements beginning with SELECT or WITH are allowed. Any statement containing DELETE, UPDATE, DROP, TRUNCATE, ALTER, INSERT, MERGE, CREATE, GRANT, REVOKE, EXEC or EXECUTE shall be blocked. | M |
| FR-SQL-03 | Validation types shall include Record Count, NULL, Duplicate, Transformation, Data Reconciliation, Business Rule and Incremental Load. The default expected result is "0 rows returned (no validation failures)." | M |
| FR-SQL-04 | Execution on Databricks shall be opt-in. When disabled, or when credentials are dummy values, each test shall be marked SKIPPED with an explanatory note. | M |
| FR-SQL-05 | Queries that still contain `${...}` placeholders shall be SKIPPED at execution with a message to replace them. | M |
| FR-SQL-06 | Executed queries shall use a configurable timeout (default 120 seconds) and return a preview limited to a configurable row count (default 20). Truncated results shall be flagged. | M |
| FR-SQL-07 | Execution status values: PASS (zero rows expected and zero returned), FAIL (rows returned when zero expected, or truncated results on an expected-zero test), EXECUTED (no zero-row expectation), SKIPPED, ERROR (with message). | M |

### 5.13 Results and Exports (FR-RES, FR-EXP)

| ID | Requirement | Pri |
|---|---|---|
| FR-RES-01 | With no generated pack the page shall show "No QA pack generated yet." | M |
| FR-RES-02 | The page shall show metrics: SQL Tests, Test Cases, Run ID and Mode, and the export center. | M |
| FR-RES-03 | The page shall preview the QA report (Markdown), the Requirement Traceability Matrix, the Test Coverage Matrix and Databricks execution results as tables. | M |
| FR-RES-04 | A button shall open the Test Case Explorer. | M |
| FR-EXP-01 | The export center shall provide: QA Report (.md), Test Cases (.xlsx), Full QA Pack (.zip), RTM and Artifacts (.json) and SQL Tests (.json), each only when the content exists. | M |
| FR-EXP-02 | The Excel workbook shall contain a QA Test Cases sheet (22 columns including steps and SQL) and, when data exists, Scenario Summary, RTM, Coverage Matrix, Automation, Mapping Analysis and Mapping Gaps sheets. | M |
| FR-EXP-03 | The Markdown report shall contain: Run Summary, Scope, Analyst Notes, Missing Information, ETL Agent Coverage, Assumptions, KPI Logic Normalization, Mapping Analysis (VR coverage), Blocked Queries, Test Scenario Summary, Requirement Traceability Matrix, and execution evidence. | M |
| FR-EXP-04 | The ZIP shall contain run_summary.json, the report, the Excel file, etl_spec.json, test_case_artifacts.json and sql_execution_results.json, when each exists. | M |
| FR-EXP-05 | Mapping output shall be downloadable as JSON or Excel (Mapping Rows, Canonical Mappings, Analysis, Gaps, ETL Spec mapping, Pseudo Code). | M |
| FR-EXP-06 | Generated files shall overwrite previous outputs (`output/qa_validation_pack.md`, `output/qa_test_cases.xlsx`). | M |

### 5.14 Test Case Explorer (FR-TCX)

| ID | Requirement | Pri |
|---|---|---|
| FR-TCX-01 | If no pack exists the page shall show "Generate a QA pack first to explore test cases." | M |
| FR-TCX-02 | The page shall provide filters: Test type, Priority, and free-text Search across the whole test case. | M |
| FR-TCX-03 | A caption shall show "Showing N of M test cases". | M |
| FR-TCX-04 | Each case shall be an expander titled "<ID> \| <scenario>" and show requirement ID, module and feature, priority and severity, type, automation, description and a steps table (Step, Action, Expected) or a list of test steps. | M |
| FR-TCX-05 | Each case shall offer a "Copy test case JSON" download. | M |

### 5.15 Spec Library and Run History (FR-LIB, FR-HIS)

| ID | Requirement | Pri |
|---|---|---|
| FR-LIB-01 | Approved complete ETL specs shall be saved to a local SQLite database with name, version, content and timestamps; saving an existing name creates a new version. | M |
| FR-LIB-02 | The Spec Library shall list specs as expanders "<name> \| v<version> \| updated <time>", show the spec JSON, an Execute on Databricks checkbox, Re-run Validation and Download Spec JSON. | M |
| FR-LIB-03 | Re-run Validation shall run the pipeline for the stored spec, show a loading toast, save outputs per spec name, and navigate to Results. | M |
| FR-LIB-04 | With no specs the page shall show "No approved ETL specs yet." | M |
| FR-HIS-01 | Run History shall list up to 100 runs in a selector "<run id first 8> \| <spec> \| <time>" and default to the last selected run. | M |
| FR-HIS-02 | For the selected run the page shall show cards (Spec, SQL Tests, Test Cases, Run At), the export center (when the report still exists), a Run metadata expander (JSON) and a Report Preview. | M |
| FR-HIS-03 | With no runs the page shall show "No runs recorded yet." | M |

### 5.16 Background tasks and notifications (FR-BGT)

| ID | Requirement | Pri |
|---|---|---|
| FR-BGT-01 | A bell icon shall be fixed at the top right of every page. A badge shall show the count of running or queued tasks and pulse while a task is running. | M |
| FR-BGT-02 | Clicking the bell shall open a Background Tasks panel with: title, subtitle "Monitor your ongoing operations", a live label ("N tasks running" or "No active tasks"), a summary (Active, Completed, Failed) and a task list. | M |
| FR-BGT-03 | Each task card shall show an icon by kind, name, status chip (Running, Completed, Failed, Queued), description, last updated time, a progress bar and a trailing percentage, check or error icon. | M |
| FR-BGT-04 | Task actions: Details (expand started, updated, error, metadata), Retry (failed), Dismiss (completed), Cancel with a Confirm step (running). | M |
| FR-BGT-05 | The panel footer shall provide Clear completed and View all tasks (opens the Background Tasks page). | M |
| FR-BGT-06 | The panel shall close with the × button, a click outside the panel, or the Escape key. | M |
| FR-BGT-07 | While the panel is open or tasks are active, the bell and panel shall refresh every second. | M |
| FR-BGT-08 | The panel shall show an empty state "You're all caught up" when there are no tasks. | M |
| FR-BGT-09 | Long operations that run on the page (build draft, import stories, mapping generation, requirement or story analysis, re-run validation, workspace start) shall show a loading toast and, when finished, record a notification (completed or failed, with the error text) in the bell. The bell keeps the 30 most recent notifications. | M |
| FR-BGT-10 | Operations that run in true background threads (QA pack generation, KPI normalization) shall appear in the bell while running with estimated progress (approaching but not exceeding 92 percent until complete), then change to completed or failed. | M |
| FR-BGT-11 | The Background Tasks page shall show metrics (Running, Queued, Completed, Failed), a Clear completed button and a card per task with progress and actions (Retry, Dismiss) and error text. | M |
| FR-BGT-12 | Retrying a failed QA generation task shall clear the job and open Generate QA Pack. | S |

### 5.17 Settings and health (FR-SET)

| ID | Requirement | Pri |
|---|---|---|
| FR-SET-01 | Settings and Health shall list the connection status for Azure OpenAI, Azure DevOps and Azure Databricks with a detail caption. | M |
| FR-SET-02 | Test buttons shall verify Azure OpenAI (a one-word reply), Azure DevOps (organization and project), and Databricks configuration (host present or "credentials are not configured"). | M |
| FR-SET-03 | Environment notes shall state that credentials come from `.env`, secrets are never displayed in the UI and the page should be refreshed after changing credentials. | M |
| FR-SET-04 | A connection shall be reported "ready" only when its required variables are present and do not contain placeholder values (for example dummy, your-, xxxxxxxx). | M |

### 5.18 Activity log (FR-LOG)

| ID | Requirement | Pri |
|---|---|---|
| FR-LOG-01 | The application shall capture warnings, errors and its own progress messages in an in-memory buffer (maximum 600 records), excluding noisy third-party HTTP logs. | M |
| FR-LOG-02 | An Activity log button (sidebar and Generate page) shall open a popover with the log, an Errors only toggle, Refresh and Clear; the label shall show the number of issues. | M |

### 5.19 Command-line interface (FR-CLI)

| ID | Requirement | Pri |
|---|---|---|
| FR-CLI-01 | The CLI shall support: ado-test, ado-import (with --build), build (--from-ado, --use-samples, --mapping, --requirements), review, approve (--no-execute), validate (--spec, --no-execute), list-specs and list-drafts. | S |
| FR-CLI-02 | The web UI remains the supported primary interface. | M |

---

## 6. UI/UX Requirements

### 6.1 Design principles

1. **Guided, not cluttered.** One clear next action per page; the stepper and sidebar show where the user is.
2. **Human in control.** Nothing is generated without review and explicit approval.
3. **Transparent AI.** Gaps, assumptions, risks and rejection reasons are always visible.
4. **Never block the user.** Long operations run in the background or show progress, and the user can navigate away.
5. **Safe by default.** Databricks execution is off by default; destructive actions are explicit.
6. **Consistent and calm.** One dark theme, one component vocabulary, predictable spacing and motion.

### 6.2 Visual design system

| Aspect | Specification |
|---|---|
| Theme | Dark, Material 3 inspired. Streamlit base theme dark with custom CSS |
| Typeface | Google Sans Flex (weights 400 to 800) with Google Sans and Segoe UI fallback; monospace (Cascadia Code, Consolas) for code |
| Background | #0d1117 (app), #131920 (surface) |
| Containers | #0a0f14 (lowest), #141c26 (low), #1a2330 (default), #202c3c (high), #283446 (highest) |
| Text | #dde4ee primary, #92a1b5 muted |
| Outline | #3a4758, subtle #26333f |
| Primary | #38bdf8 (container #0c4369, on-container #d0eeff) |
| Secondary (success) | #4ade80 (container #143d22, on-container #b9f8d0) |
| Tertiary (accent) | #a78bfa (container #2e1b5e) |
| Error | #f87171 (container #5c1818) |
| Warning | #fbbf24 (container #3d2a07) |
| Corner radii | 8, 12, 16, 20, 24, 28 px and full pill (999 px) |
| Content width | Maximum 1300 px, centered |
| Motion | Quick 120 ms, normal 250 ms, emphasized 400 ms; spring and standard easings; reduced-motion media query disables animations |
| Iconography | Material Symbols (rounded) for task kinds and status; inline SVG for stepper checks and chevrons |

### 6.3 Global layout

```
+----------------------+------------------------------------------------------+
| Sidebar (left)       |  [eyebrow: QA Accelerator]                    [Bell] |
|  Brand + collapse    |  Page title (H1)                                     |
|  Navigation groups   |  Caption                                             |
|  Session card        |  Workflow stepper (workflow pages only)              |
|  Workflow progress   |  ---------------------------------------------------  |
|  Quick Import/Export |  Page content                                        |
|  Activity log        |                                                      |
|  Footer              |                                                      |
+----------------------+------------------------------------------------------+
```

- A full-screen loading overlay with a spinning ring and the word "Loading" appears during initial application start (blurred, translucent background).
- The bell is fixed at the top-right corner on every page (top 12 px, right 16 px, 48 px circular target).

### 6.4 Sidebar specification

| Element | Behavior |
|---|---|
| Brand | "QA" badge, eyebrow "QA Platform", title "Accelerator", tagline "AI-powered test case and ETL validation"; a collapse control ("«") |
| Navigation groups | **Workflow**: Home, Import, Build Spec, Review, Generate, Exports. **Explore**: Test Cases, Spec Library, History. **System**: Tasks, Settings |
| Nav buttons | Full-width; the active page uses the primary button style, others secondary; clicking navigates and reruns |
| Session card | Draft (first 8 characters of the ID or "None yet"), Mode, Last run ID, Test cases count, and QA pack state (Running in background, Failed, Ready to review) |
| Workflow progress | Five steps (Import stories, Build spec, Review draft, Generate pack, Export results); states done (check mark), active (highlighted), pending (muted); all pending on non-workflow pages |
| Quick actions | Import and Export buttons side by side |
| Activity log | Popover button with issue count |
| Footer | "Insight Studio · ETL QA · v1.0" |

### 6.5 Page header and stepper

- Every page starts with a small eyebrow ("QA Accelerator"), an H1 title and a one-line caption.
- The five-step stepper (Import, Build Spec, Review, Generate, Export) appears on the Import, Build ETL Spec, Review Draft, Generate QA Pack and Results and Exports pages. The current step has a pulsing ring, completed steps show a green check, upcoming steps are muted. The stepper scrolls horizontally on narrow screens.

### 6.6 Page-by-page UI specification

**Home**
- Row of three connection cards (equal width, wrap on narrow screens) with a colored left border and a status badge with a leading dot.
- Four summary cards in an auto-fit grid (minimum 200 px each) with accent colors.
- "Quick Actions" section title with three equal-width buttons.
- "Recent Runs" table (Spec, Run At, Tests badge) in a rounded table container.
- "Latest QA Pack" with download buttons when available.

**Import**
- Tabs: Azure DevOps, File Upload, Manual Entry.
- Azure DevOps tab: two-column organization and project inputs, work item IDs input, spec name, helper caption, a three-button row (Test Connection, Import User Stories primary, Start new import), an info box with the latest import, story cards each with a circular ✕ remove control, a spacer, and a three-column action row (Download Requirements, Download Stories JSON, Build Draft from this Import primary).
- File Upload tab: explanatory caption, three uploaders (requirement, mapping, screenshots), spec name, Save & continue to Build Spec (primary).
- Manual Entry tab: title input, description and acceptance criteria text areas (120 px), business rules text area (80 px), screenshots uploader, spec name, Create Functional Draft (primary).
**Build ETL Spec**
- Stepper, horizontal radio for input source, optional caption about the mapping in use, spec name, workflow mode dropdown, screenshots uploader, mapping override uploader, ETL spec JSON uploader, divider, KPI Logic Document section, divider, Generate Draft (primary), and the Latest ADO Import preview (divider, subheader, detected mode info box).

**KPI Logic Document section** (shared component)
- Subheader, caption, uploader (nine formats), optional info or error banner for background state, and a three-column button row: Process and Normalize SQL for Databricks (primary, full column width), Export normalized KPI document (.xlsx) (visible only with results), and an empty spacer.
- Results: three metric tiles, expanders (Normalization notes, Normalized SQL preview with code blocks, Rejected queries).

**Review Draft**
- Stepper, pending-draft selector, info banner, two columns (Requirement Analysis; Gaps and Assumptions expander), User Stories cards, ETL Spec JSON area, STM summary or mapping preview, LLM mapping output, Mapping Analysis, Download popover, divider, KPI section, three equal action buttons (Save Draft, Delete Draft, Proceed to Generate primary).

**Generate QA Pack**
- Stepper, info banner, three checkboxes with caption, mapping download, running-state info banner, Approve and Generate QA Pack (primary, disabled while running), error messages with Activity log button, Last Run Summary (four metrics).

**Results and Exports**
- Stepper, four metrics, Downloads subheader with three columns (report, Excel, ZIP) and further download buttons, divider, QA Report Preview (rendered Markdown), RTM table, Coverage Matrix table, Databricks Execution Results table, and Open Test Case Explorer.

**Test Case Explorer**
- Three-column filter row (Test type, Priority, Search), result count caption, one expander per case with details, steps table and JSON download.

**Spec Library**
- Expander per spec: JSON viewer, execute checkbox, two columns (Re-run Validation, Download Spec JSON).

**Run History**
- Run selector, four equal summary cards with line-break-friendly text for long names, export center, metadata expander and report preview.

**Background Tasks**
- Four metrics, Clear completed, bordered task cards (icon, name with status chip, description, started time, percentage, progress bar, Retry or Dismiss, error banner).

**Settings and Health**
- Connection status list with icons, three test buttons, environment notes.

### 6.7 Global UI components

| Component | Specification |
|---|---|
| Connection card | Rounded 28 px card, 3 px colored left border, label (uppercase), status badge (pill with dot), monospace detail; lifts on hover |
| Summary card | Title and large value, colored left border; equal-height grid variant for history |
| Story card | Collapsible row: ID chip "US-<id>", title, type badge, state and tag badges, chevron that rotates when open; body with Description and Acceptance Criteria sections |
| Stepper | See Section 6.5 |
| Tables and dataframes | Rounded border, subtle shadow, horizontally scrollable |
| Buttons | Rounded pill buttons; primary (filled sky blue tonal), secondary (neutral); full width inside columns; disabled state visibly muted |
| Download popover | Compact button "Download" opening a small panel with JSON and Excel buttons |
| Inputs and uploaders | Dashed outline upload areas with rounded corners, hover highlight, accepted format and 200 MB per file caption |
| Alerts | Success (green), error (red), warning (amber), info (blue) with a colored left border |
| Metrics | Large number with small label |
| Code blocks | Monospace, dark, scrollable; SQL highlighted as SQL |
| Scrollbars | Thin (6 px), themed |

### 6.8 Toast notifications

| Rule | Specification |
|---|---|
| Purpose | Confirm progress and results of long operations without blocking the page |
| Loading toast | Shows a clock icon and the operation message (for example "Building draft...") and stays visible while work runs, where the Streamlit version supports persistent toasts; otherwise it is a normal short toast |
| Result toast | Updates to a check mark with the done message, or a warning icon with "Something went wrong." |
| Bell record | Every completed or failed toast operation is also stored in the bell as a notification so it can be reviewed later |
| Background completion | QA pack and KPI normalization show a toast when the job ends (success or failure), wherever the user is |

### 6.9 Background task center (bell) UX

- Closed state: bell icon with an optional numeric badge (active tasks).
- Open state: floating panel under the bell. Header with title, subtitle and live status; summary chips (Active, Completed, Failed); scrollable task list; footer actions.
- Progress visual: determinate bar with shimmer for running tasks, indeterminate bar when progress is unknown, green full bar when completed, red bar when failed, empty bar when queued.
- Status chips use color and text (not color alone).
- The panel never traps the user: Escape, outside click and the × button all close it.

### 6.10 Interaction patterns

| Pattern | Rule |
|---|---|
| Navigation | Sidebar buttons and in-page primary buttons set the current page; the sidebar and stepper update immediately |
| Progressive disclosure | Details (notes, SQL previews, pseudo-code, metadata) live in expanders; defaults are collapsed |
| Confirmation | Destructive or discarding actions (Cancel a running task) require a Confirm step; Delete Draft acts immediately and reports the result |
| Disabled actions | Buttons that cannot run (a job is already running) are disabled and an adjacent message explains why |
| Persistence | Uploaded files and draft context are saved so that navigation does not lose work |
| Feedback | Every action ends with a visible result (toast, success banner, error banner or navigation) |

### 6.11 State catalogue

| State | Treatment |
|---|---|
| Empty | Friendly info message that names the next step (for example "No runs yet. Import a user story and generate a QA pack.") |
| Loading | Toast with message; startup overlay; progress bar in the bell |
| Success | Green banner or toast, plus navigation to the next stage where appropriate |
| Warning | Amber banner for gaps, review-required mappings and skipped SQL |
| Error | Red banner with the exact message; Activity log button for details |
| Disabled | Muted button with explanatory caption |
| Blocked | Rejected KPI queries and blocked SQL listed with reasons |

### 6.12 Content and tone

- Plain, direct English; sentences begin with the user's outcome.
- Buttons use verbs ("Generate Draft", "Approve and Generate QA Pack").
- Error messages state what happened and what to do next.
- Technical identifiers (draft IDs, run IDs) are shortened to eight characters in tables and selectors and shown in full where precision is needed (Review Draft banner).

### 6.13 Accessibility

| ID | Requirement |
|---|---|
| UX-A11Y-01 | Text contrast shall meet WCAG 2.1 AA on the dark theme. |
| UX-A11Y-02 | Status shall never be conveyed by color alone; chips and badges include text and icons. |
| UX-A11Y-03 | The bell panel shall use dialog semantics with an accessible label; progress bars expose role, value, minimum and maximum; the page loader uses a polite live region. |
| UX-A11Y-04 | All interactive controls shall be reachable by keyboard and show a visible focus ring. |
| UX-A11Y-05 | Motion shall be reduced when the user prefers reduced motion. |

### 6.14 Responsiveness

- Designed for desktop browsers; content is capped at 1300 px.
- Grids (connection cards, summary cards) wrap automatically; the stepper scrolls horizontally; long identifiers use soft line breaks.
- Browser zoom (Ctrl and minus) is the supported way to fit large layouts on small displays.

---

## 7. Data Requirements

### 7.1 Input data

| Input | Formats | Notes |
|---|---|---|
| Azure DevOps stories | REST API | Title, description, acceptance criteria, tags, state, area and iteration paths, attachments |
| Requirement document | TXT, DOCX, PDF | Text is extracted; used for analysis and traceability |
| Mapping document | XLSX, XLSM, CSV, DOCX (STM) | CoE template columns; Word STM tables and pseudo-code |
| ETL spec JSON | JSON | Must contain source table, target table and primary key to be complete |
| KPI logic document | XLSX, XLSM, CSV, SQL, TXT, DOCX, PDF, MD, JSON | Developer SQL for UI KPI validation |
| UI screenshots | PNG, JPG, JPEG, WEBP | 200 MB per file; file names and references become UI context |
| Platform metadata | JSON | Optional types, keys and nullability |

### 7.2 ETL spec data model

| Field | Type | Description |
|---|---|---|
| database_dialect | text | Default "Databricks SQL" |
| catalog | text | Default "main" |
| source_table | text, required | Qualified source table |
| target_table | text, required | Qualified target table |
| primary_key | text, required | Key column(s) |
| load_type | full, incremental, snapshot, cdc | Default full |
| incremental_column, watermark_column | text | For incremental and CDC loads |
| source_to_target_mapping | list | source_column, target_column, transformation |
| transformation_rules, business_rules | text list | |
| not_null_columns | text list | |
| additional_notes | text | |

A spec is "complete" only when source_table, target_table and primary_key are all non-empty.

### 7.3 Mapping analysis data model (per mapping)

mapping_id, source (database, schema, table, column, data type), target (same), transformation (type, logic), business rule, nullable, primary key, validation_rules (rule_id, type, description, priority), risk, gaps, requires_review.

### 7.4 Test case data model

Test Case ID, Requirement ID, Module, Feature, Test Scenario, Test Case Description, Preconditions, Test Data, Priority, Severity, Test Type, Positive/Negative, Automation Candidate, Automation Reason, Execution Steps (step number, user action, expected result, actual result, status), Expected Result, SQL Query, Source Table, Target Table, Spec Version, Mapping ID, Rule ID.

### 7.5 SQL test data model

test_id, test_scenario, validation_type, sql_query, expected_result, priority, mapping_id, rule_id; KPI tests also carry kpi_id, kpi_name and module.

### 7.6 KPI normalization data model

Per query: kpi_id, kpi_name, module, original_sql, normalized_sql, runnable, fixes_applied, issues_remaining, expected_result, priority. Per result: queries, tests, rejected_queries, global_notes, runnable_count, total_count, source path, raw JSON path, normalized JSON path.

### 7.7 Storage and persistence

| Data | Location |
|---|---|
| Drafts | `review/drafts/<draft-id>.json` |
| Approved specs and run summaries | `metadata/qa_accelerator.db` (SQLite) |
| Run logs | `runs/<run-id>.json` |
| ADO imports | `imports/ado/<import-id>/` and `imports/ado/latest.json` |
| Uploads | `uploads/` (KPI results in `uploads/kpi_logic/`) |
| Outputs | `output/qa_validation_pack.md`, `output/qa_test_cases.xlsx` |

Runtime folders are excluded from source control. Session state (current draft, last result, background tasks) is held in the Streamlit session.

---

## 8. Integration Requirements

### 8.1 Azure OpenAI

- Required. Configured by endpoint, API key, deployment (default gpt-5.1) and API version.
- Temperature 0 and the Responses API are used for reproducibility.
- Responses must be valid JSON objects; a failed parse is retried up to two more times with a corrective instruction.
- Placeholder or dummy credentials shall produce a clear configuration error.

### 8.2 Azure DevOps

- Authentication by personal access token with Work Items (Read).
- REST API version 7.1: list projects (connection test), WIQL query, work item batch retrieval with relations, attachment download.
- Query filters: explicit IDs, or project, work item types (default User Story), area path, iteration path, excluding Removed items.
- Configurable timeout (default 60 seconds) and story limit (default 25).

### 8.3 Azure Databricks

- Optional and used only for execution. SQL warehouse connection by server hostname, HTTP path and access token.
- Read-only: the client independently asserts that a statement is SELECT-only before executing.
- Defaults: catalog main, source schema stg, target schema dw, timeout 120 seconds, 20 preview rows.

---

## 9. AI Agent Requirements

| Agent | Responsibility | Key behavior |
|---|---|---|
| Requirement Agent | Facts, business rules and gaps from requirements | Returns structured summary; never invents tables or rules |
| Mapping Agent | ETL spec, canonical mappings, entity output | Works per target table; fills primary keys, load type, rules; reports missing information |
| KPI SQL Agent | Normalizes developer KPI SQL | Read-only, Databricks syntax, preserves intent and IDs, documents fixes and issues, flags non-runnable queries |
| SQL Agent | Validation SQL | SELECT-only, driven by mapping ID and rule ID ("what to test" comes from mapping, "how" from the agent) |
| Test Case Agent | Functional and data test cases | Traceable, measurable steps; scenario, RTM, coverage and automation artifacts |
| Reporting Agent | Markdown QA pack | Run summary, scope, gaps, coverage, KPI normalization, mapping analysis, blocked queries, execution evidence |

Common rules: temperature 0, JSON-only output, no fabricated tables, columns, catalogs or business logic, and explicit listing of gaps and assumptions.

---

## 10. Non-Functional Requirements

### 10.1 Performance and responsiveness

| ID | Requirement |
|---|---|
| NFR-PERF-01 | Page navigation shall respond within one second on local data. |
| NFR-PERF-02 | Operations that call the LLM shall never block navigation: they either run in the background or show a toast; users shall always see activity feedback. |
| NFR-PERF-03 | KPI normalization shall process independent batches concurrently (default 4 parallel batches). A 6 to 8 query document should complete in about the time of one LLM call (typically under 30 seconds); large documents (about 100 queries) are expected to take several minutes. |
| NFR-PERF-04 | Draft generation from a large mapping (hundreds of rows, many target tables) is dominated by one LLM call per target table and may take several minutes; the user shall be informed that the operation is in progress. |
| NFR-PERF-05 | The bell shall refresh at one-second intervals only while a task is active or the panel is open. |

### 10.2 Reliability

| ID | Requirement |
|---|---|
| NFR-REL-01 | A failure in one entity or batch shall not abort the whole run; it is recorded as missing information or a rejected query. |
| NFR-REL-02 | Invalid LLM JSON shall be retried (up to two retries). |
| NFR-REL-03 | Locked output files shall produce a clear message rather than a crash. |
| NFR-REL-04 | Streamlit reruns shall not duplicate background jobs; a second concurrent generation or normalization shall be refused with a message. |
| NFR-REL-05 | Source edits shall refresh cached modules so that code changes take effect without stale behavior. |

### 10.3 Security and privacy

| ID | Requirement |
|---|---|
| NFR-SEC-01 | Secrets (API keys, PAT, Databricks token) shall be loaded only from `.env` and never displayed in the UI or written to logs and reports. |
| NFR-SEC-02 | All SQL shall be read-only. Mutating keywords shall be blocked at generation time and again at execution time. |
| NFR-SEC-03 | Databricks execution shall be opt-in per run. |
| NFR-SEC-04 | The `.env` file and runtime data folders shall be excluded from source control. |
| NFR-SEC-05 | User-provided text rendered as HTML shall be escaped. |
| NFR-SEC-06 | Personally identifiable data in uploaded documents is sent to Azure OpenAI; deployments shall use an approved, tenant-controlled Azure OpenAI resource. |

### 10.4 Usability

| ID | Requirement |
|---|---|
| NFR-USE-01 | A first-time user shall be able to complete the sample demo in under five minutes without documentation. |
| NFR-USE-02 | Each page shall state its purpose in the header caption and offer a single obvious next action. |
| NFR-USE-03 | Errors shall be written in plain language and name the corrective action. |

### 10.5 Maintainability and testability

| ID | Requirement |
|---|---|
| NFR-MNT-01 | The code shall be organized by layer: UI (app), agents, graph, mapping engine, parsers, integrations, exporters, models, prompts, services, utilities. |
| NFR-MNT-02 | An automated test suite shall cover parsers, mapping analysis, SQL safety, agents, exporters, stores and background task registry (73 tests at the time of writing). |
| NFR-MNT-03 | Prompts shall live in dedicated modules and be tunable without code changes elsewhere. |

### 10.6 Compatibility

- Browsers: current Chrome and Edge (primary), Firefox and Safari (best effort).
- Operating system: Windows (PowerShell scripts setup.ps1 and run_ui.ps1); the Python code is cross-platform.
- Streamlit 1.40 or later; persistent toasts require a Streamlit version that supports the toast duration option, with a graceful fallback.

### 10.7 Observability

- In-app Activity log and per-run JSON logs; the QA report includes execution evidence; failures are logged with stack traces.

---

## 11. Configuration Requirements

| Variable | Purpose | Required |
|---|---|---|
| AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY | LLM access | Yes |
| AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_MODEL | Model selection (defaults gpt-5.1) | Yes (defaults available) |
| AZURE_DEVOPS_ORG, AZURE_DEVOPS_PROJECT, AZURE_DEVOPS_PAT | Story import | For ADO workflow |
| AZURE_DEVOPS_AREA_PATH, AZURE_DEVOPS_ITERATION_PATH, AZURE_DEVOPS_WORK_ITEM_IDS, AZURE_DEVOPS_WORK_ITEM_TYPES, AZURE_DEVOPS_MAX_STORIES, AZURE_DEVOPS_TIMEOUT_SECONDS | Query filters and limits | No |
| DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_ACCESS_TOKEN | Warehouse access | Only for execution |
| DATABRICKS_CATALOG, DATABRICKS_SOURCE_SCHEMA, DATABRICKS_TARGET_SCHEMA | Naming context (main, stg, dw) | No |
| DATABRICKS_QUERY_TIMEOUT_SECONDS, DATABRICKS_PREVIEW_ROWS | Execution limits (120, 20) | No |
| FABRIC_METADATA_PATH | Platform metadata JSON | No |
| KPI_NORMALIZATION_WORKERS | Parallel KPI batches (default 4) | No |

---

## 12. Deployment and Operations

| Topic | Requirement |
|---|---|
| Setup | `setup.ps1` creates the virtual environment and installs dependencies; `.env.example` is copied to `.env` |
| Run | `run_ui.ps1` starts Streamlit (typically http://localhost:8501) |
| Dependencies | langgraph, langchain, langchain-openai, pydantic, python-dotenv, databricks-sql-connector, openpyxl, python-docx, pypdf, streamlit, pytest |
| Samples | Bundled sample BRD, mapping (XLSX and DOCX), ETL spec JSON, KPI queries, mapping template, platform metadata |
| Tests | `python -m pytest` |
| Server mode | Headless; usage statistics disabled |

---

## 13. Acceptance Criteria (Key Scenarios)

| ID | Scenario | Expected result |
|---|---|---|
| AC-01 | Run Sample Demo from Home | A draft is created and Review Draft opens with mapping analysis |
| AC-02 | Import ADO story without work item IDs | Error "Enter one or more Work Item IDs..." and no import |
| AC-03 | Upload a mapping XLSX and build a draft | ETL draft with mapping analysis, VR rules, risk and gaps |
| AC-04 | Upload a Word STM document | Entities and pseudo-code are extracted and a normalized Excel is created |
| AC-05 | Manual story creation | Functional draft is created and the ETL section is replaced by the functional explanation |
| AC-06 | Normalize a KPI document with valid and invalid queries | Valid queries are Databricks-ready; queries with unresolved placeholders or unsafe SQL are listed as Rejected; metrics and export match |
| AC-07 | KPI normalization while navigating away | Task is visible in the bell with progress; a toast confirms completion; results are available when returning |
| AC-08 | Export normalized KPI workbook | XLSX contains Summary, Normalized KPI SQL and (when applicable) Rejected Queries and Normalization Notes |
| AC-09 | Approve and generate with Databricks execution off | Tests are generated, execution status is SKIPPED, outputs are exported |
| AC-10 | Attempt a second generation while one runs | Button is disabled with an explanatory message |
| AC-11 | Generate while the Excel output is open | Clear message to close the file |
| AC-12 | Results and Exports | Report preview, RTM, coverage, downloads (MD, XLSX, ZIP, JSON) all work |
| AC-13 | Test Case Explorer filtering | Filters and search narrow the list and the count caption updates |
| AC-14 | Spec Library re-run | New run appears in Run History and Results |
| AC-15 | Bell behavior | Opens and closes by button, outside click and Escape; Clear completed and Dismiss work |
| AC-16 | Toast loader | A loading toast appears for long actions; a completed or failed notification is added to the bell |
| AC-17 | SQL safety | A statement containing DELETE, UPDATE, DROP and so on is blocked and listed under Blocked Queries |
| AC-18 | Settings tests | Each connection test reports success or the exact error |

### Requirement traceability (summary)

| Objective | Requirements |
|---|---|
| OBJ-1 Speed | FR-IMP, FR-BLD, FR-GEN, FR-PIP, NFR-PERF |
| OBJ-2 Gaps and risk | FR-ANL, FR-REV-04, FR-REV-09 |
| OBJ-3 Safe SQL | FR-SQL, FR-KPI-06 to FR-KPI-08, NFR-SEC-02 |
| OBJ-4 Functional cases | FR-TC, FR-TCX |
| OBJ-5 Human control | FR-REV, FR-GEN-05 |
| OBJ-6 Status and notifications | FR-BGT, Section 6.8 and 6.9 |
| OBJ-7 Output formats | FR-EXP, FR-RES |

---

## 14. Risks, Constraints and Known Limitations

| Area | Description |
|---|---|
| LLM latency and cost | Draft generation and KPI normalization depend on LLM response time; large inputs take minutes |
| LLM variability | Wording and fixes can vary between runs even at temperature 0; human review is required |
| Single-user design | State lives in the browser session and local files; no authentication or multi-user isolation |
| Background threads | Jobs run in-process; closing the app or browser session stops them; cancelling hides the result but does not interrupt the running call |
| Output overwriting | Latest pack replaces the previous Excel and Markdown outputs |
| File locking | An open Excel output blocks regeneration |
| Mapping quality | Poorly structured mapping documents produce many gaps; table boundaries must be explicit |
| Read-only scope | The product cannot fix data or pipelines; it only validates |
| Toast persistence | Persistent loading toasts require a recent Streamlit version |

---

## 15. Glossary of Statuses

| Status | Where | Meaning |
|---|---|---|
| pending_review | Draft | Awaiting review and approval |
| approved | Draft | Approved and used for generation |
| Running, Queued, Completed, Failed | Background task | Lifecycle of a task |
| Ready, Missing, Error | Connection | Configuration or connectivity state |
| PASS, FAIL, EXECUTED, SKIPPED, ERROR | SQL execution | Outcome of a validation query |
| Covered, Partially Covered, Not Covered | Traceability | Requirement coverage |
| Low, Medium, High, Very High | Mapping risk | Review priority |

---

## 16. Recommended Enhancements (Future)

| Priority | Enhancement |
|---|---|
| High | Real streaming progress for draft generation (per target table) in the bell, and run the remaining page-bound operations as background jobs |
| High | Parallelize per-table mapping output generation to shorten large mapping runs |
| High | Time-stamped, versioned outputs and an output archive |
| Medium | Push generated test cases to Azure DevOps Test Plans |
| Medium | Authentication, roles and multi-user workspaces |
| Medium | Side-by-side comparison of original and normalized KPI SQL, and in-app editing of rejected queries followed by re-normalization |
| Medium | Notification read and unread state with a bell dot |
| Low | Light theme, localization and responsive layouts for tablets |
| Low | Test case import and export to common test management tools |

---

## Appendix A — Validation Rule Library (VR01 to VR26)

| Rule | Type | Title | Default priority |
|---|---|---|---|
| VR01 | RECORD | Record existence | High |
| VR02 | NULL | NULL handling | High |
| VR03 | DUPLICATE | Duplicate and uniqueness | High |
| VR04 | DATATYPE | Data type compatibility | Medium |
| VR05 | LENGTH | Length | Medium |
| VR06 | PRECISION | Precision and scale | Medium |
| VR07 | FORMAT | Format | Medium |
| VR10 | TRANSFORMATION | Direct mapping | High |
| VR11 | TRANSFORMATION | Calculation | High |
| VR12 | TRANSFORMATION | String transformation | High |
| VR13 | TRANSFORMATION | Date transformation | High |
| VR14 | TRANSFORMATION | Conditional logic | High |
| VR15 | LOOKUP | Lookup | High |
| VR16 | JOIN | Join keys and cardinality | High |
| VR17 | AGGREGATION | Aggregation | High |
| VR18 | DEFAULT | Default value | Medium |
| VR19 | FILTER | Filter include and exclude | Medium |
| VR20 | LOAD | Full load | Medium |
| VR21 | LOAD | Incremental load | High |
| VR22 | LOAD | CDC | High |
| VR23 | SCD | SCD Type 1 | High |
| VR24 | SCD | SCD Type 2 | High |
| VR25 | LATE_ARRIVING | Late arriving data | Medium |
| VR26 | REJECT | Reject records | Medium |

Transformation type to rules:

| Transformation type | Rules assigned |
|---|---|
| DIRECT | VR10, VR02, VR04, VR05 |
| STRING_TRANSFORMATION | VR12, VR02, VR05 |
| DATE_TRANSFORMATION | VR13, VR02, VR07 |
| DEFAULT_VALUE | VR18, VR02 |
| CONDITIONAL | VR14, VR02 |
| CALCULATION | VR11, VR02, VR06 |
| DATATYPE_CONVERSION | VR04, VR07, VR02 |
| LOOKUP | VR15, VR02, VR03 |
| JOIN | VR16, VR03, VR02 |
| AGGREGATION | VR17, VR06 |
| SCD | VR23, VR24, VR02 |
| FILTER | VR19 |
| COMPLEX_SQL | VR16, VR15, VR11, VR02 |

All mappings also receive VR01. Non-nullable columns add VR02 (High); key or unique columns add VR03; compatible type pairs add VR04 and, depending on target type, VR05 or VR06; format-related business rules add VR07; reject or late-arriving rules add VR26 and VR25.

## Appendix B — Risk Matrix

| Transformation type | Base risk |
|---|---|
| DIRECT, STRING_TRANSFORMATION, DATE_TRANSFORMATION | Low |
| DEFAULT_VALUE, CONDITIONAL, FILTER | Medium |
| CALCULATION, DATATYPE_CONVERSION, LOOKUP, JOIN, AGGREGATION, SCD | High |
| COMPLEX_SQL | Very High |

Adjustments: a data type mismatch or complex logic raises the risk by one level; any "missing ..." gap raises Low to Medium; mandatory, unique or key columns raise Low to Medium.

## Appendix C — ETL Test Coverage Categories

| Category | Description | Covered when |
|---|---|---|
| Schema validation | Column names, data types, missing or extra columns | Mapping columns available |
| Source-target reconciliation | Record counts and matching records | Source and target tables defined |
| Data quality | NULLs, duplicates, key violations | Mapping rules available |
| Transformation validation | Joins, filters, aggregations, calculated columns | Mapping has transformation types |
| Business-rule validation | Eligibility, balances, classifications | Business rules in spec or mapping |
| Incremental-load testing | Inserts, updates, deletes, watermarks, reruns | Load type incremental or CDC |
| SCD testing | Type 1 and Type 2 history | SCD logic found |
| Negative and boundary testing | Invalid values, empty inputs, date boundaries | Mapping available |
| Regression testing | Approved rules against new versions | Approved spec or baseline available |
| Lineage testing | Source-to-target paths | Mapping available |

## Appendix D — Sample File Inventory

| File | Purpose |
|---|---|
| samples/requirements/sample_brd.txt, sample_brd.docx | Sample business requirement document |
| samples/mappings/sample_mapping.xlsx | Sample mapping with full CoE headers |
| samples/mappings/sample_stm_mapping.docx | Sample Word STM document |
| samples/mappings/databricks_catalog_mapping.xlsx | Mapping exported from Unity Catalog |
| samples/templates/mapping_template.xlsx | Empty mapping template |
| samples/specs/sample_etl_spec.json | Direct JSON spec |
| samples/kpi_logic/sample_kpi_queries.sql, .xlsx | Sample KPI SQL |
| samples/metadata/fabric_columns.json | Platform column metadata |

## Appendix E — Representative User Messages

| Context | Message |
|---|---|
| Missing work item IDs | Enter one or more Work Item IDs. An empty field does not reuse a previous story. |
| ADO connection | Connected to <organization>/<project> |
| No draft | No draft selected. Import or build a draft first. |
| Draft saved | Draft saved. |
| KPI upload missing | Upload a KPI logic document first. |
| KPI running | Normalizing KPI SQL in the background. Track progress from the Background Tasks bell. |
| Second generation | A QA pack generation is already running. |
| Excel locked | Could not write output files. Close output/qa_test_cases.xlsx in Excel if it is open, then try again. |
| Functional SQL skipped | SQL validation is skipped for functional-only stories without a KPI logic document. |
| No results | No QA pack generated yet. |
| Empty bell | You're all caught up |
| LLM config | Azure OpenAI dummy values detected. Update AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env with a real deployment. |

---

*End of document.*
