import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from src.config import adb_runtime_context
from src.prompts.kpi_logic_prompts import KPI_SQL_NORMALIZATION_PROMPT, KPI_SQL_NORMALIZER_SYSTEM_PROMPT
from src.utils.llm_json import invoke_llm_json
from src.utils.sql_safety import has_unresolved_placeholders, is_select_only, validate_sql_test

BATCH_SIZE = 8
MAX_WORKERS = int(os.getenv("KPI_NORMALIZATION_WORKERS", "4"))


def _to_validation_test(entry: dict[str, Any], index: int) -> dict[str, Any]:
    kpi_id = entry.get("kpi_id") or f"KPI-{index:03d}"
    test_id = kpi_id if str(kpi_id).upper().startswith("QA-") else f"QA-KPI-{index:03d}"
    return {
        "test_id": test_id,
        "test_scenario": f"KPI validation: {entry.get('kpi_name', kpi_id)}",
        "validation_type": "KPI Data Validation",
        "sql_query": (entry.get("normalized_sql") or entry.get("sql_query") or "").strip(),
        "expected_result": entry.get("expected_result") or "0 rows returned (no validation failures).",
        "priority": entry.get("priority") or "High",
        "kpi_id": kpi_id,
        "kpi_name": entry.get("kpi_name", ""),
        "module": entry.get("module", ""),
    }


def normalize_kpi_sql_queries(
    entries: list[dict[str, Any]],
    *,
    requirement_context: str = "",
) -> dict[str, Any]:
    if not entries:
        return {
            "queries": [],
            "tests": [],
            "rejected_queries": [],
            "global_notes": [],
            "runnable_count": 0,
            "total_count": 0,
        }

    normalized_queries: list[dict[str, Any]] = []
    global_notes: list[str] = []

    adb_context = json.dumps(adb_runtime_context(), indent=2)
    batches = [entries[start : start + BATCH_SIZE] for start in range(0, len(entries), BATCH_SIZE)]

    def _normalize_batch(batch: list[dict[str, Any]]) -> dict[str, Any]:
        return invoke_llm_json(
            KPI_SQL_NORMALIZATION_PROMPT.format(
                adb_context=adb_context,
                requirement_context=requirement_context or "No additional requirement context provided.",
                kpi_entries=json.dumps(batch, indent=2),
            ),
            system_prompt=KPI_SQL_NORMALIZER_SYSTEM_PROMPT,
        )

    # Batches are independent LLM calls; run them concurrently and keep input order.
    workers = max(1, min(MAX_WORKERS, len(batches)))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="kpi-batch") as pool:
        for payload in pool.map(_normalize_batch, batches):
            normalized_queries.extend(payload.get("queries") or [])
            global_notes.extend(payload.get("global_notes") or [])

    tests: list[dict[str, Any]] = []
    rejected: list[str] = []
    runnable_count = 0

    for index, entry in enumerate(normalized_queries, start=1):
        if not entry.get("runnable", True):
            rejected.append(
                f"{entry.get('kpi_id', f'KPI-{index}')}: not runnable — "
                + "; ".join(entry.get("issues_remaining") or ["normalization failed"])
            )
            continue

        test = _to_validation_test(entry, index)
        if has_unresolved_placeholders(test["sql_query"]):
            rejected.append(
                f"{entry.get('kpi_id', test['test_id'])}: not runnable — unresolved placeholder(s) "
                "remain in the normalized SQL"
            )
            continue
        ok, reason = validate_sql_test(test)
        if ok and is_select_only(test["sql_query"]):
            tests.append(test)
            runnable_count += 1
        else:
            rejected.append(reason or f"{test['test_id']}: failed SQL safety validation")

    return {
        "queries": normalized_queries,
        "tests": tests,
        "rejected_queries": rejected,
        "global_notes": list(dict.fromkeys(global_notes)),
        "runnable_count": runnable_count,
        "total_count": len(entries),
    }
