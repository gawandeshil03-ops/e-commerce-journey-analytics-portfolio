from __future__ import annotations

import math

import pandas as pd
from scipy.stats import norm


def two_proportion_sample_size(
    baseline_rate: float,
    treatment_rate: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be between 0 and 1.")
    if not 0 < treatment_rate < 1:
        raise ValueError("treatment_rate must be between 0 and 1.")
    if baseline_rate == treatment_rate:
        raise ValueError("The treatment rate must differ from the baseline rate.")

    pooled_rate = (baseline_rate + treatment_rate) / 2
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)

    numerator = (
        z_alpha * math.sqrt(2 * pooled_rate * (1 - pooled_rate))
        + z_power
        * math.sqrt(
            baseline_rate * (1 - baseline_rate)
            + treatment_rate * (1 - treatment_rate)
        )
    ) ** 2
    denominator = (treatment_rate - baseline_rate) ** 2
    return math.ceil(numerator / denominator)


def build_power_table(
    baseline_rate: float,
    weekly_eligible_visitors: float,
    relative_lifts: tuple[float, ...] = (0.15, 0.20, 0.25, 0.30),
    follow_up_days: int = 7,
    alpha: float = 0.05,
    power: float = 0.80,
) -> pd.DataFrame:
    rows: list[dict[str, float | int]] = []

    for relative_lift in relative_lifts:
        treatment_rate = baseline_rate * (1 + relative_lift)
        per_arm = two_proportion_sample_size(
            baseline_rate,
            treatment_rate,
            alpha=alpha,
            power=power,
        )
        total = per_arm * 2
        acquisition_weeks = total / weekly_eligible_visitors
        calendar_weeks = math.ceil(acquisition_weeks + follow_up_days / 7)
        rows.append(
            {
                "baseline_rate": baseline_rate,
                "alpha": alpha,
                "power": power,
                "relative_mde": relative_lift,
                "absolute_mde": treatment_rate - baseline_rate,
                "treatment_rate": treatment_rate,
                "sample_size_per_arm": per_arm,
                "total_sample_size": total,
                "weekly_eligible_visitors": weekly_eligible_visitors,
                "acquisition_weeks": acquisition_weeks,
                "follow_up_days": follow_up_days,
                "estimated_calendar_weeks": calendar_weeks,
            }
        )

    return pd.DataFrame(rows)
