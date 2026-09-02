from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from .config import OUTPUT_DIR, TABLE_DIR, ensure_directories
from .experiment import build_power_table


EXPORT_TABLES = (
    "data_quality_summary",
    "event_type_summary",
    "session_gap_sensitivity",
    "product_kpi_summary",
    "funnel_summary",
    "weekly_metrics",
    "visitor_status_metrics",
    "visitor_status_sensitivity",
    "visitor_concentration",
    "cohort_retention",
    "overall_retention_by_week",
    "activation_retention_w1",
    "cart_recovery_curve",
    "cart_recovery_weekly_eligibility",
)


def _native(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def _record(dataframe: pd.DataFrame) -> dict[str, Any]:
    return {key: _native(value) for key, value in dataframe.iloc[0].items()}


def export_tables(connection: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    ensure_directories()
    tables: dict[str, pd.DataFrame] = {}

    for table_name in EXPORT_TABLES:
        dataframe = connection.execute(f"SELECT * FROM {table_name}").df()
        dataframe.to_csv(TABLE_DIR / f"{table_name}.csv", index=False)
        tables[table_name] = dataframe

    recovery_7d = tables["cart_recovery_curve"].query("days == 7").iloc[0]
    weekly_eligibility = tables["cart_recovery_weekly_eligibility"]
    power_table = build_power_table(
        baseline_rate=float(recovery_7d["recovery_rate_pct"]) / 100,
        weekly_eligible_visitors=float(weekly_eligibility["eligible_visitors"].mean()),
    )
    power_table.to_csv(TABLE_DIR / "experiment_power.csv", index=False)
    tables["experiment_power"] = power_table

    return tables


def build_summary(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    quality = _record(tables["data_quality_summary"])
    kpis = _record(tables["product_kpi_summary"])
    status = tables["visitor_status_metrics"].set_index("visitor_status")
    activation = tables["activation_retention_w1"].set_index("first_session_stage")
    recovery = tables["cart_recovery_curve"].set_index("days")
    retention = tables["overall_retention_by_week"].set_index("week_number")
    concentration = tables["visitor_concentration"].set_index(
        "visitor_activity_segment"
    )
    power = tables["experiment_power"]
    recommended_power = power.loc[np.isclose(power["relative_mde"], 0.25)].iloc[0]

    summary = {
        "data": {
            "raw_event_rows": quality["raw_event_rows"],
            "clean_event_rows": quality["clean_event_rows"],
            "duplicate_rows_removed": quality["duplicate_rows_removed"],
            "visitors": quality["visitors"],
            "items": quality["items"],
            "transactions": quality["transactions"],
            "min_event_time_utc": quality["min_event_time_utc"],
            "max_event_time_utc": quality["max_event_time_utc"],
        },
        "sessions": {
            "total_sessions": int(kpis["total_sessions"]),
            "one_session_visitor_share_pct": kpis[
                "one_session_visitor_share_pct"
            ],
            "transaction_session_rate_pct": kpis[
                "transaction_session_rate_pct"
            ],
        },
        "funnel": {
            "view_sessions": int(kpis["view_sessions"]),
            "ordered_view_to_cart_sessions": int(
                kpis["ordered_view_to_cart_sessions"]
            ),
            "ordered_full_funnel_sessions": int(
                kpis["ordered_view_to_cart_to_transaction_sessions"]
            ),
            "ordered_view_to_cart_rate_pct": kpis[
                "ordered_view_to_cart_rate_pct"
            ],
            "ordered_cart_to_transaction_rate_pct": kpis[
                "ordered_cart_to_transaction_rate_pct"
            ],
            "ordered_view_to_transaction_rate_pct": kpis[
                "ordered_view_to_transaction_rate_pct"
            ],
            "cart_without_transaction_sessions": int(
                kpis["cart_without_transaction_sessions"]
            ),
            "same_session_cart_to_transaction_rate_pct": kpis[
                "same_session_cart_to_transaction_rate_pct"
            ],
        },
        "visitor_status": {
            "new_transaction_session_rate_pct": _native(
                status.loc["new", "transaction_session_rate_pct"]
            ),
            "returning_transaction_session_rate_pct": _native(
                status.loc["returning", "transaction_session_rate_pct"]
            ),
            "returning_to_new_rate_ratio": _native(
                status.loc["returning", "transaction_session_rate_pct"]
                / status.loc["new", "transaction_session_rate_pct"]
            ),
            "top_0_1_percent_transaction_session_share_pct": _native(
                concentration.loc[
                    "top_0_1_percent", "transaction_session_share_pct"
                ]
            ),
        },
        "retention": {
            "weighted_w1_retention_rate_pct": _native(
                retention.loc[1, "weighted_retention_rate_pct"]
            ),
            "view_only_w1_retention_rate_pct": _native(
                activation.loc["view_only", "w1_retention_rate_pct"]
            ),
            "cart_no_purchase_w1_retention_rate_pct": _native(
                activation.loc["cart_no_purchase", "w1_retention_rate_pct"]
            ),
            "purchased_w1_retention_rate_pct": _native(
                activation.loc["purchased", "w1_retention_rate_pct"]
            ),
        },
        "cart_recovery": {
            "eligible_visitors_7d": _native(
                recovery.loc[7, "eligible_visitors"]
            ),
            "recovered_visitors_7d": _native(
                recovery.loc[7, "recovered_visitors"]
            ),
            "recovery_rate_7d_pct": _native(
                recovery.loc[7, "recovery_rate_pct"]
            ),
            "average_weekly_eligible_visitors": _native(
                tables["cart_recovery_weekly_eligibility"][
                    "eligible_visitors"
                ].mean()
            ),
        },
        "experiment": {
            "relative_mde_pct": 25.0,
            "absolute_mde_percentage_points": _native(
                recommended_power["absolute_mde"] * 100
            ),
            "sample_size_per_arm": int(recommended_power["sample_size_per_arm"]),
            "total_sample_size": int(recommended_power["total_sample_size"]),
            "estimated_calendar_weeks": int(
                recommended_power["estimated_calendar_weeks"]
            ),
        },
    }
    return summary


def write_summary(summary: dict[str, Any], path: Path | None = None) -> Path:
    ensure_directories()
    output_path = path or OUTPUT_DIR / "summary_metrics.json"
    output_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path
