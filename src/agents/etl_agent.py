"""ETL QA coverage planning for the manager-defined validation categories."""

from __future__ import annotations

from typing import Any


ETL_TEST_CATEGORIES: tuple[dict[str, str], ...] = (
    {
        "category": "Schema validation",
        "description": "Column names, data types, and missing or extra columns.",
    },
    {
        "category": "Source-target reconciliation",
        "description": "Source and target record counts and matching records.",
    },
    {
        "category": "Data quality",
        "description": "NULLs, duplicates, and primary-key violations.",
    },
    {
        "category": "Transformation validation",
        "description": "Joins, filters, aggregations, and calculated columns.",
    },
    {
        "category": "Business-rule validation",
        "description": "Eligibility, balances, classifications, and other rules.",
    },
    {
        "category": "Incremental-load testing",
        "description": "Inserts, updates, deletes, watermarks, and rerun behavior.",
    },
    {
        "category": "SCD testing",
        "description": "SCD Type 1 and Type 2 history behavior.",
    },
    {
        "category": "Negative and boundary testing",
        "description": "Invalid values, empty inputs, and date boundaries.",
    },
    {
        "category": "Regression testing",
        "description": "Previously approved rules against new pipeline versions.",
    },
    {
        "category": "Lineage testing",
        "description": "Source-to-target mapping and transformation paths.",
    },
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _has_mapping_data(mapping_analysis: dict[str, Any]) -> bool:
    return bool(mapping_analysis.get("mappings"))


def build_etl_test_plan(
    etl_spec: dict[str, Any] | None,
    mapping_analysis: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Build a transparent coverage plan before SQL generation.

    The planner never invents tables or rules. It records which manager-defined
    categories are supported by the supplied ETL spec and mapping evidence.
    """

    spec = etl_spec or {}
    analysis = mapping_analysis or {}
    mappings = list(analysis.get("mappings") or [])
    has_mappings = _has_mapping_data(analysis)
    load_type = _text(spec.get("load_type")).lower()
    transformation_types = {
        _text((item.get("transformation") or {}).get("type")).upper()
        for item in mappings
    }
    mapping_business_rules = any(
        _text((item.get("transformation") or {}).get("logic"))
        or _text((item.get("business_rule") or (item.get("target") or {}).get("business_rule")))
        for item in mappings
    )
    business_rules = list(spec.get("business_rules") or [])
    notes = _text(spec.get("additional_notes")).lower()
    has_scd = "SCD" in transformation_types or "slowly changing" in notes or "scd" in notes

    evidence: dict[str, tuple[bool, str, str]] = {
        "Schema validation": (
            has_mappings,
            "Mapping columns and source/target data types are available.",
            "Upload or approve a source-to-target mapping.",
        ),
        "Source-target reconciliation": (
            bool(_text(spec.get("source_table")) and _text(spec.get("target_table"))),
            "Source and target tables are defined.",
            "Provide source_table and target_table.",
        ),
        "Data quality": (
            has_mappings,
            "Mapping rules provide NULL, duplicate, and key-validation evidence.",
            "Provide mapping rows, nullable metadata, or primary-key information.",
        ),
        "Transformation validation": (
            has_mappings and bool(transformation_types),
            "Mapping transformations can be checked against target values.",
            "Provide transformation logic in the mapping.",
        ),
        "Business-rule validation": (
            bool(business_rules) or mapping_business_rules,
            "Business rules were supplied in the ETL spec or mapping.",
            "Provide explicit business rules such as eligibility or classification logic.",
        ),
        "Incremental-load testing": (
            load_type in {"incremental", "cdc", "change data capture"},
            f"Load type is {load_type or 'not specified'}.",
            "Set load_type to incremental or cdc and provide watermark details.",
        ),
        "SCD testing": (
            has_scd,
            "SCD logic was identified in the mapping or ETL notes.",
            "Declare SCD Type 1/2 behavior and effective-date columns.",
        ),
        "Negative and boundary testing": (
            has_mappings,
            "Column types, nullability, and mapping rules provide boundary candidates.",
            "Provide data types, limits, and invalid-value expectations.",
        ),
        "Regression testing": (
            bool(spec.get("spec_version") or spec.get("approved_rules")),
            "An approved spec or rule baseline is available.",
            "Select an approved prior spec or provide a regression baseline.",
        ),
        "Lineage testing": (
            has_mappings,
            "Source-to-target mapping rows provide lineage evidence.",
            "Provide source-to-target mapping and transformation paths.",
        ),
    }

    plan: list[dict[str, Any]] = []
    for definition in ETL_TEST_CATEGORIES:
        category = definition["category"]
        supported, evidence_text, gap = evidence[category]
        plan.append(
            {
                "category": category,
                "description": definition["description"],
                "status": "covered" if supported else "gap",
                "evidence": evidence_text if supported else "",
                "gap": "" if supported else gap,
                "source_rule_ids": sorted(
                    {
                        str(rule.get("rule_id") or "")
                        for item in mappings
                        for rule in item.get("validation_rules") or []
                        if rule.get("rule_id")
                    }
                )
                if supported
                else [],
            }
        )
    return plan
