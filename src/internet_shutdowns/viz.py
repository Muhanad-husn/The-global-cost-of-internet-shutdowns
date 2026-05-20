"""Plotly visualization helpers for the internet-shutdowns analysis.

Three reusable figures, called from both `notebooks/02_main.ipynb` (§12) and
`app/streamlit_dashboard.py` (S6):

- :func:`world_choropleth` — country-level shutdown-days or estimated cost.
- :func:`time_series` — monthly event count + cumulative estimated cost.
- :func:`top10_bar` — hero figure (top-10 countries by total estimated cost),
  with the Top10VPN methodology caveat baked into the title.

Cost figures throughout are *reported under Top10VPN's methodology, which is
debated* — see CLAUDE.md and the README "Limitations" section. The caveat
string is exported as :data:`METHODOLOGY_CAVEAT` so the dashboard can surface
it consistently in tab titles and banners.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from .rollups import country_cost_rollup, monthly_event_series, shutdown_day_rollup

pio.templates.default = "plotly_white"

ROOT = Path(__file__).resolve().parents[2]
FIGURES_DIR = ROOT / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

METHODOLOGY_CAVEAT = "Top10VPN methodology — see limitations"

# Short display names for chart labels. The Access Now / WB feeds use formal
# UN names (e.g. "Russian Federation", "Iran (Islamic Republic of)") which run
# off the page at LinkedIn thumbnail size — `display_country` swaps these for
# the conventional short form. Hover names and ISO-3 codes are unchanged.
_DISPLAY_COUNTRY_OVERRIDES = {
    "Russian Federation": "Russia",
    "Iran (Islamic Republic of)": "Iran",
    "Venezuela (Bolivarian Republic of)": "Venezuela",
    "Syrian Arab Republic": "Syria",
    "Lao People's Democratic Republic": "Laos",
    "Democratic Republic of the Congo": "DR Congo",
    "United Republic of Tanzania": "Tanzania",
    "Bolivia (Plurinational State of)": "Bolivia",
    "Republic of Korea": "South Korea",
    "Democratic People's Republic of Korea": "North Korea",
    "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
    "United States of America": "United States",
}


def display_country(name: str | None) -> str | None:
    """Short display label for chart axes (formal UN name → conventional short form)."""
    if name is None:
        return None
    return _DISPLAY_COUNTRY_OVERRIDES.get(name, name)

ChoroplethMetric = Literal["total_shutdown_days", "total_cost_usd", "event_count"]
TimeSeriesMetric = Literal["event_count", "cumulative_cost"]


def world_choropleth(
    df: pd.DataFrame,
    metric: ChoroplethMetric = "total_shutdown_days",
    year_range: tuple[int, int] | None = None,
) -> go.Figure:
    """World choropleth of shutdown activity by country.

    Reads the analytic dataset shape. Built-in Plotly country layer is used
    (no GADM dep at viz time); ISO-3 codes drive the join. Somaliland (iso3
    None per Decision Log #7) is dropped silently — it has no ISO map polygon.
    """
    f = df.copy()
    if year_range is not None:
        lo, hi = year_range
        f = f[(f["year"] >= lo) & (f["year"] <= hi)]

    if metric == "total_cost_usd":
        rollup = country_cost_rollup(f, year_range=year_range)
        value_col = "total_cost_usd"
        title = f"Estimated shutdown cost by country ({METHODOLOGY_CAVEAT})"
        colorbar_title = "Cost (USD)"
    elif metric == "total_shutdown_days":
        rollup = shutdown_day_rollup(f, view="combined").rename(
            columns={"duration_days": "total_shutdown_days"}
        )
        value_col = "total_shutdown_days"
        title = "Total shutdown-days by country"
        colorbar_title = "Days"
    elif metric == "event_count":
        rollup = (
            f.groupby(["country", "iso3"], dropna=False)
             .size().reset_index(name="event_count")
        )
        value_col = "event_count"
        title = "Number of recorded shutdown events by country"
        colorbar_title = "Events"
    else:
        raise ValueError(f"unknown metric: {metric!r}")

    rollup = rollup.dropna(subset=["iso3"])

    fig = px.choropleth(
        rollup,
        locations="iso3",
        color=value_col,
        hover_name="country",
        color_continuous_scale="Reds",
        labels={value_col: colorbar_title},
        title=title,
    )
    fig.update_geos(showcoastlines=True, showframe=False, projection_type="natural earth")
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 50, "b": 0},
        coloraxis_colorbar={"title": colorbar_title},
    )
    return fig


def time_series(
    df: pd.DataFrame,
    metric: TimeSeriesMetric = "event_count",
) -> go.Figure:
    """Monthly event count OR cumulative estimated cost over time.

    Built off `monthly_event_series` so the same time index drives both
    metrics — switching `metric` swaps the y-axis on the same x grid.
    """
    series = monthly_event_series(df)

    if metric == "event_count":
        y_col = "event_count"
        y_title = "Recorded shutdown events"
        title = "Monthly recorded shutdown events"
    elif metric == "cumulative_cost":
        y_col = "cumulative_cost_usd"
        y_title = "Cumulative cost (USD)"
        title = f"Cumulative estimated shutdown cost ({METHODOLOGY_CAVEAT})"
    else:
        raise ValueError(f"unknown metric: {metric!r}")

    fig = px.line(series, x="month", y=y_col, title=title, labels={"month": "", y_col: y_title})
    fig.update_traces(mode="lines+markers", line={"width": 2})
    fig.update_layout(margin={"l": 50, "r": 20, "t": 50, "b": 40})
    return fig


def top10_bar(
    df: pd.DataFrame,
    metric: Literal["total_cost_usd", "total_shutdown_days"] = "total_cost_usd",
    year_range: tuple[int, int] | None = (2019, 2025),
    caveat_in_title: bool = True,
) -> go.Figure:
    """Hero figure: top-10 countries by metric.

    For ``metric="total_cost_usd"`` the title always carries the Top10VPN
    methodology caveat — this is the headline cost chart and the caveat is
    load-bearing (CLAUDE.md "Done definition"). Set
    ``caveat_in_title=False`` only for the rare case where the caveat is
    surfaced elsewhere (e.g. a dashboard banner above the chart) — even then
    `metric="total_cost_usd"` keeps a brief caveat note.
    """
    if metric == "total_cost_usd":
        rollup = country_cost_rollup(df, year_range=year_range).head(10)
        value_col = "total_cost_usd"
        x_title = "Estimated cost (USD)"
        base_title = "Top 10 countries by estimated shutdown cost"
    elif metric == "total_shutdown_days":
        rollup = shutdown_day_rollup(df, view="combined").head(10).rename(
            columns={"duration_days": "total_shutdown_days"}
        )
        value_col = "total_shutdown_days"
        x_title = "Total shutdown-days"
        base_title = "Top 10 countries by total shutdown-days"
    else:
        raise ValueError(f"unknown metric: {metric!r}")

    if year_range is not None:
        lo, hi = year_range
        base_title = f"{base_title}, {lo}–{hi}"

    if metric == "total_cost_usd":
        # Caveat is always tagged on cost figures, even when the dashboard
        # banner repeats it — better redundant than missing on a shared PNG.
        title = f"{base_title}<br><sup>{METHODOLOGY_CAVEAT}</sup>"
    elif caveat_in_title:
        title = f"{base_title}<br><sup>{METHODOLOGY_CAVEAT}</sup>"
    else:
        title = base_title

    rollup = rollup.assign(country=rollup["country"].map(display_country))
    plot_df = rollup.iloc[::-1]  # horizontal bar reads top→bottom by largest

    if metric == "total_cost_usd":
        plot_df = plot_df.assign(
            _label=plot_df[value_col].map(_format_usd_short)
        )
    else:
        plot_df = plot_df.assign(
            _label=plot_df[value_col].map(lambda v: f"{v:,.0f}")
        )

    fig = px.bar(
        plot_df,
        x=value_col,
        y="country",
        orientation="h",
        title=title,
        labels={value_col: x_title, "country": ""},
        text="_label",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        margin={"l": 20, "r": 130, "t": 90, "b": 50},
        title={"x": 0.02, "xanchor": "left"},
        uniformtext_minsize=11,
        uniformtext_mode="show",
    )
    if metric == "total_cost_usd":
        fig.update_xaxes(
            showgrid=True, gridcolor="#eee",
            tickprefix="$", ticksuffix="B",
            tickvals=[0, 5e9, 10e9, 15e9, 20e9, 25e9, 30e9, 35e9, 40e9],
            ticktext=["0", "5", "10", "15", "20", "25", "30", "35", "40"],
        )
    else:
        fig.update_xaxes(showgrid=True, gridcolor="#eee")
    return fig


def _format_usd_short(value: float) -> str:
    """Compact USD label for chart bars — `$37.5B`, `$420M`, `$1.2K`."""
    if value is None or pd.isna(value):
        return ""
    v = float(value)
    if abs(v) >= 1e9:
        return f"${v / 1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:.0f}M"
    if abs(v) >= 1e3:
        return f"${v / 1e3:.1f}K"
    return f"${v:.0f}"


def save_figure(fig, name: str, *, width: int = 800, height: int = 800, scale: int = 2) -> Path:
    """Save a Plotly figure to ``figures/<name>.png`` via kaleido.

    Defaults to 800×800 @2x — the LinkedIn-thumbnail constraint from CLAUDE.md.
    Also handles matplotlib / plotnine figures for backwards compatibility
    with template scaffolding.
    """
    path = FIGURES_DIR / f"{name}.png"

    if hasattr(fig, "write_image"):
        fig.write_image(str(path), width=width, height=height, scale=scale)
    elif hasattr(fig, "save"):
        fig.save(str(path), dpi=200, verbose=False)
    elif hasattr(fig, "savefig"):
        fig.savefig(path, dpi=200, bbox_inches="tight")
    else:
        raise TypeError(f"Don't know how to save figure of type {type(fig)!r}")

    return path
