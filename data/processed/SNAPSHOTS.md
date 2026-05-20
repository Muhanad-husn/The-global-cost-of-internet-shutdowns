# Data snapshots

This project pins dated snapshots of revisable sources so that re-running the
notebook six months later produces identical numbers. Whenever a new snapshot
is taken, append a row below and add a revision-magnitude diagnostic to
`notebooks/03_robustness.ipynb`.

## Active snapshots

| Snapshot file | Source | Access date | Source URL | Notes |
|---|---|---|---|---|
| `access_now_snapshot_2026-05-20.parquet` | Access Now #KeepItOn STOP dataset | 2026-05-20 | https://www.accessnow.org/keepiton-data-spreadsheet → Google Sheet ID `1DvPAuHNLp5BXGb0nnZDGNoiIwEeu2ogdXEIDvT4Hyfk` (XLSX export) | 2,102 rows × 47 cols; sourced from the **"Combined (2016-2025)"** sheet, which carries Access Now's curated cross-year view and a `count_year` attribution column. Per-year sheets duplicate "ongoing since" events from earlier years and were not used. Object columns cast to `string` for parquet stability; `start_date`/`end_date` coerced to `datetime` (2 unparseable `end_date` values coerced to NaT — true "ongoing" status lives in `shutdown_status`, not `end_date`). Project scope is 2019+ (1,704 rows). |

## Planned snapshots (later sessions)

- Top10VPN cost figures 2019–2025: hand-transcribed annual reports landed in `data/raw/top10vpn_<year>.csv` (committed); Session 2 will write `top10vpn_snapshot_2026-05-20.parquet`.
- GADM 4.1 country boundaries: heavy (~50 MB), fetched into `data/raw/` (gitignored) by a helper, not committed.
- World Bank indicators: pulled via the public Indicators v2 JSON API with `requests-cache` (30-day TTL); cache at `.cache/http_cache.sqlite` (gitignored).
