# Internet Shutdowns — Multi-Session Implementation Plan

> **Created:** 2026-05-20
> **Source plan:** `CLAUDE.md` + `README.md` (project root)
> **Total sessions:** 7
> **Estimated total effort:** 7 sessions (1 conversation each)

## Overview

Build a descriptive cartographic + time-series analysis of internet shutdowns 2019–latest using Access Now's #KeepItOn registry, Top10VPN's contested cost figures, World Bank macro indicators, and GADM boundaries. Headline deliverable is an interactive Plotly/Streamlit dashboard; portfolio signal is six load-bearing data-processing decisions documented in five-part form inline in the main notebook. The Top10VPN methodology-debate caveat is surfaced throughout — cost figures are reported, never endorsed.

## Session Dependency Graph

```
S1 (scaffold + Access Now snapshot)
  └─ S2 (Top10VPN ingest + WB API + GADM loaders)
       └─ S3 (clean.py + dedup + duration decisions)
            └─ S4 (cost join + WB normalize + grouping + platform-block decisions)
                 └─ S5 (viz module + hero figure)
                      ├─ S6 (Streamlit dashboard)
                      └─ S7 (README fill-in + smoke tests + reproducibility + robustness notebook)
```

S6 and S7 are independent and can be done in either order after S5.

---

## Session 1: Scaffold + Access Now snapshot fetch

**Objective:** Stand up the project skeleton from `_template/` and commit the first dated snapshot of the Access Now #KeepItOn registry.
**Inputs:** `D:\github-ds-portfolio\_template\` (canonical scaffold), `CLAUDE.md`, `README.md`.
**Outputs:** `pyproject.toml`, `src/internet_shutdowns/{__init__,data,clean,viz,diagnostics}.py`, `tests/test_smoke.py`, `notebooks/NOTEBOOK_STRUCTURE.md`, `notebooks/_scratch/`, `app/`, `data/{raw,processed}/`, `figures/`, `.gitignore`, `data/processed/access_now_snapshot_2026-05-20.parquet`.
**Depends on:** None.

### Context for resumption

Only `CLAUDE.md` and `README.md` exist at the project root. The sibling `_template/` directory is the canonical scaffold (pyproject with viz/geo/nlp/llm/ml extras already declared, `src/project_name/{data,diagnostics,viz}.py` stubs, `tests/test_smoke.py`, `notebooks/NOTEBOOK_STRUCTURE.md` documenting the five-part decision block). Conda env is `portfolio` (Python 3.14.4). Access Now publishes the #KeepItOn registry as a Google Sheet / form download; today's date 2026-05-20 is the snapshot pin.

### Steps

1. Copy `_template/` contents to the project root, renaming `src/project_name/` → `src/internet_shutdowns/`. Skip `_template/README.md` (project already has one).
2. Update `pyproject.toml`: project name `internet-shutdowns`, description from `CLAUDE.md`, add `streamlit>=1.32` to viz extras, confirm `requests-cache`, `pyarrow`, `pandas`, `plotly`, `kaleido`, `geopandas` are present (they are in template — verify).
3. Replace `src/internet_shutdowns/__init__.py` stub with a one-line package docstring referencing the project's purpose.
4. Create `notebooks/_scratch/` (gitkeep) and `app/` (placeholder `streamlit_dashboard.py` with a `# TODO: implemented in Session 6` comment).
5. Write `.gitignore` covering `data/raw/`, `data/cache/` (requests-cache sqlite), `__pycache__/`, `.ipynb_checkpoints/`, `notebooks/_scratch/*.ipynb`, `*.egg-info/`, `.venv/`. Keep `data/processed/` tracked.
6. `pip install -e ".[viz,geo]"` inside the `portfolio` conda env. Verify import: `python -c "import internet_shutdowns; import plotly; import geopandas"`.
7. **Access Now fetch.** Locate the current public download for the #KeepItOn registry (the site links to a Google Sheet / CSV). Download to `data/raw/access_now_keepiton_2026-05-20.csv` (raw, gitignored). Load with pandas, do a quick `df.info()` + `df.head()` sanity print, then write to `data/processed/access_now_snapshot_2026-05-20.parquet` (committed). Record the source URL and access date in a short `data/processed/SNAPSHOTS.md`.
8. Stub `src/internet_shutdowns/data.py` with one function signature: `load_access_now_snapshot(date: str = "2026-05-20") -> pd.DataFrame` that reads the committed parquet. Confirm it loads.
9. Update `tests/test_smoke.py` template stubs to one real test: `test_access_now_snapshot_loads` — asserts non-empty DataFrame and presence of expected core columns (country, start_date, end_date, type — exact names confirmed after step 7).
10. Run `pytest tests/ -q`. Commit everything as one scaffold commit.

### Completion criteria

- [ ] `pip install -e ".[viz,geo]"` succeeds in `portfolio` env
- [ ] `import internet_shutdowns` works
- [ ] `data/processed/access_now_snapshot_2026-05-20.parquet` exists and is committed
- [ ] `data/processed/SNAPSHOTS.md` records source URL + access date
- [ ] `pytest tests/ -q` passes (1 test green)
- [ ] One commit on `main` with the scaffold

### Handoff notes

- **Access Now snapshot source.** The KeepItOn STOP dataset is published as a Google Sheet via `https://www.accessnow.org/keepiton-data-spreadsheet` → `docs.google.com/spreadsheets/d/1DvPAuHNLp5BXGb0nnZDGNoiIwEeu2ogdXEIDvT4Hyfk`. XLSX export (`/export?format=xlsx`) works without auth.
- **Sheet to use is "Combined (2016-2025)"**, not the per-year sheets. The per-year sheets each include "ongoing since" events from earlier years (e.g. Iran 2009, Turkey 2013 appear in every annual sheet), so concatenating them creates massive duplication. The Combined sheet has 47 cols including a `count_year` attribution column the per-year sheets don't have.
- **Snapshot stats.** 2,102 rows × 47 cols, 0.6 MB parquet. Per `count_year`: 2016=80, 2017=113, 2018=205, 2019=224, 2020=171, 2021=197, 2022=206, 2023=289, 2024=304, 2025=313. Project scope (2019+) is 1,704 rows.
- **Schema notes for Session 3.** Core columns: `country`, `start_date`, `end_date`, `shutdown_type`, `shutdown_status`, `duration`, `geo_scope`, `area_name`, `affected_network`, `shutdown_extent`, `actual_cause`, `gov_justification`, `event`, `an_link`, `region`, `count_year`. Date columns coerced to datetime (2 unparseable `end_date` values → NaT; "ongoing" status lives in `shutdown_status` ∈ {"Ongoing", ...}, not in `end_date`). All other object columns cast to pandas `string` dtype for parquet stability — that includes `duration`, which contains the literal string `"Curfew Style"` alongside numeric-hours strings (so don't blindly cast to int/float in cleaning).
- **`shutdown_type` distribution (raw).** `Shutdown` 1913, `Shutdown, Throttle` 123, `Throttle` 63, `Unknown` 3. NB: there is no separate "platform_block" type — platform-specific blocks are encoded via the `*_affected` columns (`facebook_affected`, `twitter_affected`, ...). The CLAUDE.md/plan assumption of three categories (full / throttle / platform_block) needs rewording in S3's `standardize_event_columns`: type is currently {Shutdown, Shutdown+Throttle, Throttle, Unknown} and "platform block" is a *derived* flag from the per-platform columns. Log this as a decision input for S3.
- **`.gitignore` gotcha resolved.** Directory-level `data/raw/` ignore prevented `!data/raw/top10vpn_*.csv` re-include; switched to `data/raw/*` + negation. Same fix applied to `notebooks/_scratch/*` so the .py exploration scripts are properly excluded while `.gitkeep` is tracked.
- **`.cache/` vs `data/cache/`.** Template's `data.py` puts the HTTP cache at `.cache/` (project root); CLAUDE.md mentioned `data/cache/`. Both are gitignored. S2 should use the template's location (`.cache/http_cache.sqlite`) to avoid divergence.
- **Streamlit dep.** Added to `viz` extras (S6 needs it). Template kept `streamlit` in a separate `dashboard` extra; flattened into `viz` so a single `pip install -e ".[viz,geo]"` covers everything in this project.
- **`pycountry` dep added** to project deps (S2 will need it for ISO-3 reconciliation across sources).
- **Scratch scripts.** `notebooks/_scratch/{fetch_access_now,inspect_access_now,snapshot_access_now}.py` are gitignored but useful if the snapshot ever needs to be regenerated. Don't delete them locally.

---

## Session 2: Data loaders + remaining snapshots

**Objective:** Implement the remaining four loaders (Top10VPN manual-CSV ingest, World Bank API with `requests-cache`, GADM country polygons) and produce the dated Top10VPN snapshot.
**Inputs:** Session 1 scaffold + Access Now snapshot. User-supplied `data/raw/top10vpn_<year>.csv` files transcribed manually from the annual reports (one CSV per year 2019–2025).
**Outputs:** Fleshed-out `src/internet_shutdowns/data.py` (4 loaders + a unified `load_all()`), `data/processed/top10vpn_snapshot_2026-05-20.parquet`, `data/raw/gadm_world_admin0.gpkg`, `data/cache/` sqlite cache, two more smoke tests.
**Depends on:** Session 1.

### Context for resumption

Scaffold is in place; Access Now snapshot loads via `load_access_now_snapshot()`. Now wire the other three sources. Top10VPN has no API and no clean machine-readable feed — the user will hand-transcribe each year's country-level table from the annual HTML report into `data/raw/top10vpn_<year>.csv` (columns: `country`, `cost_usd`, `duration_hours`, `users_affected`, `year`). World Bank uses the public indicators API; cache aggressively because indicators are stable. GADM 4.1 country boundaries are a one-time ~50MB download.

### Steps

1. **Top10VPN ingest.** Implement `load_top10vpn_csvs(raw_dir="data/raw") -> pd.DataFrame` that globs `top10vpn_*.csv`, concatenates, standardizes country names (use `pycountry` if needed — add to deps), and returns long-form `country × year × {cost_usd, duration_hours, users_affected}`. **Before coding: confirm with user that the CSV files exist; if not, write the loader and a one-page `data/raw/TOP10VPN_INGEST_GUIDE.md` documenting the expected schema, then stop and ask user to populate.**
2. Snapshot Top10VPN: `df_top10vpn.to_parquet("data/processed/top10vpn_snapshot_2026-05-20.parquet")`. Append entry to `SNAPSHOTS.md`.
3. **World Bank loader.** Implement `load_worldbank_indicators(indicators=["NY.GDP.MKTP.CD", "IT.NET.USER.ZS", "SP.POP.TOTL"], years=range(2019, 2026)) -> pd.DataFrame` using `requests` + `requests-cache` (sqlite at `data/cache/wb_cache.sqlite`, TTL 30 days). Returns long-form `country × year × indicator × value`. Use the v2 JSON endpoint, paginate, handle nulls.
4. **GADM loader.** Implement `load_gadm_countries(level=0) -> geopandas.GeoDataFrame`. One-time fetch of `gadm_410-levels.gpkg` is heavy — instead use the per-level world file (`gadm_world_admin0.gpkg`, ~50MB). Cache to `data/raw/` (gitignored — too large to commit). Document size in `SNAPSHOTS.md` and add a fetch helper rather than committing the file.
5. Add `load_all()` convenience that returns a dict `{"shutdowns", "costs", "wb", "boundaries"}`.
6. Smoke tests: `test_top10vpn_snapshot_loads`, `test_worldbank_cached_call_returns_data` (mock-friendly — assert non-empty for one country/year), `test_gadm_loads` (skip if file absent with a clear message).
7. Run `pytest -q`. Commit.

### Completion criteria

- [ ] All four loaders importable and callable
- [ ] `data/processed/top10vpn_snapshot_2026-05-20.parquet` committed (if CSVs supplied) OR clear `TOP10VPN_INGEST_GUIDE.md` waiting for user
- [ ] `data/cache/wb_cache.sqlite` populated on first run
- [ ] `SNAPSHOTS.md` has entries for all three snapshots
- [ ] All smoke tests pass
- [ ] One commit

### Handoff notes

- **Top10VPN snapshot.** 169 rows × 7 cols at `data/processed/top10vpn_snapshot_2026-05-20.parquet`. Per-year counts: 2019=22, 2020=21, 2021=22, 2022=23, 2023=25, 2024=28, 2025=28. Schema: `country, iso3, year, cost_usd, duration_hours, users_affected, source`. Top-10 by total cost 2019–2025: Russia $37.5B, Myanmar $8.6B, India $6.0B, Venezuela $4.2B, Iraq $3.5B, Sudan $3.3B, Pakistan $3.0B, Iran $2.6B, Ethiopia $2.3B, Nigeria $1.6B (Top10VPN methodology — debated; surface caveat in every figure).
- **Country-name reconciliation surprises.** `pycountry`'s bundled data uses **"Türkiye"** (no English "Turkey" alias) and **"Russian Federation"** (no "Russia" alias), so neither resolves via `.lookup()`. Both are pinned in `_TOP10VPN_ISO3_OVERRIDES` (TUR, RUS). Other overrides: `Congo DRC`/`DRC→COD`, `Republic of Congo→COG`, `eSwatini→SWZ`, `Pakistan - Azad Kashmir→PAK` (sub-national entry collapses to parent country for joining). **Somaliland** is intentionally left with `iso3=None` — it is a de-facto state with no ISO-3166 code, and the World Bank / GADM do not recognize it; mapping it to SOM would corrupt joins. Downstream (S4 cost join) needs to decide whether to display Somaliland's single 2022 row separately or drop it from country-level aggregates.
- **Same overrides will be reusable in S3** when standardizing Access Now's `country` column to ISO-3 — `_country_to_iso3` in `data.py` is currently named with a leading underscore. Consider promoting it to public API in S3 or moving it to `clean.py`.
- **World Bank indicators.** Defaults are `NY.GDP.MKTP.CD` (GDP current USD), `IT.NET.USER.ZS` (% internet users), `SP.POP.TOTL` (population). 5,586 rows = 261 countries × 7 years × 3 indicators in long form. 2025 rows are mostly NaN — WB hasn't reported current-year figures yet, which is expected and won't bite until S4's normalization step (use `min_periods` / forward-fill or just exclude 2025 from `cost_pct_gdp`). The v2 API returns aggregate rows (regions, income groups) with empty `countryiso3code`; these are dropped during load.
- **WB cache.** `.cache/http_cache.sqlite` (~1.2 MB) populated on first call. Cache TTL is 30 days; force-refresh by deleting the sqlite file. WB Indicators codes are stable — no surprises against the plan's defaults.
- **GADM.** Loader implemented but file **not fetched** (50 MB, gitignored). Smoke test `test_gadm_loads` skips when absent. Per the S5 plan, default-Plotly country layer is the path of least resistance and we may never need GADM; only fetch (`load_gadm_countries(fetch_if_missing=True)`) if S5/S6 require precise boundary geometry.
- **`load_all()`** is the one-call convenience for notebooks — returns `{shutdowns, costs, wb}` (and `boundaries` only if GADM is on disk). S3's main notebook §1 should use this.
- **No `data/cache/` directory.** Decision Log row 5 confirmed; cache is at `.cache/`. WB loader uses the shared `session` from `data.py` (no per-loader caches).

---

## Session 3: Cleaning module + dedup decision + duration imputation decision

**Objective:** Build `src/internet_shutdowns/clean.py` and execute the first two five-part decision blocks (deduplication, duration imputation) inline in `notebooks/02_main.ipynb`.
**Inputs:** Snapshots from S1+S2, `diagnostics.py` helpers, `NOTEBOOK_STRUCTURE.md` template.
**Outputs:** `src/internet_shutdowns/clean.py` (3 functions: `dedupe_events`, `compute_duration`, `standardize_event_columns`), `notebooks/02_main.ipynb` with sections §1 (load), §2 (standardize), §3 (dedup decision block), §4 (duration imputation decision block), populated rows in README decisions table for these two decisions.
**Depends on:** S2.

### Context for resumption

Loaders work. Now do the lab work. CLAUDE.md explains both decisions in detail: dedup rule starts with `country + start_date within ±N days + type match`, tune N against a ~30-case probe set, document false-merge and unmerged-duplicate rates. Duration imputation has four options to evaluate (drop / snapshot-date / 30-day ceiling / carry-as-missing-with-flag). Each decision **must** be presented in five parts: problem → diagnostic code → 2–3 named options → decision + rationale → sensitivity check. Diagnostics helpers (`missingness_summary`, `missingness_pattern`, `distribution_compare`, `before_after`, `compare_alternatives`) live in `src/internet_shutdowns/diagnostics.py`.

### Steps

1. Create `notebooks/02_main.ipynb` from `NOTEBOOK_STRUCTURE.md` template. Add the project's title, the methodology caveat banner cell, and table-of-contents cell.
2. §1 Load: call `load_access_now_snapshot()` + `load_top10vpn_csvs()` + `load_worldbank_indicators()`.
3. §2 Standardize: implement `standardize_event_columns(df)` — canonical column names, ISO-3 country codes, parsed dates, type as ordered categorical (`full_blackout` / `throttle` / `platform_block`).
4. §3 **Decision block: deduplication.** Run `missingness_summary` + value-counts on `(country, start_date, type)` triples to find clusters. Code dedup at N ∈ {0, 1, 3, 7} days and report merge counts via `compare_alternatives`. Hand-spot-check ~30 borderline cases. Decide N. Implement final `dedupe_events(df, days_tolerance=N)`. Sensitivity: re-run with N±2 and report headline metric drift.
5. §4 **Decision block: duration imputation.** Diagnose: what fraction of rows are missing `end_date`? Of those, what fraction are "ongoing" vs. simply unrecorded? `distribution_compare` of known-duration events. Implement `compute_duration(df, missing_strategy="...")`. Sensitivity: re-run cost rollup (placeholder — actual rollup in S4) under each strategy, report top-10-country ranking stability.
6. Populate README decisions table rows for these two decisions (fill in `Chose` + `Why` + `Sensitivity` columns).
7. Add smoke tests: `test_dedupe_collapses_known_duplicates`, `test_compute_duration_handles_missing_end_date`.
8. Run notebook top-to-bottom, run pytest, commit.

### Completion criteria

- [ ] `notebooks/02_main.ipynb` §§1–4 runs top-to-bottom without error
- [ ] Both decision blocks contain real diagnostic output (not placeholder text)
- [ ] README decisions table rows 1 and 2 populated
- [ ] `clean.py` exports tested and importable
- [ ] One commit

### Handoff notes

- **`clean.py` shipped** with three public functions plus `resolve_iso3` helper. `standardize_event_columns` is *additive* — it leaves all 47 raw columns intact and adds {`iso3`, `type`, `duration_hours`, `platform_block`, `platforms_affected`}. S4 can rely on either the raw or the canonical names.
- **Country resolution.** `resolve_iso3` is `_country_to_iso3` + parenthetical-strip fallback. Covers all 92 in-scope countries except **Somaliland** (intentionally None — same policy as Top10VPN in `data.py`). The three multi-country rows (`"Cameroon; Central African Republic"`, etc.) are split row-wise inside `standardize_event_columns`; raw `len(df)=2102` → standardized `len=2108`.
- **Type mapping.** `{Shutdown, "Shutdown, Throttle"} → full_blackout`, `Throttle → throttle`, `Unknown → other`. Combined "Shutdown+Throttle" is folded into `full_blackout` because the blackout is the load-bearing event; throttle co-occurrence shows up via the raw `shutdown_type` if needed. Decision Log #2 satisfied: `platform_block` is a derived bool (from `shutdown_extent contains "Service-based"` OR any `*_affected=="Yes"`), not a `type` value.
- **Duration column gotcha (new).** Raw `duration` contains some Excel-date-shaped garbage (e.g. `"-44270"` — that's a negative Excel serial for ~2021). `_coerce_duration_hours` nulls anything `< 0` or `> 175200` (20 years). Without this guard, `compute_duration` returned -1854-day values. ~37 raw values in the in-scope subset get nulled. Document under `duration_source="duration_field"` if anything sneaks through.
- **Dedup chosen N=0.** ~200 rows collapse in 2019+. Cluster key is `(iso3, type, normalized area_name)`, so Ethiopia/Tigray vs. Ethiopia/Wellega on the same day remain distinct. `dedupe_events` keeps the most-populated row per cluster (max non-null count).
- **Recorded end_date < start_date.** 3 rows in the post-dedup in-scope subset have `end_date < start_date` (data-entry error). `compute_duration` treats these as "no usable end_date" and falls through to the hybrid logic. Surfaced via `duration_source` flag, not silently clipped to zero.
- **Hybrid duration coverage.** Post-dedup in-scope = 1,511 rows. Hybrid populates 1,224 (recorded=1,142, snapshot_date=81, duration_field=1, missing=287). The 287 "missing" rows carry `duration_imputed=True` with NaN — S4's cost rollup will need a default treatment.
- **Pre-cost-join top-10 by total shutdown-days (hybrid).** Ethiopia, India, Iran, Myanmar, Pakistan, Russian Federation, Türkiye, Ukraine, Yemen, Tigray-included long-runners. The Iran 2009 / Turkey 2013 ongoing-since events drive the long tail (~17 years each). Verify against Top10VPN's ordering in S4.
- **Notebook builder pattern.** `notebooks/_scratch/build_02_main.py` constructs the .ipynb via `nbformat`; execute with `jupyter nbconvert --execute --inplace`. Reuse this pattern in S4 — add S4 cells to the same builder (or a new `build_02_main_s4.py` that loads the existing notebook and appends).
- **README decisions table rows 1 & 2 populated.** Rows 3–6 still placeholders for S4 / S5.
- **Tests added (3): 9 pass, 1 skip (GADM).** Suite runtime ~18 s.

---

## Session 4: Cost join + WB normalization + country grouping + platform-block decisions

**Objective:** Build the analytic dataset by joining costs and macro indicators, and execute decision blocks 3–5 (cost source choice, country grouping, platform-block treatment). Decision 6 (snapshot pinning) is documented based on the work already done in S1–S2.
**Inputs:** Cleaned event dataset from S3, Top10VPN + WB snapshots from S2.
**Outputs:** `notebooks/02_main.ipynb` §§5–9 (cost join, WB norm, decision blocks for cost source / country grouping / platform-block treatment / snapshot pinning), `data/processed/analytic_dataset_2026-05-20.parquet`, 4 more populated rows in README decisions table.
**Depends on:** S3.

### Context for resumption

Cleaned event dataset exists at the end of S3 (`notebooks/02_main.ipynb` §§1–4 produces it). Now layer cost + macro and execute the four remaining decisions. **Top10VPN methodology caveat is load-bearing**: the cost-source decision block (decision #3) is where the methodology debate lives — cite Top10VPN's methodology page AND at least one critical secondary source, present the debate honestly, choose Top10VPN as primary for cross-country comparability while documenting the limitation. Country grouping (#4) has three named options (WB income group / UN LDC / custom regional) — each gives a different LMIC ranking. Platform-block treatment (#5) per CLAUDE.md: present both views (combined as headline + separated in drill-down).

### Steps

1. §5 Cost join: outer join cleaned events ↔ Top10VPN cost on `(iso3, year)`. Diagnose join completeness.
2. §6 WB normalization: join WB indicators on `(iso3, year)`. Compute `cost_pct_gdp = cost_usd / gdp_usd` and `cost_per_internet_user`.
3. §7 **Decision block: cost source choice.** Surface the methodology debate explicitly. Diagnostic: compare Top10VPN figures vs. any academic alternates available for 2–3 well-studied cases (Iran 2019, Sudan 2019, India Kashmir 2019–2020). Decide: Top10VPN as primary, alternates cited where they exist, methodology caveat printed in every figure title.
4. §8 **Decision block: country grouping.** Compute top-10 cost ranking under WB income group / UN LDC / custom-regional framings. Diagnostic: rank-correlation across the three. Decide one as headline, note others in robustness notebook.
5. §9 **Decision block: platform-block treatment.** Diagnostic: what share of shutdown-days are full vs. throttle vs. platform-block? Per-country totals under combined vs. separated counting. Decision: combined as headline view, separated in country drill-down. Implement a `view: Literal["combined","separated"]` parameter on the rollup helper.
6. §10 **Decision block: snapshot pinning.** Mostly retrospective — the snapshots already exist from S1+S2; document the *why* and add a revision-magnitude diagnostic placeholder (will be runnable next time a fresh snapshot is taken).
7. Persist final analytic dataset: `df_analytic.to_parquet("data/processed/analytic_dataset_2026-05-20.parquet")`.
8. Populate README decisions table rows 3–6.
9. Run notebook top-to-bottom, commit.

### Completion criteria

- [ ] `notebooks/02_main.ipynb` §§1–10 runs top-to-bottom
- [ ] `data/processed/analytic_dataset_2026-05-20.parquet` exists, committed
- [ ] All 6 README decisions table rows populated
- [ ] Cost-source block contains real citation to ≥1 secondary critical source
- [ ] One commit

### Handoff notes

- **Analytic dataset shipped.** `data/processed/analytic_dataset_2026-05-20.parquet` — 1,511 rows × 66 cols, 542 KB. Built in §§5–11. S5 reads from here, *not* from the upstream snapshots.
- **Cost-join completeness.** 1,305 / 1,511 events (86.4%) joined to a Top10VPN cost row. At the `(iso3, year)` level: 152 keys in both, 96 event-only (countries below Top10VPN's reporting threshold), 17 cost-only. Cost-only iso3s: COD, COL, HTI, SOM — Top10VPN reports shutdowns the registry missed *or* aggregated cost from events not surfaced at country-year granularity. S5 can decide whether to surface these on the world map as "cost but no detail" or drop.
- **Somaliland.** Top10VPN's 2022 row carries `iso3=None` (Decision Log #7); it drops out of the country-keyed join. S5/S6 must decide whether to display it as a separate map annotation or drop entirely. Recommend the latter for the headline; mention in Limitations.
- **WB join.** `wb` was pivoted long→wide on `(iso3, year)` inline in the notebook. Columns renamed to `gdp_usd`, `internet_pct`, `population`; derived `cost_pct_gdp`, `internet_users`, `cost_per_internet_user`. 2025 has 0 WB GDP rows (current-year figures unreported) — 260 events in 2025 lose normalization. S5's hero figure should restrict the cost rollup to 2019–2024 to avoid 2025's truncation, or compute on cost_usd directly (which IS available for 2025).
- **WB income groups via `/v2/country` endpoint** — 86 HIC + 54 UMC + 50 LMC + 25 LIC. Pulled inline in §8 with the shared cached session. If S7/robustness needs this regularly, promote to `load_worldbank_country_meta()` in `data.py`. UN LDC list (45 ISO-3s) and `CUSTOM_REGION` dict (~80 countries) live in the §8 code cell — same promotion candidate.
- **Headline top-10 by total estimated cost** (used in S5 hero figure): **Russia ($37.5B), Myanmar ($8.6B), India ($6.0B), Venezuela ($4.2B), Iraq ($3.5B), Sudan ($3.3B), Pakistan ($3.0B), Iran ($2.5B), Ethiopia ($1.9B), Nigeria ($1.6B)**. Methodology caveat must be in the title — *"Top10VPN methodology — see limitations"* or similar.
- **Platform-block surprise.** The combined headline view (131,500 shutdown-days) is dominated by `platform_block` (109,808) and `throttle` (3,337); full blackouts contribute only 18,355. Per-country: Iran 96.7% non-blackout, Russia 99.5%, Türkiye 100%. The "Combined" view matches Top10VPN's aggregation but the *substance* of those shutdown-days is mostly platform blocks — important for the README *Findings* prose in S7. Top-10 by `combined` is different from top-10 by `blackout_only` (Bangladesh / Indonesia / China move up sharply on a blackout-only view).
- **§9 rollup helper** lives inline in the notebook as `shutdown_day_rollup(frame, view)`. S5 viz helpers should call it from the analytic dataset rather than re-implementing the bucket logic. If S5 prefers it in `src/`, lift verbatim into `clean.py` or a new `rollups.py`.
- **Decisions table rows 3–6 populated in README** with real numbers and rank-overlap diagnostics. S7's *Findings* and *Limitations* sections still need prose — anchor them in the §§5–10 diagnostics.
- **No new deps.** §8 uses only pandas + a single live `requests` call through the shared cached session for WB country metadata. UN LDC list and the custom-regional dict are inlined. If S7 wants to lift any of this into `src/`, no new deps are required.

---

## Session 5: Viz module + hero figure

**Objective:** Build `src/internet_shutdowns/viz.py` with reusable Plotly helpers and export the static `figures/hero.png` (top-10 countries by total estimated shutdown cost, with methodology caveat in the title).
**Inputs:** `data/processed/analytic_dataset_2026-05-20.parquet` from S4.
**Outputs:** `src/internet_shutdowns/viz.py` (3 functions: `world_choropleth`, `time_series`, `top10_bar`), `figures/hero.png`, `notebooks/02_main.ipynb` §11 (viz showcase), 1 smoke test.
**Depends on:** S4.

### Context for resumption

Analytic dataset is finalized at `data/processed/analytic_dataset_2026-05-20.parquet`. Viz library is Plotly (justified in CLAUDE.md: dashboard depends on hover + click-through). Hero constraint: top-10 chart must read at ~800×800 LinkedIn thumbnail size and the methodology caveat in the title must remain legible at that size. Same viz helpers will power S6 dashboard — don't build two parallel viz pipelines.

### Steps

1. `world_choropleth(df, metric="total_shutdown_days" | "total_cost_usd", year_range=None) -> plotly.Figure`. Use GADM polygons if a real geo overlay is needed; default to Plotly's built-in country layer (cheaper, no GADM dep at viz time).
2. `time_series(df, freq="M", metric="event_count" | "cumulative_cost") -> plotly.Figure`.
3. `top10_bar(df, metric="total_cost_usd", caveat_in_title=True) -> plotly.Figure`. Title: `"Top 10 countries by estimated shutdown cost, 2019–2025 (Top10VPN methodology — see limitations)"`. Confirm legibility at 800×800.
4. §11 in notebook: render all three figures inline.
5. Static export: `plotly.io.write_image(fig, "figures/hero.png", width=800, height=800, scale=2)`. Requires `kaleido` (already in viz extras).
6. Smoke test: `test_top10_bar_renders_with_caveat` — asserts caveat substring is in figure title.
7. Commit `hero.png` + viz module.

### Completion criteria

- [ ] `figures/hero.png` exists, committed, legible at 800×800
- [ ] Methodology caveat visible in hero title
- [ ] Three viz helpers callable from notebook and (later) Streamlit
- [ ] Smoke test passes
- [ ] One commit

### Handoff notes

- **`figures/hero.png` shipped.** 800×800 @ scale=2 (so file is 1600×1600), 136 KB. Top-10 cost ranking matches S4 handoff exactly: Russia $37.5B, Myanmar $8.6B, India $6.0B, Venezuela $4.2B, Iraq $3.5B, Sudan $3.3B, Pakistan $3.0B, Iran $2.5B, Ethiopia $1.9B, Nigeria $1.6B. Caveat *"Top10VPN methodology — see limitations"* renders as a `<sup>` subtitle and stays legible at thumbnail size.
- **Rollups lifted to `src/internet_shutdowns/rollups.py`.** Three functions: `shutdown_day_rollup(frame, view)` (verbatim from the notebook), `country_cost_rollup(frame, year_range=None)`, `monthly_event_series(frame)`. S6 (dashboard) imports the same three — there is exactly one code path for the headline figures. The §9 inline `shutdown_day_rollup` in the notebook is now dead code but left in place to keep the §9 decision-block flow self-contained for readers.
- **Cost rollup gotcha.** The analytic dataset attaches each `(iso3, year)` Top10VPN cost to *every* event in that country-year — summing `cost_usd` event-wise inflates by the event-multiplicity factor. `country_cost_rollup` first dedupes on `(iso3, year)` then sums. S6 must use this helper (or the same dedup logic) for any country-level cost aggregation.
- **`display_country` shortener.** Formal UN names ("Russian Federation", "Iran (Islamic Republic of)", "Venezuela (Bolivarian Republic of)") run off the page at 800×800. `viz.display_country` swaps them for conventional short forms ("Russia", "Iran", "Venezuela"). Only used for axis labels — the underlying `country` column and ISO-3 join keys are unchanged. Reuse from S6.
- **`METHODOLOGY_CAVEAT` constant.** Exported from `viz`. Use this exact string in the S6 dashboard banner — keeps the caveat consistent across the static hero and the interactive UI.
- **Kaleido on Windows worked first try.** `plotly.io.write_image` with `width=800, height=800, scale=2` exports without flicker. No `--browser` shim needed. Version locked via `viz` extra.
- **Axis tick prefix/suffix didn't stick** when `tickvals/ticktext` were provided alongside `tickprefix="$"`. The bar value labels ("$37.5B" etc.) carry the unit, and the axis title reads "Estimated cost (USD)" — clear enough; left as is. Worth re-attempting if S6/S7 polish requires "$5B / $10B / ..." on the axis.
- **§12 viz showcase.** `notebooks/02_main.ipynb` now ends with §12 — loads the analytic parquet (decoupled from §§1–11), renders the three figures inline, saves `hero.png`. Re-running §12 alone is enough to refresh the PNG.
- **Smoke tests now 10 pass / 1 skip** (GADM still skipped). New test: `test_top10_bar_renders_with_caveat` asserts the caveat substring is in the title and that the chart has exactly 10 bars.
- **For S6**: import path is `from internet_shutdowns.viz import world_choropleth, time_series, top10_bar, METHODOLOGY_CAVEAT, display_country, save_figure`. Read the analytic dataset directly — do not re-run `clean.py`.

---

## Session 6: Streamlit dashboard

**Objective:** Build the headline interactive deliverable: world map + country drill-down + time series in a single Streamlit app.
**Inputs:** `data/processed/analytic_dataset_2026-05-20.parquet`, viz helpers from S5.
**Outputs:** Fully implemented `app/streamlit_dashboard.py`, screenshot at `figures/dashboard_screenshot.png`.
**Depends on:** S5.

### Context for resumption

Viz helpers exist. Dashboard reuses them — do not duplicate. Layout per CLAUDE.md: sidebar with year-range + country + view-mode (combined/separated) filters; main pane has tabs `World Map` / `Country Drill-down` / `Time Series` / `Top 10`. Country drill-down should show the per-event timeline for the selected country with event-level details on hover. Methodology caveat must appear as a persistent banner at the top, not buried in a footer.

### Steps

1. Sidebar controls: year-range slider (2019–latest), country multi-select, view-mode toggle (combined/separated per S4 decision).
2. Persistent banner cell with the Top10VPN methodology caveat.
3. Tab 1: `world_choropleth` driven by sidebar.
4. Tab 2: country drill-down — event timeline (Plotly Gantt-style) + table of events with details.
5. Tab 3: `time_series` (monthly count + cumulative cost — toggleable).
6. Tab 4: `top10_bar` (the same hero figure, interactive).
7. Run with `streamlit run app/streamlit_dashboard.py` in `portfolio` env. Take a screenshot of the World Map tab with a representative filter applied, save to `figures/dashboard_screenshot.png`.
8. Reference the screenshot from README's "How to reproduce" section.
9. Commit.

### Completion criteria

- [ ] Dashboard launches via `streamlit run` without error
- [ ] All four tabs render with real data
- [ ] Methodology caveat banner visible without scrolling
- [ ] `figures/dashboard_screenshot.png` committed
- [ ] One commit

### Handoff notes

_[Fill during execution: streamlit version installed, any deprecation warnings, perf observations.]_

---

## Session 7: README fill-in + smoke tests + robustness notebook + reproducibility check

**Objective:** Finalize the deliverable — populate README with findings + limitations, complete the smoke test suite, write `notebooks/03_robustness.ipynb`, and run a clean reproducibility check.
**Inputs:** Everything from S1–S6.
**Outputs:** Filled-in `README.md` (Findings, Limitations, decisions table rationale prose, run-time number), `tests/test_smoke.py` (full coverage of loaders + clean + viz), `notebooks/03_robustness.ipynb`, `REPRODUCIBILITY.md` log of the clean re-run.
**Depends on:** S5 (S6 can be parallel).

### Context for resumption

All upstream work done. This session is the "ship it" pass. Findings come from the analytic dataset and must be **falsifiable statements anchored to specific numbers** (e.g., "Country X: Y total shutdown-days 2019–2025, estimated cost Z USD per Top10VPN methodology"). Limitations section must explicitly name the Top10VPN methodology debate as a **limitation, not a finding**. Robustness notebook covers: dedup-N sensitivity, alternate duration imputation, alternate country grouping (each of these decisions was made in S3–S4 with sensitivity placeholders — now elaborate).

### Steps

1. Populate README Findings: ≥3 numeric statements anchored to analytic dataset values, each cost statement tagged with the methodology caveat.
2. Populate README Limitations: Top10VPN methodology debate (most prominent), Access Now reporting bias, definitional drift across sources, WB data quality, "trend in counts is partly trend in reporting".
3. Fill the rationale prose in each row of the README decisions table (cross-link to the notebook section).
4. Complete `tests/test_smoke.py`: loader tests, clean tests, viz title test, end-to-end test that loads analytic dataset and asserts non-empty + expected columns.
5. Build `notebooks/03_robustness.ipynb`: re-run dedup at N±2/±5, re-run duration imputation under all four strategies, re-run top-10 ranking under WB income group / UN LDC / custom-regional. For each, report the rank-correlation or magnitude drift.
6. **Reproducibility check.** Fresh terminal: `pip install -e ".[viz,geo]"`, run `pytest -q`, run notebook 02 top-to-bottom (record wall-clock), launch dashboard. Log result in `REPRODUCIBILITY.md` with the wall-clock number. Update README's "Full run time: ~X minutes" placeholder.
7. Final commit. Optionally tag `v0.1.0`.

### Completion criteria

- [ ] README Findings + Limitations sections populated with real numbers + prose
- [ ] All 6 decisions table rows have real `Chose` + `Why` + `Sensitivity` content
- [ ] `pytest -q` green (≥8 tests)
- [ ] `notebooks/03_robustness.ipynb` runs top-to-bottom
- [ ] `REPRODUCIBILITY.md` records the clean re-run wall-clock
- [ ] Final commit on `main`

### Handoff notes

_[Fill during execution: final run-time, any reproducibility surprises, things deferred to a v0.2.]_

---

## Decision & Change Log

Track decisions made during execution that affect later sessions.

| # | Session | Decision | Affects |
|---|---------|----------|---------|
| 1 | S1 | Use **Access Now's curated "Combined (2016-2025)" sheet** as the snapshot source, not per-year sheets. Per-year sheets duplicate "ongoing since" events from earlier years (~6 dupes per sheet across 2016–2025 = ~60 false dupes). Combined sheet adds a `count_year` attribution column. | S3 dedup work starts from a cleaner base; reduces the "false-merge rate" baseline. |
| 2 | S1 | `shutdown_type` in raw data is `{Shutdown, Shutdown+Throttle, Throttle, Unknown}` — there is **no native "platform_block" type**. Platform-specific blocks must be **derived** in S3's `standardize_event_columns` from the `*_affected` columns (facebook_affected, twitter_affected, ...). | S3 type taxonomy; S4 platform-block decision block. |
| 3 | S1 | Snapshot persistence policy: cast all object columns to pandas `string` dtype before `to_parquet`. Reason: `duration` column contains mixed types (numeric hours alongside literal `"Curfew Style"` strings). | S3 must parse `duration` carefully — it's not numeric. |
| 4 | S1 | `streamlit` consolidated into the `viz` extra (template had a separate `dashboard` extra). One install covers all viz + dashboard work. | Reproducibility check in S7 uses a single `pip install -e ".[viz,geo]"`. |
| 5 | S1 | HTTP cache lives at `.cache/http_cache.sqlite` (template default), not `data/cache/` (mentioned in CLAUDE.md). | S2 World Bank loader points here. |
| 6 | S2 | `pycountry` does **not** resolve common English names "Russia" or "Turkey" — bundled data uses "Russian Federation" and "Türkiye" with no short-name aliases. Both pinned in `_TOP10VPN_ISO3_OVERRIDES` (RUS, TUR). | S3 standardization needs the same override map for Access Now's `country` column; consider promoting `_country_to_iso3` to public API. |
| 7 | S2 | **Somaliland** kept with `iso3=None` rather than collapsing to SOM. It is a de-facto state with no ISO-3166 code; WB and GADM do not recognize it, so a SOM map would corrupt joins. Single Top10VPN row affected (2022). | S4 cost join must decide: show Somaliland separately on the dashboard, or drop from country-level aggregates. |
| 8 | S3 | Dedup cluster key is `(iso3, type, normalized area_name)`, `days_tolerance=0`. Same-day exact-key collapse only. Higher N risks merging co-located escalations and regional reignitions. | S4/S5 inherit this. Sensitivity to N is in `03_robustness.ipynb` (S7). |
| 9 | S3 | Raw `duration` column has Excel-date-shaped garbage (e.g. `"-44270"`). `_coerce_duration_hours` nulls values `< 0` or `> 175200` (20 years). ~37 in-scope values affected. | If future snapshots have a different garbage pattern, revisit this cap. |
| 10 | S3 | Duration imputation = **hybrid** strategy: recorded → `duration_hours` → snapshot-date-if-Ongoing → NaN+flag for Unknown. Pure strategies span 13k–489k total shutdown-days; hybrid sits at ~130k. | S4 cost rollup multiplies through these durations; `duration_imputed=True` rows need a documented treatment in the cost join. |
| 11 | S3 | `type` value mapping: `Shutdown` and `Shutdown, Throttle` both → `full_blackout`. `Throttle` alone → `throttle`. `Unknown` → `other`. | S4 platform-block decision block can still split out "combined throttle+blackout" via the raw `shutdown_type` column, which is preserved. |
| 12 | S4 | **Cost-source primary = Top10VPN**, methodology caveat surfaced in every figure title; West (Brookings, 2016) cited as the methodology ancestor. Rejected: averaging top-down sources (false precision — they all share West's lineage), bottom-up-where-available (incoherent dataset), drop-cost (loses framing). | S5 hero-figure title must carry the caveat. S7 *Findings* prose tags every cost statement with "per Top10VPN methodology, debated." |
| 13 | S4 | **Country grouping primary = WB income group**, with UN LDC and a custom regional (MENA / SSA / S/SE Asia / Eurasia / Americas / Asia-Pac) exposed as dashboard toggles. Anchored in headline-set overlap: Overall ∩ WB-LMC = 5/10, Overall ∩ UN-LDC = 3/10, WB-LMC ∩ UN-LDC = 5/10. | S6 dashboard sidebar gets the grouping toggle. S7 robustness covers all three. |
| 14 | S4 | **Platform-block treatment = combined headline, separated drill-down.** Combined matches Top10VPN's country/year aggregation; separated reveals that 70–100% of shutdown-days in top countries are non-blackout (Iran 96.7%, Russia 99.5%). Weighted alternatives rejected (made-up weights). | S5 hero-figure uses combined. S6 drill-down splits the per-country timeline by bucket. S7 *Findings* must note the non-blackout dominance explicitly. |
| 15 | S4 | **Both sources pinned with dated parquets** (Access Now + Top10VPN). Re-snapshot is an explicit dated step, prior snapshots remain in place. First snapshot → cross-snapshot revision diagnostic is structurally untestable until a second snapshot exists; placeholder schema lives in §10. | Future snapshots append a new dated parquet, populate the revision table, do not overwrite. |
| 16 | S4 | **Top10VPN does not cover all 2019+ event countries.** 86.4% of cleaned events join to a cost row; 26 event-only iso3s (AGO, ARE, BHR, CAF, CHN, ECU, GBR, ISR, KHM, LAO, LBN, LTU, LVA, MLI, MWI, MYS, NER, OMN, PSE, QAT, RWA, SAU, SLV, TUN, UKR, USA) — these appear on the world map for *event counts* / *shutdown-days* but carry NaN cost. The 4 cost-only iso3s (COD, COL, HTI, SOM) appear in cost rollups but not in event-level drill-downs. | S5 needs to handle NaN cost on the choropleth gracefully (separate "no Top10VPN coverage" color or omit). S6 drill-down for cost-only countries should show "cost reported by Top10VPN; no event-level detail in Access Now snapshot." |
| 17 | S4 | **Analytic dataset is the S5+ contract.** S5 (viz) and S6 (dashboard) read `data/processed/analytic_dataset_2026-05-20.parquet`, *not* the upstream snapshots. Re-running the cleaning notebook is only required when an upstream snapshot changes. | S5/S6 do not import from `clean.py` for the headline rollups; they read the parquet and call `shutdown_day_rollup` (currently inline in the notebook — promote to `src/` if S5 needs reusable functions). |
| 18 | S5 | **Rollups promoted to `src/internet_shutdowns/rollups.py`** (`shutdown_day_rollup`, `country_cost_rollup`, `monthly_event_series`). S6 dashboard must import from here — one rollup code path, two surfaces. Inline §9 version in the notebook left in place for narrative continuity but is now redundant. | S6 imports the same three; S7 robustness can call the same shutdown-day rollup at alternate views without re-implementing. |
| 19 | S5 | **Cost figures dedupe on `(iso3, year)` before summing.** The analytic dataset attaches each Top10VPN country-year cost to every event in that bucket — naive `cost_usd.sum()` inflates by event multiplicity. `country_cost_rollup` handles this. | S6 dashboard country drill-down + tooltip totals must use the helper, not raw `.sum()`. |
| 20 | S5 | **Display-name shortener (`display_country`).** Maps formal UN names ("Russian Federation", "Iran (Islamic Republic of)", "Venezuela (Bolivarian Republic of)") to conventional short forms for *axis labels only*. ISO-3 join keys and the underlying `country` column are unchanged. | S6 axis labels should call `display_country` too for consistency between the static hero and the dashboard. |

## Progress Tracker

| Session | Title | Status | Date | Notes |
|---------|-------|--------|------|-------|
| 1 | Scaffold + Access Now snapshot fetch | Complete | 2026-05-20 | 2102×47 snapshot from Combined sheet |
| 2 | Data loaders + remaining snapshots | Complete | 2026-05-20 | Top10VPN snapshot (169×7) + WB loader (5586×5, cached) + GADM helper (fetch on demand). 6 smoke tests pass, 1 skipped (GADM). |
| 3 | Cleaning + dedup decision + duration imputation decision | Complete | 2026-05-20 | clean.py (3 fns + resolve_iso3); 02_main.ipynb §§1–4 with two five-part blocks; 3 new tests (9 pass, 1 skip); README rows 1–2 populated. |
| 4 | Cost join + WB normalize + country grouping + platform-block decisions | Complete | 2026-05-20 | analytic_dataset_2026-05-20.parquet (1511×66) + 4 decision blocks (cost source, country grouping, platform-block treatment, snapshot pinning); README rows 3–6 populated; 9 tests pass, 1 skipped. |
| 5 | Viz module + hero figure | Complete | 2026-05-20 | viz.py (3 helpers + display_country + save_figure) + rollups.py + §12 + hero.png (800×800, caveat in title). 10 tests pass, 1 skipped. |
| 6 | Streamlit dashboard | Not started | | |
| 7 | README fill-in + smoke tests + robustness notebook + reproducibility | Not started | | |
