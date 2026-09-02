from __future__ import annotations

import json
from pathlib import Path

import nbformat

from .config import FIGURE_DIR, NOTEBOOK_PATH, OUTPUT_DIR, PROJECT_ROOT, TABLE_DIR
from .database import connect


EXPECTED = {
    "raw_event_rows": 2_756_101,
    "duplicate_rows_removed": 460,
    "total_sessions": 1_761_675,
    "eligible_visitors_7d": 27_784,
    "recovered_visitors_7d": 1_369,
}


def validate_project() -> list[str]:
    checks: list[str] = []
    connection = connect(read_only=True)

    quality = connection.execute("SELECT * FROM data_quality_summary").fetchone()
    quality_columns = [
        column[0] for column in connection.description
    ]
    quality_record = dict(zip(quality_columns, quality))

    assert quality_record["raw_event_rows"] == EXPECTED["raw_event_rows"]
    assert (
        quality_record["duplicate_rows_removed"]
        == EXPECTED["duplicate_rows_removed"]
    )
    assert quality_record["rows_with_missing_required_fields"] == 0
    assert quality_record["invalid_event_type_rows"] == 0
    assert quality_record["transactions_without_id"] == 0
    assert quality_record["non_transactions_with_id"] == 0
    checks.append("PASS: source grain, required fields, and event rules")

    funnel = connection.execute("SELECT * FROM funnel_summary").df().iloc[0]
    assert int(funnel["total_sessions"]) == EXPECTED["total_sessions"]
    assert (
        funnel["view_sessions"]
        >= funnel["ordered_view_to_cart_sessions"]
        >= funnel["ordered_view_to_cart_to_transaction_sessions"]
    )
    for column in (
        "ordered_view_to_cart_rate_pct",
        "ordered_cart_to_transaction_rate_pct",
        "ordered_view_to_transaction_rate_pct",
        "same_session_cart_to_transaction_rate_pct",
        "transaction_session_rate_pct",
    ):
        assert 0 <= float(funnel[column]) <= 100
    checks.append("PASS: funnel denominators and stage ordering")

    recovery = connection.execute(
        "SELECT * FROM cart_recovery_curve ORDER BY days"
    ).df()
    seven_day = recovery.query("days == 7").iloc[0]
    assert int(seven_day["eligible_visitors"]) == EXPECTED["eligible_visitors_7d"]
    assert (
        int(seven_day["recovered_visitors"])
        == EXPECTED["recovered_visitors_7d"]
    )
    assert (recovery["recovered_visitors"] <= recovery["eligible_visitors"]).all()
    checks.append("PASS: right-censored cart-recovery windows")

    gap_sensitivity = connection.execute(
        "SELECT * FROM session_gap_sensitivity ORDER BY gap_minutes"
    ).df()
    rate_range = (
        gap_sensitivity["transaction_session_rate_pct"].max()
        - gap_sensitivity["transaction_session_rate_pct"].min()
    )
    assert rate_range < 0.1
    checks.append("PASS: session-gap sensitivity remains below 0.1 percentage point")

    connection.close()

    summary_path = OUTPUT_DIR / "summary_metrics.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["data"]["raw_event_rows"] == EXPECTED["raw_event_rows"]
    assert summary["sessions"]["total_sessions"] == EXPECTED["total_sessions"]
    assert (
        summary["cart_recovery"]["eligible_visitors_7d"]
        == EXPECTED["eligible_visitors_7d"]
    )
    checks.append("PASS: exported summary matches database results")

    required_tables = [
        "data_quality_summary.csv",
        "product_kpi_summary.csv",
        "cohort_retention.csv",
        "cart_recovery_curve.csv",
        "experiment_power.csv",
    ]
    for filename in required_tables:
        path = TABLE_DIR / filename
        assert path.exists() and path.stat().st_size > 0

    required_figures = [
        "01_funnel_conversion.png",
        "02_weekly_metrics.png",
        "03_visitor_status_conversion.png",
        "04_cohort_retention.png",
        "05_cart_recovery.png",
    ]
    for filename in required_figures:
        path = FIGURE_DIR / filename
        assert path.exists() and path.stat().st_size > 10_000
    checks.append("PASS: required tables and figures exist")

    notebook = nbformat.read(NOTEBOOK_PATH, as_version=4)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert code_cells
    assert all(cell.execution_count is not None for cell in code_cells)
    assert not any(
        output.output_type == "error"
        for cell in code_cells
        for output in cell.get("outputs", [])
    )
    checks.append("PASS: notebook executed top to bottom without errors")

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "4.93%" in readme
    assert "1,761,675" in readme
    assert "5,416" in readme
    checks.append("PASS: headline README claims are present")

    report_path = OUTPUT_DIR / "validation_report.txt"
    report_path.write_text("\n".join(checks) + "\n", encoding="utf-8")
    return checks
