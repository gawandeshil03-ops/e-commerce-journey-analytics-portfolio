from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from .config import FIGURE_DIR, ensure_directories


BLUE = "#315C8C"
BLUE_LIGHT = "#9DB7D2"
GOLD = "#D39E2F"
CHARCOAL = "#25313C"
GREY = "#6E7781"
GRID = "#D9DEE3"
BACKGROUND = "#FFFFFF"


def configure_style() -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams.update(
        {
            "figure.facecolor": BACKGROUND,
            "axes.facecolor": BACKGROUND,
            "axes.edgecolor": CHARCOAL,
            "axes.labelcolor": CHARCOAL,
            "axes.titlecolor": CHARCOAL,
            "text.color": CHARCOAL,
            "xtick.color": GREY,
            "ytick.color": GREY,
            "grid.color": GRID,
            "grid.linewidth": 0.7,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.frameon": False,
        }
    )


def _save(figure: plt.Figure, filename: str) -> Path:
    ensure_directories()
    output_path = FIGURE_DIR / filename
    figure.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=BACKGROUND)
    plt.close(figure)
    return output_path


def plot_funnel(funnel: pd.DataFrame) -> plt.Figure:
    row = funnel.iloc[0]
    labels = [
        "View → cart",
        "Cart → transaction",
        "View → transaction",
    ]
    values = [
        row["ordered_view_to_cart_rate_pct"],
        row["ordered_cart_to_transaction_rate_pct"],
        row["ordered_view_to_transaction_rate_pct"],
    ]
    colors = [BLUE, GOLD, BLUE_LIGHT]

    figure, axis = plt.subplots(figsize=(8.2, 4.6))
    bars = axis.barh(labels, values, color=colors, edgecolor=CHARCOAL, linewidth=0.6)
    axis.invert_yaxis()
    axis.set_xlim(0, max(values) * 1.2)
    axis.set_xlabel("Conversion rate, %")
    axis.set_ylabel("")
    axis.grid(axis="y", visible=False)
    axis.spines[["top", "right"]].set_visible(False)

    for bar, value in zip(bars, values):
        axis.text(
            value + max(values) * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}%",
            va="center",
            color=CHARCOAL,
            fontweight="bold",
        )

    figure.suptitle(
        "Observed within-session funnel conversion",
        x=0.125,
        y=0.98,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    axis.set_title(
        "30-minute sessions; ordered events with non-decreasing timestamps; UTC",
        loc="left",
        color=GREY,
        pad=12,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.9))
    return figure


def plot_weekly_metrics(weekly: pd.DataFrame) -> plt.Figure:
    data = weekly.copy()
    data["week_start"] = pd.to_datetime(data["week_start"])

    figure, axis = plt.subplots(figsize=(9.4, 4.9))
    axis.plot(
        data["week_start"],
        data["cart_session_rate_pct"],
        color=BLUE,
        linewidth=2.1,
        marker="o",
        markersize=4,
        label="Cart-session rate",
    )
    axis.plot(
        data["week_start"],
        data["transaction_session_rate_pct"],
        color=GOLD,
        linewidth=2.1,
        marker="s",
        markersize=3.8,
        label="Transaction-session rate",
    )
    axis.set_ylabel("Share of sessions, %")
    axis.set_xlabel("")
    axis.xaxis.set_major_locator(mdates.WeekdayLocator(interval=3))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    axis.legend(loc="upper right")
    axis.spines[["top", "right"]].set_visible(False)

    figure.suptitle(
        "Weekly cart and transaction session rates",
        x=0.09,
        y=0.98,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    axis.set_title(
        "Complete Monday–Sunday weeks; partial boundary weeks excluded",
        loc="left",
        color=GREY,
        pad=12,
    )
    figure.autofmt_xdate(rotation=0)
    figure.tight_layout(rect=(0, 0, 1, 0.9))
    return figure


def plot_visitor_status(sensitivity: pd.DataFrame) -> plt.Figure:
    labels = {
        "all_visitors": "All visitors",
        "excluding_top_0_1_percent": "Excluding top 0.1%",
    }
    data = sensitivity.copy()
    data["analysis_scope"] = data["analysis_scope"].map(labels)
    pivot = data.pivot(
        index="visitor_status",
        columns="analysis_scope",
        values="transaction_session_rate_pct",
    ).reindex(["new", "returning"])

    figure, axis = plt.subplots(figsize=(7.8, 4.8))
    pivot.plot(
        kind="bar",
        ax=axis,
        color=[BLUE, GOLD],
        edgecolor=CHARCOAL,
        linewidth=0.6,
        width=0.68,
    )
    axis.set_xticklabels(["New", "Returning"], rotation=0)
    axis.set_xlabel("")
    axis.set_ylabel("Transaction-session rate, %")
    axis.set_ylim(0, pivot.to_numpy().max() * 1.25)
    axis.grid(axis="x", visible=False)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(title="")

    for container in axis.containers:
        axis.bar_label(container, fmt="%.2f%%", padding=3, fontsize=9)

    figure.suptitle(
        "Transaction-session rate by visitor status",
        x=0.105,
        y=0.98,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    axis.set_title(
        "Sensitivity cut removes visitors above the 99.9th percentile of session count",
        loc="left",
        color=GREY,
        pad=12,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.9))
    return figure


def plot_retention_heatmap(retention: pd.DataFrame) -> plt.Figure:
    data = retention.copy()
    data["cohort_week"] = pd.to_datetime(data["cohort_week"])
    data = data.query("week_number >= 1")
    pivot = data.pivot(
        index="cohort_week",
        columns="week_number",
        values="retention_rate_pct",
    )
    pivot.index = pivot.index.strftime("%d %b")
    pivot.columns = [f"W{column}" for column in pivot.columns]

    figure, axis = plt.subplots(figsize=(9.2, 6.7))
    sns.heatmap(
        pivot,
        mask=pivot.isna(),
        cmap=sns.light_palette(BLUE, as_cmap=True),
        annot=True,
        fmt=".1f",
        linewidths=0.5,
        linecolor=BACKGROUND,
        cbar_kws={"label": "Retention rate, %"},
        ax=axis,
        annot_kws={"fontsize": 8},
    )
    axis.set_xlabel("Weeks since first observed activity")
    axis.set_ylabel("First observed week")
    axis.tick_params(axis="y", rotation=0)

    figure.suptitle(
        "Weekly visitor-ID retention by first observed cohort",
        x=0.105,
        y=0.99,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    axis.set_title(
        "Any event counts as return activity; incomplete future weeks are left blank",
        loc="left",
        color=GREY,
        pad=12,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.93))
    return figure


def plot_cart_recovery(recovery: pd.DataFrame) -> plt.Figure:
    data = recovery.copy()

    figure, axis = plt.subplots(figsize=(8.2, 4.8))
    axis.plot(
        data["days"],
        data["recovery_rate_pct"],
        color=BLUE,
        linewidth=2.3,
        marker="o",
        markersize=6,
    )
    axis.set_xticks(data["days"])
    axis.set_xlabel("Days after first observed cart abandonment")
    axis.set_ylabel("Visitors with a later transaction, %")
    axis.set_ylim(0, data["recovery_rate_pct"].max() * 1.28)
    axis.spines[["top", "right"]].set_visible(False)

    for _, row in data.iterrows():
        axis.annotate(
            f"{row['recovery_rate_pct']:.2f}%\n(n={int(row['eligible_visitors']):,})",
            (row["days"], row["recovery_rate_pct"]),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color=CHARCOAL,
        )

    figure.suptitle(
        "Natural purchase recovery after cart abandonment",
        x=0.11,
        y=0.98,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    axis.set_title(
        "First qualifying event per visitor; each horizon uses complete follow-up only",
        loc="left",
        color=GREY,
        pad=12,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.9))
    return figure


def generate_figures(tables: dict[str, pd.DataFrame]) -> list[Path]:
    configure_style()
    return [
        _save(plot_funnel(tables["funnel_summary"]), "01_funnel_conversion.png"),
        _save(plot_weekly_metrics(tables["weekly_metrics"]), "02_weekly_metrics.png"),
        _save(
            plot_visitor_status(tables["visitor_status_sensitivity"]),
            "03_visitor_status_conversion.png",
        ),
        _save(
            plot_retention_heatmap(tables["cohort_retention"]),
            "04_cohort_retention.png",
        ),
        _save(
            plot_cart_recovery(tables["cart_recovery_curve"]),
            "05_cart_recovery.png",
        ),
    ]
