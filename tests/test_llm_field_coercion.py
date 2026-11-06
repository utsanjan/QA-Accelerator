from src.agents.reporting_agent import format_qa_report
from src.utils.llm_json import coerce_str_list, coerce_text


def test_coerce_text_flattens_list():
    assert coerce_text(["first note", "second note"]) == "first note\nsecond note"
    assert coerce_text("plain") == "plain"
    assert coerce_text(None) == ""
    assert coerce_text({"summary": "ok"}) == "summary: ok"


def test_coerce_str_list_does_not_split_a_string():
    assert coerce_str_list("one gap") == ["one gap"]
    assert coerce_str_list(["a", "", "b"]) == ["a", "b"]
    assert coerce_str_list([["nested", "value"]]) == ["nested value"]
    assert coerce_str_list(None) == []


def test_report_survives_list_valued_analyst_notes():
    """Reproduces 'sequence item 20: expected str instance, list found'."""
    state = {
        "etl_spec": {"source_table": "main.stg.src", "target_table": "main.dw.tgt"},
        "analyst_notes": ["Counts can be validated.", "Watermark table is unknown."],
        "missing_information": "No watermark table provided.",
        "assumptions": ["Load is incremental."],
        "tests": [],
        "test_cases": [],
    }
    report = format_qa_report(state)["qa_report"]
    assert "Counts can be validated." in report
    assert "Watermark table is unknown." in report
    assert "- No watermark table provided." in report


def test_report_survives_list_valued_gaps_and_test_case_ids():
    state = {
        "etl_spec": {},
        "tests": [],
        "test_cases": [],
        "mapping_analysis": {
            "mappings": [
                {
                    "mapping_id": "MAP-001",
                    "source": {"column": "cust_id"},
                    "target": {"column": "customer_id"},
                    "transformation": {"type": "DIRECT"},
                    "gaps": [["datatype mismatch", "missing business rule"]],
                    "validation_rules": [{"rule_id": "VR10"}],
                }
            ]
        },
        "test_case_artifacts": {
            "requirement_traceability_matrix": [
                {"requirement_id": "US-1", "coverage_status": "Covered", "test_case_ids": [101, "TC-2"]}
            ]
        },
    }
    report = format_qa_report(state)["qa_report"]
    assert "datatype mismatch" in report
    assert "101, TC-2" in report
