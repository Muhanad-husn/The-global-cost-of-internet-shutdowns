"""Country-level rollups built off the analytic dataset.

The headline rollups live here so both the notebook (`02_main.ipynb` §9 + §12)
and the Streamlit dashboard (S6) call the same code path. The functions read a
DataFrame in the shape of `data/processed/analytic_dataset_*.parquet`.
"""
from __future__ import annotations

from typing import Literal

import pandas as pd

View = Literal["combined", "blackout_only", "separated"]


def shutdown_day_rollup(frame: pd.DataFrame, view: View = "combined") -> pd.DataFrame:
    """Country-level shutdown-day totals under the chosen view.

    Views (Decision Log #14):
    - ``"combined"``: every event contributes its `duration_days` regardless of
      bucket. Matches Top10VPN's country/year aggregation.
    - ``"blackout_only"``: restricts to `bucket == "full_blackout"`.
    - ``"separated"``: keeps the bucket axis (one row per country × bucket).
    """
    f = frame.copy()
    f["bucket"] = (
        f["platform_block"].map({True: "platform_block"})
            .fillna(f["type"].astype("string"))
    )
    if view == "separated":
        return (
            f.groupby(["country", "iso3", "bucket"], dropna=False)["duration_days"]
             .sum(min_count=1).reset_index()
        )
    if view == "combined":
        sub = f
    elif view == "blackout_only":
        sub = f[f["bucket"] == "full_blackout"]
    else:
        raise ValueError(f"unknown view: {view!r}")
    return (
        sub.groupby(["country", "iso3"], dropna=False)["duration_days"]
           .sum(min_count=1).reset_index()
           .sort_values("duration_days", ascending=False)
    )


def country_cost_rollup(frame: pd.DataFrame, year_range: tuple[int, int] | None = None) -> pd.DataFrame:
    """Total estimated shutdown cost per country (Top10VPN methodology).

    The analytic dataset attaches the per-(iso3, year) Top10VPN cost to every
    *event* row in that country-year — multiple events share one cost value.
    Summing `cost_usd` event-wise would over-count by the event-multiplicity
    factor; this helper first reduces to unique (iso3, year) pairs and sums
    those instead.

    Returns a DataFrame with columns ``country``, ``iso3``, ``total_cost_usd``,
    ``event_count``, ``total_shutdown_days``, sorted descending by cost.
    """
    f = frame.copy()
    if year_range is not None:
        lo, hi = year_range
        f = f[(f["year"] >= lo) & (f["year"] <= hi)]

    # Costs are country-year level — dedupe before summing.
    cost_per_country = (
        f.dropna(subset=["cost_usd"])
         .drop_duplicates(subset=["iso3", "year"])
         .groupby(["iso3"], dropna=False)["cost_usd"]
         .sum(min_count=1)
         .rename("total_cost_usd")
    )

    # Event-level metrics aggregate normally.
    events = (
        f.groupby(["iso3"], dropna=False)
         .agg(
             country=("country", "first"),
             event_count=("country", "size"),
             total_shutdown_days=("duration_days", "sum"),
         )
    )

    out = events.join(cost_per_country, how="left").reset_index()
    out = out[["country", "iso3", "total_cost_usd", "event_count", "total_shutdown_days"]]
    return out.sort_values("total_cost_usd", ascending=False, na_position="last")


def monthly_event_series(frame: pd.DataFrame) -> pd.DataFrame:
    """Monthly event counts and cumulative estimated cost.

    Cost time-series is built off `(iso3, year)` cost rows attributed to the
    first event of that country-year (avoids the event-multiplicity over-count).
    Months without events are filled with 0 / forward-filled cumulative cost so
    the line chart doesn't have gaps.
    """
    f = frame.copy()
    f["month"] = f["start_date"].dt.to_period("M").dt.to_timestamp()

    counts = (
        f.groupby("month").size().rename("event_count")
    )

    # Attribute each (iso3, year) cost to its earliest in-snapshot event month.
    cost_attr = (
        f.dropna(subset=["cost_usd"])
         .sort_values("start_date")
         .drop_duplicates(subset=["iso3", "year"])
         .groupby("month")["cost_usd"]
         .sum(min_count=1)
         .rename("monthly_cost_usd")
    )

    idx = pd.date_range(counts.index.min(), counts.index.max(), freq="MS")
    series = pd.concat([counts, cost_attr], axis=1).reindex(idx).rename_axis("month")
    series["event_count"] = series["event_count"].fillna(0).astype(int)
    series["monthly_cost_usd"] = series["monthly_cost_usd"].fillna(0.0)
    series["cumulative_cost_usd"] = series["monthly_cost_usd"].cumsum()
    return series.reset_index()
