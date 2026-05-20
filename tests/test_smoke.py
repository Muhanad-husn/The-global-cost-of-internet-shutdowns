"""Smoke tests — verify package imports, data paths, and the Access Now snapshot."""

EXPECTED_ACCESS_NOW_COLUMNS = {
    "country",
    "start_date",
    "end_date",
    "shutdown_type",
    "shutdown_status",
    "duration",
    "geo_scope",
    "region",
    "count_year",
}


def test_module_imports():
    """The project module imports without error."""
    import internet_shutdowns  # noqa: F401


def test_data_dirs_exist():
    """The data directories exist (auto-created on import of data.py)."""
    from internet_shutdowns.data import EXTERNAL_DIR, PROCESSED_DIR, RAW_DIR

    assert RAW_DIR.exists()
    assert PROCESSED_DIR.exists()
    assert EXTERNAL_DIR.exists()


def test_diagnostics_import():
    """The diagnostics helpers import."""
    from internet_shutdowns.diagnostics import (  # noqa: F401
        before_after,
        compare_alternatives,
        distribution_compare,
        distribution_summary,
        missingness_pattern,
        missingness_summary,
    )


def test_access_now_snapshot_loads():
    """The Access Now #KeepItOn snapshot loads and carries the expected core columns."""
    from internet_shutdowns.data import load_access_now_snapshot

    df = load_access_now_snapshot()
    assert not df.empty, "snapshot is empty"
    missing = EXPECTED_ACCESS_NOW_COLUMNS - set(df.columns)
    assert not missing, f"snapshot missing expected columns: {missing}"
    # Project scope is 2019+; the curated snapshot has ~1.7k in-scope rows.
    assert (df["count_year"] >= 2019).sum() > 500


EXPECTED_TOP10VPN_COLUMNS = {
    "country",
    "iso3",
    "year",
    "cost_usd",
    "duration_hours",
    "users_affected",
    "source",
}


def test_top10vpn_snapshot_loads():
    """The Top10VPN cost snapshot loads with the expected schema and year coverage."""
    from internet_shutdowns.data import load_top10vpn_snapshot

    df = load_top10vpn_snapshot()
    assert not df.empty, "Top10VPN snapshot is empty"
    missing = EXPECTED_TOP10VPN_COLUMNS - set(df.columns)
    assert not missing, f"Top10VPN snapshot missing expected columns: {missing}"
    # 2019–2025 inclusive should all be present.
    assert set(range(2019, 2026)).issubset(set(df["year"].unique()))
    # All rows except Somaliland (the de-facto state we keep unmapped) get ISO-3.
    unmapped = df.loc[df["iso3"].isna(), "country"].unique().tolist()
    assert unmapped == ["Somaliland"], f"unexpected unmapped countries: {unmapped}"


def test_worldbank_cached_call_returns_data():
    """World Bank API returns data for a sentinel country/year/indicator.

    Hits the v2 JSON API through requests-cache. The first run populates the
    sqlite cache at ``.cache/http_cache.sqlite``; subsequent runs are local.
    """
    from internet_shutdowns.data import load_worldbank_indicators

    df = load_worldbank_indicators(
        indicators=["NY.GDP.MKTP.CD"], years=range(2020, 2022)
    )
    assert not df.empty
    usa_2020 = df[(df["iso3"] == "USA") & (df["year"] == 2020)]
    assert len(usa_2020) == 1
    assert usa_2020["value"].iloc[0] > 1e13  # US GDP is ~$21T


def test_standardize_event_columns_shapes_frame():
    """standardize_event_columns adds canonical columns and splits multi-country rows."""
    from internet_shutdowns.clean import standardize_event_columns
    from internet_shutdowns.data import load_access_now_snapshot

    raw = load_access_now_snapshot()
    std = standardize_event_columns(raw)

    # Multi-country rows ("Cameroon; Central African Republic") split → row count grows.
    assert len(std) >= len(raw)
    for col in ("iso3", "type", "duration_hours", "platform_block", "platforms_affected"):
        assert col in std.columns, f"missing standardized column: {col}"

    # Type is the ordered categorical from the mapping; the headline values are present.
    assert set(std["type"].dropna().unique()).issubset({"full_blackout", "throttle", "other"})

    # No country-name should be ;-joined any more.
    assert not std["country"].astype("string").str.contains(";", na=False).any()

    # iso3 unresolved should be only Somaliland (per Decision Log #7 — kept as None).
    unresolved = set(std.loc[std["iso3"].isna(), "country"].unique())
    assert unresolved == {"Somaliland"}, f"unexpected unresolved countries: {unresolved}"


def test_dedupe_collapses_known_duplicates():
    """dedupe_events collapses the Ethiopia 2020-11-04 Tigray cluster (6 dup rows → 1)."""
    from internet_shutdowns.clean import dedupe_events, standardize_event_columns
    from internet_shutdowns.data import load_access_now_snapshot

    std = standardize_event_columns(load_access_now_snapshot())
    in_scope = std[std["count_year"] >= 2019].copy()

    before = len(in_scope)
    deduped = dedupe_events(in_scope, days_tolerance=0)
    after = len(deduped)

    # The conservative N=0 dedup collapses well over 100 rows in the 2019+ subset.
    assert after < before
    assert (before - after) > 100, f"only collapsed {before - after} rows"

    # The Ethiopia 2020-11-04 Tigray cluster (7 raw rows; 6 are duplicates of one event
    # and 1 is the distinct Wellega event) should collapse to exactly 2 events.
    tigray_cluster = deduped[
        (deduped["country"] == "Ethiopia")
        & (deduped["start_date"] == "2020-11-04")
        & (deduped["type"] == "full_blackout")
    ]
    assert len(tigray_cluster) == 2, (
        f"expected 2 distinct Ethiopia 2020-11-04 events (Tigray + Wellega), "
        f"got {len(tigray_cluster)}"
    )


def test_compute_duration_handles_missing_end_date():
    """compute_duration in 'hybrid' mode covers most rows and never goes negative."""
    from internet_shutdowns.clean import (
        compute_duration,
        dedupe_events,
        standardize_event_columns,
    )
    from internet_shutdowns.data import load_access_now_snapshot

    std = standardize_event_columns(load_access_now_snapshot())
    in_scope = std[std["count_year"] >= 2019].copy()
    deduped = dedupe_events(in_scope, days_tolerance=0)

    with_dur = compute_duration(deduped, missing_strategy="hybrid")
    for col in ("duration_days", "duration_source", "duration_imputed"):
        assert col in with_dur.columns

    days = with_dur["duration_days"].astype("Float64")
    # No negative durations after the sanity guard against bad raw values.
    assert (days.dropna() >= 0).all()
    # Hybrid recovers most rows (recorded + duration_field + snapshot_date for Ongoing).
    coverage = days.notna().mean()
    assert coverage > 0.75, f"hybrid coverage too low: {coverage:.0%}"

    # The two sentinel-strategy extremes should bracket hybrid in total shutdown-days.
    drop_total = compute_duration(deduped, missing_strategy="drop")["duration_days"].astype("Float64").sum()
    snap_total = compute_duration(deduped, missing_strategy="snapshot_date")["duration_days"].astype("Float64").sum()
    hybrid_total = days.sum()
    assert drop_total < hybrid_total < snap_total


def test_top10_bar_renders_with_caveat():
    """The hero figure surfaces the Top10VPN methodology caveat in its title.

    Cost figures are reported, not endorsed (CLAUDE.md "Done definition"). The
    caveat must travel with the figure — including the static `figures/hero.png`
    export — even if the dashboard banner repeats it.
    """
    import pandas as pd

    from internet_shutdowns.data import PROCESSED_DIR
    from internet_shutdowns.viz import METHODOLOGY_CAVEAT, top10_bar

    analytic = PROCESSED_DIR / "analytic_dataset_2026-05-20.parquet"
    if not analytic.exists():
        import pytest

        pytest.skip(f"analytic dataset not built — expected {analytic}")

    df = pd.read_parquet(analytic)
    fig = top10_bar(df, metric="total_cost_usd")

    title = fig.layout.title.text
    assert METHODOLOGY_CAVEAT in title, f"caveat missing from title: {title!r}"
    # 10 bars on a horizontal bar chart.
    assert len(fig.data[0].y) == 10


def test_analytic_dataset_end_to_end():
    """The shipped analytic dataset has the contract S5+ depends on.

    Per Decision Log #17, S5 (viz) and S6 (dashboard) read this parquet
    rather than re-running ``clean.py``. The smoke test pins the contract:
    expected columns are present, row count is in range, and the rollups
    produce a Top10VPN top-10 that contains the headline countries.
    """
    import pandas as pd
    import pytest

    from internet_shutdowns.data import PROCESSED_DIR
    from internet_shutdowns.rollups import country_cost_rollup

    analytic = PROCESSED_DIR / "analytic_dataset_2026-05-20.parquet"
    if not analytic.exists():
        pytest.skip(f"analytic dataset not built — expected {analytic}")

    df = pd.read_parquet(analytic)
    assert 1000 < len(df) < 3000, f"unexpected row count: {len(df)}"

    expected = {
        "country", "iso3", "year", "start_date", "type", "platform_block",
        "duration_days", "duration_imputed", "cost_usd", "gdp_usd",
        "internet_pct", "population",
    }
    missing = expected - set(df.columns)
    assert not missing, f"analytic dataset missing columns: {missing}"

    # Cost rollup must dedupe (iso3, year) before summing — naive .sum() would
    # over-count by event multiplicity (Decision Log #19). The headline-cost
    # top-10 from S4/S5 must remain stable.
    cost = country_cost_rollup(df).dropna(subset=["total_cost_usd"])
    headline = set(cost.head(10)["iso3"])
    expected_headline = {"RUS", "MMR", "IND", "VEN", "IRQ", "SDN", "PAK", "IRN", "ETH", "NGA"}
    assert headline == expected_headline, (
        f"headline cost top-10 has drifted: {sorted(headline)} "
        f"vs. {sorted(expected_headline)}"
    )


def test_dashboard_module_imports():
    """The Streamlit dashboard module imports without executing the app.

    Streamlit apps don't lend themselves to running-server smoke tests, but
    an import-time error (typo, missing helper, schema-mismatch in a helper
    call evaluated at module scope) would still surface here.
    """
    import importlib.util
    from pathlib import Path

    app_path = Path(__file__).resolve().parents[1] / "app" / "streamlit_dashboard.py"
    assert app_path.exists(), f"dashboard module not found at {app_path}"

    spec = importlib.util.spec_from_file_location("streamlit_dashboard", app_path)
    module = importlib.util.module_from_spec(spec)
    # Streamlit calls during module execution are no-ops without a running
    # server; the heavy lifting is data-load + viz, which must succeed here.
    spec.loader.exec_module(module)
    # load_analytic is the data-contract surface for the dashboard.
    assert hasattr(module, "load_analytic")


def test_gadm_loads():
    """GADM admin-0 polygons load — skipped if the (~50 MB) file isn't fetched."""
    import pytest

    from internet_shutdowns.data import GADM_ADMIN0_PATH, load_gadm_countries

    if not GADM_ADMIN0_PATH.exists():
        pytest.skip(
            f"GADM file not on disk at {GADM_ADMIN0_PATH}. "
            f"Run load_gadm_countries(fetch_if_missing=True) once to fetch."
        )
    gdf = load_gadm_countries()
    assert len(gdf) > 200  # ~250 admin-0 polygons worldwide
    assert "geometry" in gdf.columns
