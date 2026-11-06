from src.agents.etl_agent import build_etl_test_plan


def test_etl_agent_reports_manager_categories_and_coverage():
    plan = build_etl_test_plan(
        {
            "source_table": "main.stg.customer",
            "target_table": "main.dw.customer",
            "load_type": "incremental",
            "business_rules": ["Eligible customers only"],
        },
        {
            "mappings": [
                {
                    "transformation": {"type": "SCD", "logic": "SCD Type 2"},
                    "validation_rules": [{"rule_id": "VR02"}, {"rule_id": "VR24"}],
                }
            ]
        },
    )

    assert len(plan) == 10
    by_category = {item["category"]: item for item in plan}
    assert by_category["Schema validation"]["status"] == "covered"
    assert by_category["Incremental-load testing"]["status"] == "covered"
    assert by_category["SCD testing"]["status"] == "covered"
    assert by_category["Lineage testing"]["source_rule_ids"] == ["VR02", "VR24"]


def test_etl_agent_exposes_gaps_without_inventing_support():
    plan = build_etl_test_plan({}, {})
    by_category = {item["category"]: item for item in plan}

    assert by_category["Schema validation"]["status"] == "gap"
    assert by_category["Incremental-load testing"]["status"] == "gap"
    assert by_category["Regression testing"]["status"] == "gap"
    assert by_category["Regression testing"]["gap"]
