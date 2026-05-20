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
