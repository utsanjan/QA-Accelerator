import json
import logging

from src.config import adb_runtime_context, get_databricks_settings
from src.agents.etl_agent import build_etl_test_plan
from src.graph.state import AgentState, QueryExecution, ValidationTest
from src.integrations.databricks_client import execute_select
from src.mapping.sql_test_plan import (
    build_sql_test_plan,
    compact_mapping_context,
    merge_plan_with_llm_tests,
    plan_for_llm,
)
from src.prompts import ANALYZE_PROMPT, GENERATE_TESTS_PROMPT, SQL_AGENT_SYSTEM_PROMPT
from src.utils.llm_json import coerce_str_list, coerce_text, invoke_llm_json
from src.utils.sql_safety import has_unresolved_placeholders, validate_sql_test


logger = logging.getLogger(__name__)


def _llm_json(prompt: str) -> dict:
    return invoke_llm_json(prompt, system_prompt=SQL_AGENT_SYSTEM_PROMPT)


def _spec_json(state: AgentState) -> str:
    spec = dict(state.get("etl_spec") or {})
    spec.setdefault("database_dialect", "Databricks SQL")
    spec.setdefault("catalog", adb_runtime_context()["catalog"])
    return json.dumps(spec, indent=2)


def _mapping_prompt_fields(state: AgentState) -> tuple[str, str, list[dict]]:
    settings = adb_runtime_context()
    spec = dict(state.get("etl_spec") or {})
    catalog = str(spec.get("catalog") or settings.get("catalog") or "main")
    plan = build_sql_test_plan(state.get("mapping_analysis") or {}, spec, catalog=catalog)
    mapping_context = json.dumps(compact_mapping_context(state.get("mapping_analysis") or {}), indent=2)
    sql_test_plan = json.dumps(plan_for_llm(plan) if plan else [], indent=2)
    return mapping_context, sql_test_plan, plan


def analyze_spec(state: AgentState) -> AgentState:
    mapping_context, sql_test_plan, plan = _mapping_prompt_fields(state)
    etl_agent_plan = build_etl_test_plan(
        state.get("etl_spec") or {},
        state.get("mapping_analysis") or {},
    )
    logger.info("Analyzing ETL spec (%d Mapping Agent plan items)...", len(plan))
    payload = _llm_json(
        ANALYZE_PROMPT.format(
            etl_spec=_spec_json(state),
            adb_context=json.dumps(adb_runtime_context(), indent=2),
            mapping_context=mapping_context,
            sql_test_plan=sql_test_plan,
            etl_agent_plan=json.dumps(etl_agent_plan, indent=2),
        )
    )
    validation_plan = coerce_str_list(payload.get("validation_plan"))
    if plan and not validation_plan:
        validation_plan = [
            f"{item['mapping_id']}/{item['rule_id']}: {item['what_to_test']}" for item in plan[:25]
        ]
    analysis = state.get("mapping_analysis") or {}
    missing = coerce_str_list(payload.get("missing_information")) + coerce_str_list(analysis.get("summary_gaps"))
    logger.info("Spec analysis complete: %d gap(s), %d plan step(s)", len(missing), len(validation_plan))
    return {
        "analyst_notes": coerce_text(payload.get("analyst_notes")),
        "missing_information": list(dict.fromkeys(missing)),
        "assumptions": coerce_str_list(payload.get("assumptions")),
        "validation_plan": validation_plan,
        "sql_test_plan": plan,
        "etl_agent_plan": etl_agent_plan,
    }


def generate_sql_tests(state: AgentState) -> AgentState:
    mapping_context, sql_test_plan_json, plan = _mapping_prompt_fields(state)
    if state.get("sql_test_plan"):
        plan = list(state.get("sql_test_plan") or [])
        sql_test_plan_json = json.dumps(plan_for_llm(plan) if plan else [], indent=2)

    logger.info("Generating validation SQL...")
    payload = _llm_json(
        GENERATE_TESTS_PROMPT.format(
            etl_spec=_spec_json(state),
            adb_context=json.dumps(adb_runtime_context(), indent=2),
            analyst_notes=state.get("analyst_notes", ""),
            missing_information=json.dumps(state.get("missing_information", []), indent=2),
            assumptions=json.dumps(state.get("assumptions", []), indent=2),
            validation_plan=json.dumps(state.get("validation_plan", []), indent=2),
            mapping_context=mapping_context,
            sql_test_plan=sql_test_plan_json,
            etl_agent_plan=json.dumps(state.get("etl_agent_plan") or [], indent=2),
        )
    )
    llm_tests = payload.get("tests") or []
    if plan:
        tests, uncovered = merge_plan_with_llm_tests(plan, llm_tests)
    else:
        tests = llm_tests
        uncovered = []

    missing = list(
        dict.fromkeys(
            coerce_str_list(state.get("missing_information"))
            + coerce_str_list(payload.get("missing_information"))
            + uncovered
        )
    )
    assumptions = list(
        dict.fromkeys(coerce_str_list(state.get("assumptions")) + coerce_str_list(payload.get("assumptions")))
    )
    logger.info("Generated %d SQL test(s); %d plan item(s) had no SQL", len(tests), len(uncovered))
    return {
        "tests": tests,
        "missing_information": missing,
        "assumptions": assumptions,
        "sql_test_plan": plan,
    }


def safety_check(state: AgentState) -> AgentState:
    approved: list[ValidationTest] = []
    rejected: list[str] = []
    for test in state.get("tests") or []:
        ok, reason = validate_sql_test(test)
        if ok:
            approved.append(test)
        else:
            rejected.append(reason)
    logger.info("Safety check: %d approved, %d blocked", len(approved), len(rejected))
    return {"tests": approved, "rejected_queries": rejected}


def _expected_pass(expected: str, row_count: int) -> str:
    text = (expected or "").lower()
    zero_expected = any(token in text for token in ("0 row", "zero row", "no row", "empty"))
    if zero_expected:
        return "PASS" if row_count == 0 else "FAIL"
    return "EXECUTED"


def execute_on_adb(state: AgentState) -> AgentState:
    settings = get_databricks_settings()
    results: list[QueryExecution] = []

    if state.get("execute_queries") is False:
        logger.info("Databricks execution disabled; marking %d test(s) SKIPPED", len(state.get("tests") or []))
        for test in state.get("tests") or []:
            results.append(
                {
                    "test_id": test.get("test_id", "UNKNOWN"),
                    "status": "SKIPPED",
                    "error": "ADB execution disabled (--no-execute).",
                }
            )
        return {"execution_results": results}

    if settings.is_dummy:
        for test in state.get("tests") or []:
            results.append(
                {
                    "test_id": test.get("test_id", "UNKNOWN"),
                    "status": "SKIPPED",
                    "error": "Dummy Azure Databricks credentials in .env. Update DATABRICKS_* values to execute on ADB.",
                }
            )
        return {"execution_results": results}

    logger.info("Executing %d query/queries on Azure Databricks...", len(state.get("tests") or []))
    for test in state.get("tests") or []:
        test_id = test.get("test_id", "UNKNOWN")
        sql_query = (test.get("sql_query") or "").strip()
        if has_unresolved_placeholders(sql_query):
            results.append(
                {
                    "test_id": test_id,
                    "status": "SKIPPED",
                    "error": "Query contains QA placeholders (e.g. ${last_watermark_ts}). Replace them before execution.",
                }
            )
            continue
        try:
            payload = execute_select(sql_query, settings)
            status = _expected_pass(test.get("expected_result", ""), payload["row_count_preview"])
            if payload.get("truncated") and status == "PASS":
                status = "FAIL"
            results.append(
                {
                    "test_id": test_id,
                    "status": status,
                    "row_count_preview": payload["row_count_preview"],
                    "truncated": payload["truncated"],
                    "columns": payload["columns"],
                    "preview": payload["preview"],
                }
            )
        except Exception as exc:
            logger.warning("%s failed on Databricks: %s", test_id, exc)
            results.append({"test_id": test_id, "status": "ERROR", "error": str(exc)})

    return {"execution_results": results}
