# Data snapshots

This project pins dated snapshots of revisable sources so that re-running the
notebook six months later produces identical numbers. Whenever a new snapshot
is taken, append a row below and add a revision-magnitude diagnostic to
`notebooks/03_robustness.ipynb`.

## Active snapshots

| Snapshot file | Source | Access date | Source URL | Notes |
|---|---|---|---|---|
| `access_now_snapshot_2026-05-20.parquet` | Access Now #KeepItOn STOP dataset | 2026-05-20 | https://www.accessnow.org/keepiton-data-spreadsheet → Google Sheet ID `1DvPAuHNLp5BXGb0nnZDGNoiIwEeu2ogdXEIDvT4Hyfk` (XLSX export) | 2,102 rows × 47 cols; sourced from the **"Combined (2016-2025)"** sheet, which carries Access Now's curated cross-year view and a `count_year` attribution column. Per-year sheets duplicate "ongoing since" events from earlier years and were not used. Object columns cast to `string` for parquet stability; `start_date`/`end_date` coerced to `datetime` (2 unparseable `end_date` values coerced to NaT — true "ongoing" status lives in `shutdown_status`, not `end_date`). Project scope is 2019+ (1,704 rows). |
| `top10vpn_snapshot_2026-05-20.parquet` | Top10VPN "Cost of internet shutdowns" annual reports 2019–2025 | 2026-05-20 | https://www.top10vpn.com/research/cost-of-internet-shutdowns/ | 169 rows × 7 cols. Hand-transcribed from each year's annual HTML report into `data/raw/top10vpn_<year>.csv` (one CSV per year, columns `country, cost_usd, duration_hours, users_affected, year`). Loader (`load_top10vpn_csvs`) concatenates all years, adds an `iso3` column via `pycountry` plus a small override map (`Turkey→TUR`, `Russia→RUS`, `Congo DRC`/`DRC→COD`, `Republic of Congo→COG`, `Pakistan - Azad Kashmir→PAK`, `eSwatini→SWZ`). Somaliland (1 row, 2022) is intentionally left without ISO-3 because it is a de-facto state that the World Bank / GADM do not recognize. **Methodology caveat: Top10VPN's top-down formula (GDP × digital-economy contribution × shutdown duration × affected-population share) is widely cited and widely contested — figures are reported here as a debated input, not endorsed.** |
| `analytic_dataset_2026-05-20.parquet` | **Derived.** Cleaned Access Now events ↔ Top10VPN cost ↔ World Bank macro (GDP, internet penetration, population) joined on `(iso3, year)`. | 2026-05-20 | n/a — derived in `notebooks/02_main.ipynb` §§5–11 | 1,511 rows × 66 cols, 542 KB. One row per cleaned shutdown event with attached country-year cost (NaN where Top10VPN does not cover the country/year — 86.4% of events get a cost row) and WB macro indicators. Adds derived columns `cost_pct_gdp`, `cost_per_internet_user`, `internet_users`. Built by re-running `notebooks/02_main.ipynb` top-to-bottom (reads from the two upstream snapshots above + WB live-cached pull). |

## Planned snapshots (later sessions)

- GADM 4.1 country boundaries (admin-0): heavy (~50 MB) `gadm_world_admin0.gpkg`, fetched on demand via `load_gadm_countries(fetch_if_missing=True)` from `https://geodata.ucdavis.edu/gadm/gadm4.1/gadm_410-levels.gpkg`. Cached to `data/raw/` (gitignored), not committed. Skipped by the smoke test when absent. Likely not needed at viz time — Plotly's built-in country layer is sufficient unless we need richer boundary detail.

## API caches (gitignored, not pinned)

- World Bank Indicators v2 JSON API: queried by `load_worldbank_indicators()` (default indicators `NY.GDP.MKTP.CD`, `IT.NET.USER.ZS`, `SP.POP.TOTL` over 2019–2025). Responses cached at `.cache/http_cache.sqlite` via `requests-cache` (30-day TTL). First call populates the cache (~1.2 MB); subsequent calls are local. Aggregate "country" rows with empty `countryiso3code` (regions, income groups) are dropped during load.
