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
