# Reproducibility log

Session 7 reproducibility check, run 2026-05-20 on the existing `portfolio`
conda env (Python 3.14.4, Windows 11). Per Session 7 plan, this run does
**not** rebuild the env from scratch — it verifies the pinned snapshots +
shipped artifacts execute end-to-end and records wall-clock for the README.

For a brand-new environment, run `pip install -e ".[viz,geo]"` first; this
log is the "everything is already installed" path.

## What was run

| Step | Command | Wall-clock | Result |
|---|---|---|---|
| Smoke tests | `pytest -q` | 21.9 s | 12 passed, 1 skipped (GADM — fetch-on-demand 50 MB file is intentionally absent) |
| Main notebook | `jupyter nbconvert --execute --inplace notebooks/02_main.ipynb` | 71.4 s | rc 0; 226 KB output, all decision blocks render |
| Robustness notebook | `jupyter nbconvert --execute --inplace notebooks/03_robustness.ipynb` | 48.5 s | rc 0; all three sensitivity sweeps complete |
| Dashboard launch | `streamlit run app/streamlit_dashboard.py --server.headless true --server.port 8521` | ~5 s to ready | `GET /_stcore/health` returns 200; `GET /` returns a 5.4 KB Streamlit shell |

**Full run time: ~2 min 22 s** (pytest + both notebooks + dashboard probe).
The headline notebook (02_main) alone is ~1 min 11 s.

## Environment

- Python: 3.14.4 (conda env `portfolio`)
- Key versions (from `pip freeze`):
  - pandas, plotly, geopandas, requests-cache, streamlit 1.57.0, kaleido
- HTTP cache: `.cache/http_cache.sqlite` (~1.2 MB after first WB pull, 30-day TTL)

## Notes / surprises

- **No surprises this run.** All numbers in the README *Findings* section
  match the freshly re-executed notebook outputs (top-10 cost ranking,
  bucket totals, per-year event counts, 86.4% cost coverage).
- The notebook's `02_main.ipynb` §10 includes a *snapshot revision*
  diagnostic that is structurally untestable until a second snapshot
  exists. The placeholder runs cleanly; populating it is a future-session
  task once the next snapshot is pulled.
- **Streamlit env-leak gotcha (S6 carry-over).** Streamlit + plotly + the
  project package live in the `portfolio` conda env. Running from base
  conda fails with `ModuleNotFoundError: No module named 'plotly'`. Always
  invoke via the env's python (`C:/Users/mou97/.conda/envs/portfolio/python.exe -m streamlit ...`)
  or activate `portfolio` first.

## What this log does *not* cover

- A clean `pip install -e ".[viz,geo]"` from a fresh env — Session 7 chose
  the existing-env path. Dependency drift in a future Python release would
  not be caught here.
- The Playwright screenshot pipeline (`notebooks/_scratch/capture_dashboard_screenshot.py`).
  The shipped screenshot at `figures/dashboard_screenshot.png` is the
  Session 6 capture; regenerating it requires `playwright install chromium`.
- The GADM polygon download (one-time 50 MB fetch). The Plotly built-in
  country layer is the default viz path, so GADM is fetch-on-demand only.
