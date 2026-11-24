"""Export normalized KPI SQL as an Excel workbook."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from src.utils.llm_json import coerce_str_list

_MAX_CELL_CHARS = 32000


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "; ".join(str(item) for item in value if item not in (None, ""))
    return str(value)[:_MAX_CELL_CHARS]


def _style_header(sheet) -> None:
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"


def _set_widths(sheet, widths: dict[str, int]) -> None:
    for letter, width in widths.items():
        sheet.column_dimensions[letter].width = width


def kpi_normalization_excel_bytes(normalized: dict[str, Any]) -> bytes:
    queries = normalized.get("queries") or []
    rejected = normalized.get("rejected_queries") or []
    notes = normalized.get("global_notes") or []

    workbook = Workbook()

    summary = workbook.active
    summary.title = "Summary"
    summary.append(["Metric", "Value"])
    summary.append(["Total KPI queries", normalized.get("total_count", len(queries))])
    summary.append(["Databricks-ready", normalized.get("runnable_count", 0)])
    summary.append(["Rejected / blocked", len(rejected)])
    summary.append(["Source file", _text(normalized.get("source_path"))])
    _style_header(summary)
    _set_widths(summary, {"A": 24, "B": 80})

    sheet = workbook.create_sheet("Normalized KPI SQL")
    sheet.append(
        [
            "KPI ID",
            "KPI Name",
            "Module",
            "Status",
            "Original SQL",
            "Normalized SQL",
            "Fixes Applied",
            "Issues Remaining",
        ]
    )
    for entry in queries:
        sheet.append(
            [
                _text(entry.get("kpi_id")),
                _text(entry.get("kpi_name")),
                _text(entry.get("module")),
                "Ready" if entry.get("runnable", True) else "Blocked",
                _text(entry.get("original_sql") or entry.get("sql_query")),
                _text(entry.get("normalized_sql")),
                _text(coerce_str_list(entry.get("fixes_applied"))),
                _text(coerce_str_list(entry.get("issues_remaining"))),
            ]
        )
    _style_header(sheet)
    _set_widths(sheet, {"A": 14, "B": 30, "C": 18, "D": 10, "E": 70, "F": 70, "G": 40, "H": 40})
    wrap = Alignment(wrap_text=True, vertical="top")
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap

    if rejected:
        rejected_sheet = workbook.create_sheet("Rejected Queries")
        rejected_sheet.append(["Reason"])
        for item in rejected:
            rejected_sheet.append([_text(item)])
        _style_header(rejected_sheet)
        _set_widths(rejected_sheet, {"A": 120})

    if notes:
        notes_sheet = workbook.create_sheet("Normalization Notes")
        notes_sheet.append(["Note"])
        for note in notes:
            notes_sheet.append([_text(note)])
        _style_header(notes_sheet)
        _set_widths(notes_sheet, {"A": 120})

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
