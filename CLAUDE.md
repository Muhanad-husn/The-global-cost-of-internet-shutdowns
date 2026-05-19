# CLAUDE.md — Project 6: The global cost of internet shutdowns

Orientation for Claude Code working inside this project's folder. This file is self-contained because this project will eventually become its own GitHub repository.

This project has a **methodology-debate caveat at its core**: the cost figures come from Top10VPN, whose methodology is widely cited *and* widely contested. The README, the dashboard, and every cost finding must treat those figures as a *reported, debated input* — not as an endorsed estimate. Read the workflow note on this below before writing any cost-related code.

---

## Portfolio principles (verbatim — read these first)

### 1. Balance: Practicality ↔ Perfectionism

- Nothing is sacred as long as we are not writing code. Even the most fundamental principles can be modified if the holistic assessment results in better efficiency, reliability, and productivity.
- Every solution must be "good enough to ship and good enough to maintain" — not perfect, not rushed.
- Apply the 80/20 rule: spend effort where it yields the most real-world value.
- When perfectionism adds cost without proportional reliability gain, choose the practical path.
- Always ask: "Is this improvement worth the time, complexity, and maintenance cost?"

### 2. AI Developer Mindset (Not Pure Mathematician)

- We are engineers solving real problems — success is measured by cost, efficiency, and reliability.
- Indicators of success:
  - **Cost**: API calls, compute, tokens, dev time
  - **Efficiency**: Time-to-value, lines of code, CI/CD speed
  - **Reliability**: Error rates, test coverage, uptime, graceful degradation
- Avoid over-engineering: a working solution beats a theoretically optimal one.
- When in doubt, prototype and measure rather than analyze indefinitely.

### 3. Don't Reinvent the Wheel

- Before writing any new logic, check if it already exists in:
  - This project
  - Installed dependencies
  - MCP servers and tools available in the environment
  - Well-maintained open-source libraries
  - Claude Code slash commands, workflows, and skills
- Prefer composition over creation; integrate before building.
- Document external sources used so future contributors can maintain them.

### 4. Show Your Work (Decision Discipline) — *portfolio-specific*

Every meaningful data-processing decision — cleaning, imputing, transforming, categorizing, feature engineering, outlier handling, threshold setting, deduplication, aggregation — is presented in **five parts** in the notebook:

1. **Problem / choice point** — what needs to be decided and why it matters downstream.
2. **Diagnostic analysis** — actual code that explores the data to inform the choice.
3. **Options considered** — at least 2–3 reasonable alternatives, named explicitly.
4. **Decision + rationale** — anchored in the diagnostic, not in convention.
5. **Sensitivity** — robustness check where applicable, or explicit note that the result isn't sensitive to this choice.

No conventional choices ("just impute with mean"); every choice is **educated**. This is the lab-work signal that distinguishes a portfolio piece from a tutorial.

See `_template/notebooks/NOTEBOOK_STRUCTURE.md` for the canonical five-part block template, and `_template/src/project_name/diagnostics.py` for the helpers that operationalize the diagnostic step (`missingness_summary`, `missingness_pattern`, `distribution_summary`, `distribution_compare`, `before_after`, `compare_alternatives`).

(Within this project, the corresponding files live at `notebooks/NOTEBOOK_STRUCTURE.md` and `src/internet_shutdowns/diagnostics.py` — the `_template/` reference above is the canonical source from the monorepo.)

This principle is portfolio-specific because the portfolio's brand is **"balance practicality vs. perfectionism — neat lab work, not ship-ready apps."** Methodological visibility is part of the deliverable.

### How these interact

Principles 1–3 are about *engineering pragmatism* — ship working things, don't over-engineer, reuse what exists. Principle 4 is about *methodological rigor* — show how data decisions were made.

There is a creative tension between #2 (AI Developer Mindset, "avoid over-engineering") and #4 (Show Your Work, "document every choice"). Resolve it this way: **be lean in the code, rigorous in the notebook**. The code can be short and pragmatic; the notebook must show the reasoning behind any non-trivial data manipulation. This is why diagnostics live in `notebooks/02_main.ipynb` (the deliverable), not in the production-style `src/` modules.

---

## Project context

**The question.** Where, when, and at what estimated economic cost have governments imposed internet shutdowns since 2019, and is the trend rising?

**Why it matters in the LMIC / Global South frame.** Internet shutdowns are concentrated in lower-resource and politically contested settings, and they are a load-bearing topic for the AI-governance and information-ecosystem conversation. Mapping the shape of the phenomenon — country, duration, type, cost (with appropriate caveat) — supports both journalism and the broader policy debate about platform accountability and state power over communications infrastructure. The project is **descriptive cartographic + time-series**. It does **not** produce original cost estimates (we report Top10VPN's figures with caveats), and it does **not** model whether shutdowns achieve their stated political goals — that is a different research question.

## Data sources

| Source | Granularity | Time | Notes / caveats |
|--------|-------------|------|-----------------|
| [Access Now #KeepItOn](https://www.accessnow.org/campaign/keepiton/) | Event-level (country, dates, type, reason, scope) | 2016–latest (use 2019+) | Registry is reported-and-curated, not exhaustive. Authoritarian-state shutdowns with no press coverage are systematically under-counted. Contains overlapping records when one event is reported through multiple sources — **deduplication is one of the documented decisions**. |
| [Top10VPN cost reports](https://www.top10vpn.com/research/cost-of-internet-shutdowns/) | Country × year × cost in USD | 2019–latest | **Methodology contested.** Cost formula = GDP × digital-economy contribution × shutdown duration × affected population fraction. Critics argue this overstates cash-economy impact. Treat as reported, debated input — not as a finding. |
| [World Bank Indicators API](https://data.worldbank.org/) | Country × year (GDP, internet penetration, population) | 1960–latest | Standard caveats: missingness in low-resource settings, retrospective revisions, indicator-definition shifts over time. |
| [GADM 4.1](https://gadm.org/) | Country (admin-0) polygons | Current | Used for the choropleth and country drill-down map. |

Access notes: cache via `requests-cache` for the World Bank API and any Top10VPN-API access; commit snapshot parquets for Access Now and Top10VPN with dated filenames. Both sources revise historical years as new evidence emerges.

## Planned method (one paragraph)

Ingest Access Now #KeepItOn shutdown events (2019–latest) and deduplicate where the same shutdown is reported through multiple records. Standardize country, dates, type (full / throttle / platform-block), scope (national / regional / app-specific), and stated reason. Compute duration per event, with an explicit imputation rule for missing or "ongoing" end-dates. Layer Top10VPN per-country-per-year cost estimates onto the event dataset with prominent methodology caveats. Join World Bank GDP / internet-penetration / population for normalization. Build a Streamlit dashboard with: world choropleth (total shutdown-days or cost), country drill-down (event timeline + per-event details), time series (monthly count, cumulative cost). Produce the hero static figure: top-10 countries by total estimated shutdown cost 2019–latest, with the methodology caveat printed in the chart title or annotation.

## Visual style

**Plotly** for the dashboard's world map, country drill-down, time-series, and bar charts. Justification: the headline deliverable is the dashboard — hover state, click-through, and country-level drill-down depend on Plotly's interactivity. A static export of the hero "top-10 countries" figure (via `plotly.io.write_image`) ships alongside so the GitHub README and social-media share previews still have a clean static image.

## Done definition

- [ ] Cleaned shutdown event dataset 2019–latest, deduplicated
- [ ] Per-country, per-year shutdown duration and estimated economic cost
- [ ] Streamlit dashboard: world map, country drill-down, time series
- [ ] Hero figure: top-10 countries by total shutdown cost (with methodology caveat surfaced)
- [ ] README with **Methodological decisions table** + explicit data caveat (cost estimation methodology is debated)
- [ ] **Every data-processing decision documented in five-part form**
- [ ] Notebook reproducible top-to-bottom from pinned snapshots

## Expected major decisions to document

These are the decisions identified in `PORTFOLIO_PLAN.md` as load-bearing, plus two project-specific additions (platform-specific-block treatment, snapshot pinning) surfaced during this scoping pass. Each gets a five-part block inline in `notebooks/02_main.ipynb`, and a row in the README decisions table.

1. **Shutdown event deduplication** — the Access Now registry contains overlapping records when one shutdown is reported through multiple channels, or when a "shutdown" spans multiple regions / dates that are recorded as separate rows. Define the dedup rule: country + start-date proximity (within X days) + type match → merge. Diagnose how many rows the rule collapses and spot-check edge cases.
2. **Duration calculation when end-date is missing or "ongoing"** — events with no recorded end-date are common (the shutdown ended without an announcement, or is still active). Options: drop, impute as registry-snapshot-date, impute as a fixed conservative ceiling (e.g. 30 days), or carry through as missing-with-explicit-flag. Affects the cost rollup.
3. **Cost estimation source choice** — Top10VPN is the dominant source; some country-specific estimates exist in academic literature. Decision: use Top10VPN as primary for cross-country comparability, **surface the methodology debate prominently**, optionally cite academic alternates where they exist.
4. **Country grouping for the LMIC focus** — World Bank income group (low / lower-middle / upper-middle), UN LDC list, or a custom regional grouping. Each gives a different "LMIC" frame; the choice affects the headline rankings.
5. **Treatment of platform-specific blocks** — Access Now records full blackouts, throttling, and platform-specific blocks (e.g. Twitter blocked in country X) as distinct event types. Combining them in a single shutdown-day count inflates duration; separating them complicates the world map. Decision: present both views (combined + separated) with the combined view as the headline and the separated view in the drill-down.
6. **Snapshot pinning** — both Access Now and Top10VPN revise prior years. Pin dated snapshots for both. Diagnostic: compare two snapshots taken X months apart and report median per-country revision magnitude.

Out of scope for this project: original cost estimation, modeling whether shutdowns achieve political goals, individual-platform attribution, real-time monitoring (this is a retrospective study).

## Files orientation (where to find what once scaffolded)

- `README.md` — project brief, decisions summary table
- `CLAUDE.md` — this file (orientation for future Claude Code sessions)
- `pyproject.toml` — declared dependencies; install with `pip install -e ".[viz,geo]"`
- `notebooks/02_main.ipynb` — the analysis (THE deliverable, decision blocks inline)
- `notebooks/03_robustness.ipynb` — deduplication threshold sensitivity, alternate duration imputation, alternate country grouping
- `notebooks/_scratch/01_explore.ipynb` — ugly EDA (gitignored)
- `notebooks/NOTEBOOK_STRUCTURE.md` — copy of the decision-discipline pattern (carry over from `_template/`)
- `src/internet_shutdowns/data.py` — Access Now, Top10VPN, World Bank, GADM loaders with `requests-cache` and snapshot pinning
- `src/internet_shutdowns/clean.py` — deduplication + standardization + duration calculation
- `src/internet_shutdowns/viz.py` — world-map, time-series, top-10-bar helpers (Plotly)
- `src/internet_shutdowns/diagnostics.py` — diagnostic helpers used inside notebook decision blocks
- `data/raw/` — fetched source files (gitignored if large)
- `data/processed/access_now_snapshot_YYYY-MM-DD.parquet` — pinned Access Now snapshot (committed; canonical)
- `data/processed/top10vpn_snapshot_YYYY-MM-DD.parquet` — pinned Top10VPN cost snapshot (committed; canonical)
- `data/processed/` — derived analytic dataset (parquet, committed)
- `figures/` — saved figures, including `hero.png` static export of top-10 chart (committed)
- `app/streamlit_dashboard.py` — world map + country drill-down + time series (primary interactive deliverable)
- `tests/test_smoke.py` — minimal smoke tests for data loaders, deduplication, and key viz functions

## Project-specific workflow notes

### ⚠️ Top10VPN cost methodology is debated — this is a limitation, not a finding

Top10VPN's cost-of-shutdown methodology applies a top-down formula:

> cost ≈ GDP × digital-economy contribution × shutdown duration × affected-population fraction

Researchers in development economics have argued this **overstates** true economic impact in cash-economy / informal-sector-dominated contexts, where a meaningful share of economic activity doesn't depend on internet connectivity. Other researchers have argued the figures **understate** impact by missing indirect effects (e.g. on civic mobilization, on remittance flows, on supply-chain coordination). The debate is real and is not resolved by the data.

The portfolio's posture:
- Cost figures appear in the dashboard and the hero chart **with an explicit caveat surfaced in the title or annotation** (e.g. "Estimated cost per Top10VPN methodology — see limitations").
- The methodological-decisions table lists "Cost estimation source choice" as a documented decision, anchored in the methodology-debate diagnostic, not in convention.
- The README "Limitations" section explicitly names this as a **limitation**, not a finding.
- The notebook narrative cites both the Top10VPN methodology page and at least one critical secondary source so the reader can form their own view.

If you find yourself about to write narrative copy that says "the cost of shutdowns is X dollars" full-stop without the methodology caveat, stop and reframe as "Top10VPN estimates the cost at X dollars, under their methodology, which has known critiques."

### Access Now deduplication needs care

The #KeepItOn registry is reported-and-curated. One real-world shutdown may appear as multiple rows when:
- It was reported through multiple sources (each generating a record).
- It spanned multiple admin regions (each region recorded as a row).
- It was lifted and re-imposed within days (registry may treat as one event or two).

The dedup rule needs to be defined and diagnosed. A reasonable starting point: collapse rows where `country` matches, `start_date` is within ±N days, and `type` matches. Tune N against a held-out probe set (eyeball ~30 cases and check whether the rule's merges match your judgement). Document the false-merge rate and the unmerged-duplicate rate. This is one of the load-bearing decisions for the cost rollup, because over-merging deflates per-country totals and under-merging inflates them.

### Snapshot pinning for revisable sources

Both Access Now's registry and Top10VPN's annual reports restate prior years as new evidence emerges. Pin both with dated filenames:
- `data/processed/access_now_snapshot_2026-05-XX.parquet`
- `data/processed/top10vpn_snapshot_2026-05-XX.parquet`

The main notebook reads from these snapshots — not from the live source — so re-running the notebook six months later produces identical numbers. Re-snapshotting is an explicit, documented step with a revision-magnitude diagnostic (compare old vs. new snapshot, report median per-country revision).

### Other workflow notes

- The dashboard is the headline deliverable; design for it first, then derive the static hero figure from the same data and viz functions. Don't build two parallel viz pipelines.
- Hero figure constraint: top-10 countries by total estimated shutdown cost must read well at LinkedIn-post thumbnail size (~800×800). The methodology caveat in the title needs to remain legible — don't make it so small it disappears in the thumbnail.
- World Bank API: be patient with rate limits, cache aggressively. The relevant indicators are stable; you do not need to re-fetch each session.
- Out-of-scope tempting tangents to avoid: original cost estimation, modeling political effectiveness of shutdowns, real-time monitoring, individual-platform attribution.
