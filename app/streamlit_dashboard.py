"""Streamlit dashboard for internet shutdowns 2019–latest.

Headline interactive deliverable. Reads ``data/processed/analytic_dataset_<date>.parquet``
and reuses the Plotly viz helpers from :mod:`internet_shutdowns.viz` plus the
rollups from :mod:`internet_shutdowns.rollups` — there is one rollup code path
for the static hero figure and the dashboard.

The Top10VPN methodology caveat is surfaced in a persistent banner above the
tabs; every cost figure carries the caveat in its title as well (CLAUDE.md
"Done definition"). Run with::

    streamlit run app/streamlit_dashboard.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from internet_shutdowns.rollups import (
    country_cost_rollup,
    monthly_event_series,
    shutdown_day_rollup,
)
from internet_shutdowns.viz import (
    METHODOLOGY_CAVEAT,
    display_country,
    time_series,
    top10_bar,
    world_choropleth,
)

ROOT = Path(__file__).resolve().parents[1]
ANALYTIC_PARQUET = ROOT / "data" / "processed" / "analytic_dataset_2026-05-20.parquet"

st.set_page_config(
    page_title="Internet shutdowns 2019–2025",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_analytic() -> pd.DataFrame:
    return pd.read_parquet(ANALYTIC_PARQUET)


df = load_analytic()

# --- Sidebar -----------------------------------------------------------------

st.sidebar.header("Filters")

year_min, year_max = int(df["year"].min()), int(df["year"].max())
year_range = st.sidebar.slider(
    "Year range",
    min_value=year_min,
    max_value=year_max,
    value=(year_min, year_max),
    step=1,
)

view_mode = st.sidebar.radio(
    "Shutdown-day view",
    options=["combined", "separated"],
    index=0,
    help=(
        "Combined matches Top10VPN's country/year aggregation. "
        "Separated splits by bucket (full blackout / throttle / platform block) — "
        "reveals that 70–100% of shutdown-days in top countries are non-blackout."
    ),
)

countries_all = sorted(df["country"].dropna().unique().tolist())
selected_countries = st.sidebar.multiselect(
    "Countries (empty = all)",
    options=countries_all,
    default=[],
)

# Apply filters
mask = (df["year"] >= year_range[0]) & (df["year"] <= year_range[1])
if selected_countries:
    mask &= df["country"].isin(selected_countries)
df_f = df[mask].copy()

st.sidebar.markdown("---")
st.sidebar.caption(
    f"**Snapshot:** Access Now + Top10VPN @ 2026-05-20  \n"
    f"**Filtered rows:** {len(df_f):,} of {len(df):,}"
)

# --- Header + caveat banner --------------------------------------------------

st.title("The global cost of internet shutdowns, 2019–2025")
st.warning(
    f"⚠️ **Methodology caveat.** Cost figures shown throughout are reported "
    f"under **Top10VPN's methodology, which is debated** ({METHODOLOGY_CAVEAT}). "
    f"Top10VPN applies a top-down formula "
    f"(GDP × digital-economy share × duration × affected population). "
    f"Critics argue this overstates impact in cash-economy contexts and "
    f"understates indirect effects (civic mobilization, remittance flows). "
    f"Cost figures here are a *reported, debated input* — not an endorsed estimate."
)

# --- Tabs --------------------------------------------------------------------

tab_map, tab_drill, tab_ts, tab_top10 = st.tabs(
    ["🗺️ World Map", "🔍 Country Drill-down", "📈 Time Series", "🏆 Top 10"]
)

# === Tab 1: World Map ========================================================
with tab_map:
    st.subheader("Where and how heavily are shutdowns hitting?")

    metric_label = st.selectbox(
        "Metric",
        options=[
            ("Total shutdown-days", "total_shutdown_days"),
            ("Estimated cost (USD, Top10VPN)", "total_cost_usd"),
            ("Number of recorded events", "event_count"),
        ],
        format_func=lambda x: x[0],
        index=0,
    )
    metric_key = metric_label[1]

    fig_map = world_choropleth(df_f, metric=metric_key, year_range=year_range)
    st.plotly_chart(fig_map, use_container_width=True)

    if metric_key == "total_cost_usd":
        st.caption(
            "Countries with NaN cost (26 iso3s including UAE, Saudi Arabia, "
            "China, UK, USA) appear on the map only where they have a "
            "Top10VPN cost row — Access Now records events the cost report "
            "doesn't price, and vice versa. See README *Limitations*."
        )

# === Tab 2: Country Drill-down ===============================================
with tab_drill:
    st.subheader("Per-country event timeline")

    available_countries = sorted(df_f["country"].dropna().unique().tolist())
    if not available_countries:
        st.info("No events match the current filters.")
    else:
        # Default to the highest-cost country in the current filter for impact.
        default_idx = 0
        try:
            top = country_cost_rollup(df_f, year_range=year_range)
            top_country = top["country"].iloc[0]
            if top_country in available_countries:
                default_idx = available_countries.index(top_country)
        except Exception:
            pass

        country = st.selectbox(
            "Country",
            options=available_countries,
            index=default_idx,
        )
        sub = df_f[df_f["country"] == country].copy()

        col1, col2, col3 = st.columns(3)
        col1.metric("Recorded events", f"{len(sub):,}")
        col2.metric(
            "Total shutdown-days",
            f"{sub['duration_days'].sum(min_count=1):,.0f}"
            if sub["duration_days"].notna().any() else "—",
        )
        # Country-year cost dedupe — never sum cost_usd raw at event level.
        cost_sub = sub.dropna(subset=["cost_usd"]).drop_duplicates(["iso3", "year"])
        total_cost = cost_sub["cost_usd"].sum() if not cost_sub.empty else None
        col3.metric(
            f"Total estimated cost ({METHODOLOGY_CAVEAT.split('—')[0].strip()})",
            f"${total_cost / 1e9:.2f}B" if total_cost else "Not priced",
        )

        # Gantt-style event timeline. End-date can be NaT (ongoing/unknown); fall
        # back to start+duration so the bar has some length, else a 1-day bar.
        timeline = sub.dropna(subset=["start_date"]).copy()
        if not timeline.empty:
            end_proxy = timeline["end_date"]
            if timeline["duration_days"].notna().any():
                end_proxy = end_proxy.fillna(
                    timeline["start_date"]
                    + pd.to_timedelta(timeline["duration_days"].fillna(1), unit="D")
                )
            end_proxy = end_proxy.fillna(timeline["start_date"] + pd.Timedelta(days=1))
            timeline = timeline.assign(end_for_plot=end_proxy)
            # Stable y label per event
            timeline = timeline.assign(
                label=(
                    timeline["area_name"].fillna(timeline["region"]).fillna("national")
                    + " · " + timeline["start_date"].dt.strftime("%Y-%m-%d")
                )
            ).sort_values("start_date")

            fig_gantt = px.timeline(
                timeline,
                x_start="start_date",
                x_end="end_for_plot",
                y="label",
                color="type",
                hover_data={
                    "shutdown_type": True,
                    "shutdown_status": True,
                    "actual_cause": True,
                    "duration_days": ":.1f",
                    "platform_block": True,
                    "label": False,
                },
                title=f"Recorded shutdown events — {display_country(country)}",
                color_discrete_map={
                    "full_blackout": "#c0392b",
                    "throttle": "#e67e22",
                    "other": "#7f8c8d",
                },
            )
            fig_gantt.update_yaxes(autorange="reversed", title="")
            fig_gantt.update_layout(
                margin={"l": 0, "r": 20, "t": 50, "b": 40},
                height=max(300, 22 * len(timeline) + 100),
            )
            st.plotly_chart(fig_gantt, use_container_width=True)
        else:
            st.info("No events with a parseable start date for this country.")

        with st.expander("Event-level details", expanded=False):
            cols_to_show = [
                "start_date", "end_date", "duration_days", "duration_source",
                "type", "platform_block", "platforms_affected",
                "area_name", "geo_scope", "shutdown_status",
                "actual_cause", "gov_justification",
                "cost_usd", "internet_pct", "gdp_usd",
                "an_link",
            ]
            existing = [c for c in cols_to_show if c in sub.columns]
            st.dataframe(
                sub[existing].sort_values("start_date", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

# === Tab 3: Time Series ======================================================
with tab_ts:
    st.subheader("Trend over time")

    ts_metric = st.radio(
        "Series",
        options=[
            ("Monthly event count", "event_count"),
            ("Cumulative estimated cost (Top10VPN)", "cumulative_cost"),
        ],
        format_func=lambda x: x[0],
        horizontal=True,
        index=0,
    )
    ts_key = ts_metric[1]

    fig_ts = time_series(df_f, metric=ts_key)
    st.plotly_chart(fig_ts, use_container_width=True)

    if ts_key == "event_count":
        series = monthly_event_series(df_f)
        st.caption(
            f"Recorded events in the filtered window: "
            f"**{int(series['event_count'].sum()):,}** "
            f"across {series['month'].nunique()} months. "
            "Trend in recorded counts is partly trend in *reporting* — "
            "see README *Limitations*."
        )

# === Tab 4: Top 10 ===========================================================
with tab_top10:
    st.subheader("Headline ranking")

    bar_metric = st.radio(
        "Rank by",
        options=[
            ("Estimated cost (USD, Top10VPN)", "total_cost_usd"),
            ("Total shutdown-days", "total_shutdown_days"),
        ],
        format_func=lambda x: x[0],
        horizontal=True,
        index=0,
    )
    bar_key = bar_metric[1]

    fig_bar = top10_bar(df_f, metric=bar_key, year_range=year_range)
    st.plotly_chart(fig_bar, use_container_width=True)

    if bar_key == "total_cost_usd":
        st.caption(
            "Cost figures attributed at the (country × year) level then summed "
            "— event-level summation would over-count by event multiplicity. "
            "See Decision Log #19 in IMPLEMENTATION_PLAN.md."
        )
    else:
        rollup = shutdown_day_rollup(df_f, view=view_mode)
        if view_mode == "separated" and not rollup.empty:
            st.caption(
                "Sidebar set to **separated** view — bucket-level totals are "
                "expanded below."
            )
            st.dataframe(
                rollup.assign(country=rollup["country"].map(display_country))
                      .sort_values("duration_days", ascending=False)
                      .head(30),
                use_container_width=True,
                hide_index=True,
            )
