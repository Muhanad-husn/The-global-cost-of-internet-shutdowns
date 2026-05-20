"""Data loading utilities with HTTP caching.

All API calls go through a memoized session so notebooks re-run fast.
Paths are resolved relative to the project root (the folder containing pyproject.toml).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import pycountry
import requests_cache

# This file lives at src/<project>/data.py
# parents[0] = src/<project>/
# parents[1] = src/
# parents[2] = project root
ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR = DATA_DIR / "external"
FIGURES_DIR = ROOT / "figures"
CACHE_DIR = ROOT / ".cache"

for _d in (RAW_DIR, PROCESSED_DIR, EXTERNAL_DIR, FIGURES_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Shared HTTP cache for the project (gitignored).
# Expires after 30 days by default — override per-call if needed.
session = requests_cache.CachedSession(
    cache_name=str(CACHE_DIR / "http_cache"),
    backend="sqlite",
    expire_after=60 * 60 * 24 * 30,
    allowable_methods=("GET", "HEAD"),
)


def download_file(url: str, dest: str | Path, force: bool = False) -> Path:
    """Download a file to ``dest``, using the cached session.

    Parameters
    ----------
    url
        Source URL.
    dest
        Destination path. Relative paths are resolved against ``RAW_DIR``.
    force
        If True, re-download even if the local file exists.

    Returns
    -------
    Path
        Absolute path to the downloaded file.
    """
    dest = Path(dest)
    if not dest.is_absolute():
        dest = RAW_DIR / dest
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force:
        return dest

    resp = session.get(url, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    return dest


def read_processed(name: str) -> pd.DataFrame:
    """Read a parquet from ``data/processed/<name>.parquet``."""
    return pd.read_parquet(PROCESSED_DIR / f"{name}.parquet")


def write_processed(df: pd.DataFrame, name: str) -> Path:
    """Write a DataFrame to ``data/processed/<name>.parquet``."""
    path = PROCESSED_DIR / f"{name}.parquet"
    df.to_parquet(path, index=False)
    return path


# ---------------------------------------------------------------------------
# Source loaders
# ---------------------------------------------------------------------------

ACCESS_NOW_SNAPSHOT_DATE = "2026-05-20"


def load_access_now_snapshot(date: str = ACCESS_NOW_SNAPSHOT_DATE) -> pd.DataFrame:
    """Load the dated Access Now #KeepItOn STOP snapshot.

    The snapshot is the curated "Combined (2016-2025)" view, with a
    ``count_year`` attribution column. See ``data/processed/SNAPSHOTS.md``.
    """
    return read_processed(f"access_now_snapshot_{date}")


# ---------------------------------------------------------------------------
# Top10VPN
# ---------------------------------------------------------------------------

TOP10VPN_SNAPSHOT_DATE = "2026-05-20"

# Manual ISO-3 overrides for Top10VPN country labels that pycountry can't
# resolve directly (alternate naming, sub-national entries, contested states).
# A value of ``None`` means "intentionally not assigned" — Somaliland is a
# de-facto state that Top10VPN reports separately but that the World Bank /
# GADM do not recognize, so we keep it distinct rather than collapsing it.
_TOP10VPN_ISO3_OVERRIDES: dict[str, str | None] = {
    "Congo DRC": "COD",
    "DRC": "COD",
    "Republic of Congo": "COG",
    "Pakistan - Azad Kashmir": "PAK",  # sub-national report — joins to Pakistan
    "eSwatini": "SWZ",
    # pycountry's bundled data uses "Türkiye" and "Russian Federation" only;
    # the common English short names below don't resolve via .lookup(). Pin both.
    "Turkey": "TUR",
    "Russia": "RUS",
    # Somaliland is a de-facto state not in ISO-3166; keep it distinct rather
    # than collapsing it into SOM.
    "Somaliland": None,
}


def _country_to_iso3(name: str) -> str | None:
    """Best-effort country-name → ISO-3 resolution with explicit overrides."""
    if name in _TOP10VPN_ISO3_OVERRIDES:
        return _TOP10VPN_ISO3_OVERRIDES[name]
    try:
        match = pycountry.countries.lookup(name)
        return match.alpha_3
    except LookupError:
        return None


def load_top10vpn_csvs(raw_dir: str | Path = RAW_DIR) -> pd.DataFrame:
    """Load and concatenate the hand-transcribed Top10VPN annual CSVs.

    Globs ``top10vpn_*.csv`` under ``raw_dir`` (default: ``data/raw/``).
    Each CSV is expected to carry the columns ``country``, ``cost_usd``,
    ``duration_hours``, ``users_affected``, ``year``.

    Adds:
    - ``iso3``: pycountry-resolved ISO-3 with manual overrides (see
      ``_TOP10VPN_ISO3_OVERRIDES``). ``None`` where the entity is not a
      recognized country (e.g. Somaliland).
    - ``source``: literal "top10vpn", for joins downstream.
    """
    raw_dir = Path(raw_dir)
    files = sorted(raw_dir.glob("top10vpn_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No top10vpn_*.csv files found in {raw_dir}. "
            "Hand-transcribed annual CSVs are committed to data/raw/."
        )
    frames = [pd.read_csv(f) for f in files]
    df = pd.concat(frames, ignore_index=True)

    expected = {"country", "cost_usd", "duration_hours", "users_affected", "year"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Top10VPN CSVs missing columns: {missing}")

    df["iso3"] = df["country"].map(_country_to_iso3).astype("string")
    df["country"] = df["country"].astype("string")
    df["source"] = "top10vpn"
    df["source"] = df["source"].astype("string")
    df = df[["country", "iso3", "year", "cost_usd", "duration_hours", "users_affected", "source"]]
    df = df.sort_values(["year", "cost_usd"], ascending=[True, False]).reset_index(drop=True)
    return df


def load_top10vpn_snapshot(date: str = TOP10VPN_SNAPSHOT_DATE) -> pd.DataFrame:
    """Load the dated Top10VPN cost snapshot from ``data/processed/``."""
    return read_processed(f"top10vpn_snapshot_{date}")


# ---------------------------------------------------------------------------
# World Bank Indicators v2 API
# ---------------------------------------------------------------------------

# Default indicators relevant to the LMIC framing:
#   NY.GDP.MKTP.CD   GDP (current USD) — denominator for cost_pct_gdp
#   IT.NET.USER.ZS   Individuals using the Internet (% of population)
#   SP.POP.TOTL      Population, total
WB_INDICATORS_DEFAULT = ("NY.GDP.MKTP.CD", "IT.NET.USER.ZS", "SP.POP.TOTL")
WB_API_BASE = "https://api.worldbank.org/v2"


def load_worldbank_indicators(
    indicators: Iterable[str] = WB_INDICATORS_DEFAULT,
    years: Iterable[int] = range(2019, 2026),
) -> pd.DataFrame:
    """Fetch World Bank indicators in long form via the cached HTTP session.

    Returns columns: ``iso3``, ``country``, ``year``, ``indicator``, ``value``.

    The WB v2 API uses ISO-3 alpha codes; we pass ``all`` to fetch every country
    in one paginated call per indicator. Cache TTL is the project default
    (30 days) — indicators are stable enough that aggressive caching is safe.
    """
    years = list(years)
    year_range = f"{min(years)}:{max(years)}"
    frames = []
    for ind in indicators:
        page = 1
        while True:
            url = f"{WB_API_BASE}/country/all/indicator/{ind}"
            params = {
                "date": year_range,
                "format": "json",
                "per_page": 1000,
                "page": page,
            }
            resp = session.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
            if not isinstance(payload, list) or len(payload) < 2:
                break
            meta, rows = payload[0], payload[1]
            if not rows:
                break
            for r in rows:
                frames.append(
                    {
                        "iso3": r.get("countryiso3code") or None,
                        "country": (r.get("country") or {}).get("value"),
                        "year": int(r["date"]) if r.get("date") else None,
                        "indicator": ind,
                        "value": r.get("value"),
                    }
                )
            if page >= meta.get("pages", 1):
                break
            page += 1
    df = pd.DataFrame(frames)
    if df.empty:
        return df
    # Drop aggregate rows (regions/income groups) which have empty iso3.
    df = df[df["iso3"].astype(bool)].copy()
    df["iso3"] = df["iso3"].astype("string")
    df["country"] = df["country"].astype("string")
    df["indicator"] = df["indicator"].astype("string")
    df = df.sort_values(["indicator", "iso3", "year"]).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# GADM 4.1 country boundaries
# ---------------------------------------------------------------------------

# Per-level GADM file (admin-0 world): ~50 MB. Heavy enough to be gitignored.
GADM_ADMIN0_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/gadm_410-levels.gpkg"
GADM_ADMIN0_PATH = RAW_DIR / "gadm_world_admin0.gpkg"


def load_gadm_countries(
    level: int = 0,
    path: str | Path = GADM_ADMIN0_PATH,
    fetch_if_missing: bool = False,
):
    """Load GADM 4.1 country (admin-0) polygons as a GeoDataFrame.

    The GADM world file is ~50 MB and is intentionally not committed; pass
    ``fetch_if_missing=True`` on first call to download from
    ``geodata.ucdavis.edu``. Subsequent calls read from the local copy.

    Returns a ``geopandas.GeoDataFrame`` with the GADM admin-0 layer.
    """
    import geopandas as gpd  # local import — geopandas is in the "geo" extra

    path = Path(path)
    if not path.exists():
        if not fetch_if_missing:
            raise FileNotFoundError(
                f"GADM file not found at {path}. "
                f"Call load_gadm_countries(fetch_if_missing=True) once to fetch "
                f"({GADM_ADMIN0_URL}, ~50 MB)."
            )
        download_file(GADM_ADMIN0_URL, path)

    layer = f"ADM_{level}"
    return gpd.read_file(path, layer=layer)


# ---------------------------------------------------------------------------
# Convenience: load everything at once
# ---------------------------------------------------------------------------


def load_all(
    require_gadm: bool = False,
    wb_years: Iterable[int] = range(2019, 2026),
) -> dict[str, pd.DataFrame]:
    """Return all four project sources as a dict.

    ``shutdowns`` and ``costs`` come from committed parquet snapshots;
    ``wb`` is fetched live (cached); ``boundaries`` is included only if the
    GADM file is already on disk, unless ``require_gadm=True``.
    """
    out: dict[str, pd.DataFrame] = {
        "shutdowns": load_access_now_snapshot(),
        "costs": load_top10vpn_snapshot(),
        "wb": load_worldbank_indicators(years=wb_years),
    }
    if require_gadm or GADM_ADMIN0_PATH.exists():
        out["boundaries"] = load_gadm_countries(fetch_if_missing=require_gadm)
    return out
