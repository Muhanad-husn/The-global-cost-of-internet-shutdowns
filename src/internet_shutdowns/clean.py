"""Cleaning utilities for the Access Now #KeepItOn event registry.

Three public functions:

- :func:`standardize_event_columns` shapes the raw snapshot into an analytic
  frame: ISO-3 country codes, parsed durations, derived ``platform_block``
  flag, multi-country rows split into one row per country.
- :func:`dedupe_events` collapses near-duplicate rows where the same event is
  reported through multiple sources.
- :func:`compute_duration` materializes per-event ``duration_days`` with an
  explicit imputation strategy for missing / ongoing end-dates.

The dedup and duration-imputation decisions are documented in five-part form
inline in ``notebooks/02_main.ipynb`` (§3 and §4). The default parameters here
reflect the choices made there; pass alternatives to reproduce the sensitivity
checks in ``notebooks/03_robustness.ipynb``.
"""

from __future__ import annotations

import re
from typing import Iterable, Literal

import pandas as pd

from .data import _country_to_iso3


# ---------------------------------------------------------------------------
# Country resolution (Access Now-specific extensions)
# ---------------------------------------------------------------------------

# pycountry's bundled data doesn't resolve the parenthetical long-forms used
# by Access Now ("Iran (Islamic Republic of)" etc.). Stripping the parenthesis
# and re-trying covers them all without per-country overrides.
_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")


def _strip_parenthetical(name: str) -> str:
    return _PAREN_RE.sub("", name).strip()


def resolve_iso3(name: str | None) -> str | None:
    """Best-effort ISO-3 resolution for Access Now country labels.

    Tries the shared :func:`_country_to_iso3` first; on failure, strips a
    trailing parenthetical (``"Iran (Islamic Republic of)"`` → ``"Iran"``)
    and retries. Returns ``None`` for unresolvable names — callers should
    decide whether to drop or keep these.
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return None
    direct = _country_to_iso3(name)
    if direct is not None:
        return direct
    stripped = _strip_parenthetical(name)
    if stripped and stripped != name:
        return _country_to_iso3(stripped)
    return None


# ---------------------------------------------------------------------------
# Standardization
# ---------------------------------------------------------------------------

# Raw shutdown_type values map onto three canonical headline types. Platform
# blocks are *not* a raw type — they're derived from shutdown_extent and the
# per-platform ``*_affected`` columns and surface as the ``platform_block``
# bool. See Decision Log #2 in IMPLEMENTATION_PLAN.md.
_TYPE_MAP = {
    "Shutdown": "full_blackout",
    "Shutdown, Throttle": "full_blackout",  # full blackout co-occurring with throttle elsewhere — headline type is the blackout
    "Throttle": "throttle",
    "Unknown": "other",
}

PLATFORM_AFFECTED_COLS = (
    "facebook_affected",
    "twitter_affected",
    "whatsapp_affected",
    "instagram_affected",
    "telegram_affected",
    "other_affected",
    "sms_affected",
    "phonecall_affected",
)


def _coerce_duration_hours(s: pd.Series) -> pd.Series:
    """Coerce the raw ``duration`` column (mixed string) to numeric hours.

    Non-numeric values (``"Curfew Style"``, ``"for a few hours"``, ...) become
    NaN. Negative and absurdly large values are also nulled — the raw column
    contains some Excel-date-shaped garbage (e.g. ``"-44270"``) that is
    clearly not a duration in hours. The cap is 20 years (175,200 hours);
    the longest legitimate event (Iran 2009, Turkey 2013) is ~17 years.
    """
    n = pd.to_numeric(s, errors="coerce")
    n = n.where((n >= 0) & (n <= 175_200))
    return n


def _split_multicountry(df: pd.DataFrame) -> pd.DataFrame:
    """Expand rows whose ``country`` is a ``;``-joined list into one row each.

    Three in-scope rows (2019+) carry multi-country values such as
    ``"Cameroon; Central African Republic"``. Splitting preserves the original
    event metadata under each country so the per-country rollups stay correct.
    """
    needs_split = df["country"].astype("string").str.contains(";", na=False)
    if not needs_split.any():
        return df
    keep = df.loc[~needs_split].copy()
    expanded_rows = []
    for _, row in df.loc[needs_split].iterrows():
        parts = [p.strip() for p in str(row["country"]).split(";") if p.strip()]
        for p in parts:
            new_row = row.copy()
            new_row["country"] = p
            expanded_rows.append(new_row)
    expanded = pd.DataFrame(expanded_rows)
    out = pd.concat([keep, expanded], ignore_index=True)
    return out


def standardize_event_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add canonical analytic columns to the raw Access Now snapshot.

    Adds, without removing any raw columns:

    - ``iso3`` — ISO-3 country code via :func:`resolve_iso3`. ``None`` for
      Somaliland (de-facto state, no ISO-3166 code).
    - ``type`` — ordered categorical ``{full_blackout, throttle, other}``,
      mapped from raw ``shutdown_type``.
    - ``duration_hours`` — numeric coercion of raw ``duration``.
    - ``platform_block`` — bool, True if ``shutdown_extent`` contains
      ``"Service-based"`` OR any ``*_affected`` column is ``"Yes"``.
    - ``platforms_affected`` — comma-joined list of affected platform names,
      for drill-down display.

    Multi-country rows (e.g. ``"Cameroon; Central African Republic"``) are
    split into one row per country first, since downstream joins on ``iso3``
    cannot handle composites.
    """
    out = _split_multicountry(df).copy()

    out["iso3"] = out["country"].map(resolve_iso3).astype("string")

    type_cat = pd.Categorical(
        out["shutdown_type"].map(_TYPE_MAP),
        categories=["full_blackout", "throttle", "other"],
        ordered=True,
    )
    out["type"] = type_cat

    out["duration_hours"] = _coerce_duration_hours(out["duration"])

    extent_has_service = (
        out["shutdown_extent"].astype("string").str.contains("Service-based", na=False)
    )
    # eq("Yes") on string dtype preserves NA; fill to False so .any works.
    affected_mask = out[list(PLATFORM_AFFECTED_COLS)].eq("Yes").fillna(False)
    any_platform_yes = affected_mask.any(axis=1)
    out["platform_block"] = (extent_has_service | any_platform_yes).astype(bool)

    platform_names = [c.removesuffix("_affected") for c in PLATFORM_AFFECTED_COLS]
    out["platforms_affected"] = affected_mask.apply(
        lambda r: ", ".join(n for n, v in zip(platform_names, r) if bool(v)),
        axis=1,
    ).astype("string")

    return out


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _normalize_area(s: object) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return "__no_area__"
    return str(s).strip().lower()


def _completeness_score(row: pd.Series) -> int:
    """Higher = more fields populated. Used as a tie-breaker when merging."""
    return int(row.notna().sum())


def dedupe_events(
    df: pd.DataFrame,
    days_tolerance: int = 0,
    keep_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Collapse near-duplicate event rows.

    Cluster definition: rows that share ``(iso3, type, normalized area_name)``
    and have ``start_date`` within ``days_tolerance`` days of another row in
    the cluster (transitive: A↔B, B↔C → A,B,C merge). The representative row
    kept per cluster is the most-populated one (max non-null count), ties
    broken by earliest ``start_date``.

    Why ``area_name`` is part of the key: in the same country/date/type two
    different regional shutdowns (e.g. Ethiopia/Tigray vs. Ethiopia/Wellega
    on the same day) are *not* duplicates — they're co-temporal events in
    distinct locales. Including normalized area_name preserves that
    distinction. Rows with no area_name are pooled under a single sentinel
    so they can still merge with each other.

    ``days_tolerance=0`` (default) means same-day merges only — anchored in
    the diagnostic in notebook §3. Pass higher values for the sensitivity
    check in ``03_robustness.ipynb``.
    """
    if df.empty:
        return df.copy()

    work = df.copy()
    if "iso3" not in work.columns or "type" not in work.columns:
        raise ValueError(
            "dedupe_events expects a frame produced by standardize_event_columns"
        )

    work["_area_norm"] = work["area_name"].map(_normalize_area)
    work["_orig_idx"] = work.index

    groups = work.groupby(["iso3", "type", "_area_norm"], dropna=False, observed=True)
    representatives: list[pd.Series] = []
    cluster_ids: list[int] = []
    next_cluster_id = 0

    for _, sub in groups:
        sub = sub.sort_values("start_date").reset_index(drop=True)
        if len(sub) == 1:
            sub["_cluster_id"] = next_cluster_id
            representatives.append(sub.iloc[0])
            cluster_ids.append(next_cluster_id)
            next_cluster_id += 1
            continue

        # Transitive same-day-within-tol clustering via sorted-gap walk.
        cluster_assignments = [0]
        for i in range(1, len(sub)):
            prev_start = sub["start_date"].iloc[i - 1]
            curr_start = sub["start_date"].iloc[i]
            gap_days = (curr_start - prev_start).days
            if gap_days <= days_tolerance:
                cluster_assignments.append(cluster_assignments[-1])
            else:
                cluster_assignments.append(cluster_assignments[-1] + 1)

        for local_cid in set(cluster_assignments):
            members = sub.iloc[
                [i for i, c in enumerate(cluster_assignments) if c == local_cid]
            ]
            scores = members.apply(_completeness_score, axis=1)
            best = members.loc[scores.idxmax()]
            representatives.append(best)
            cluster_ids.append(next_cluster_id + local_cid)
        next_cluster_id += max(cluster_assignments) + 1

    out = pd.DataFrame(representatives).reset_index(drop=True)
    out = out.drop(columns=["_area_norm", "_orig_idx"], errors="ignore")
    return out


# ---------------------------------------------------------------------------
# Duration imputation
# ---------------------------------------------------------------------------

DurationStrategy = Literal["hybrid", "drop", "snapshot_date", "ceiling", "flag"]


def compute_duration(
    df: pd.DataFrame,
    missing_strategy: DurationStrategy = "hybrid",
    snapshot_date: str = "2026-05-20",
    ceiling_days: int = 30,
) -> pd.DataFrame:
    """Materialize ``duration_days`` from ``start_date`` / ``end_date`` with
    explicit handling of missing end-dates.

    Adds:

    - ``duration_days`` — float; (end_date - start_date) in days.
    - ``duration_imputed`` — bool; True when the value did not come from a
      recorded end_date.
    - ``duration_source`` — string; one of ``{"recorded", "duration_field",
      "snapshot_date", "ceiling", "missing"}``.

    Strategies (chosen via the diagnostic in notebook §4):

    - ``"hybrid"`` (default): prefer the recorded ``end_date``; else fall
      back to the raw ``duration_hours`` field where present; else, if the
      event is ``Ongoing`` per ``shutdown_status``, impute the snapshot date;
      else carry as NaN with the flag set. This is the most defensible
      mixture — uses every signal the registry provides, fabricates only
      where the status field actively says the event is still running.
    - ``"drop"``: rows with missing end_date are excluded.
    - ``"snapshot_date"``: all missing end_dates set to ``snapshot_date``.
    - ``"ceiling"``: all missing end_dates set to start + ``ceiling_days``.
    - ``"flag"``: pure carry-as-missing; ``duration_days`` is NaN for any
      missing end_date, regardless of status.
    """
    # Recorded end_date < start_date is a data-entry error in the raw
    # registry; treat such rows as having no usable end_date.
    def _recorded_delta(frame: pd.DataFrame) -> pd.Series:
        d = (frame["end_date"] - frame["start_date"]).dt.days
        return d.where(d >= 0)

    if missing_strategy == "drop":
        delta = _recorded_delta(df)
        out = df.loc[delta.notna()].copy()
        out["duration_days"] = delta.dropna().astype("Float64").values
        out["duration_imputed"] = False
        out["duration_source"] = pd.Series("recorded", index=out.index, dtype="string")
        return out

    out = df.copy()
    snap = pd.Timestamp(snapshot_date)

    delta_recorded = _recorded_delta(out)
    recorded_mask = delta_recorded.notna()

    duration_days = pd.Series(pd.NA, index=out.index, dtype="Float64")
    duration_source = pd.Series("missing", index=out.index, dtype="string")
    duration_imputed = pd.Series(False, index=out.index, dtype=bool)

    duration_days.loc[recorded_mask] = delta_recorded.loc[recorded_mask].astype("Float64")
    duration_source.loc[recorded_mask] = "recorded"

    missing_mask = ~recorded_mask

    if missing_strategy == "snapshot_date":
        impute = (snap - out["start_date"]).dt.days.clip(lower=0).astype("Float64")
        duration_days.loc[missing_mask] = impute.loc[missing_mask]
        duration_source.loc[missing_mask] = "snapshot_date"
        duration_imputed.loc[missing_mask] = True

    elif missing_strategy == "ceiling":
        duration_days.loc[missing_mask] = float(ceiling_days)
        duration_source.loc[missing_mask] = "ceiling"
        duration_imputed.loc[missing_mask] = True

    elif missing_strategy == "flag":
        # leave as NA; flag stays True for missing
        duration_imputed.loc[missing_mask] = True

    elif missing_strategy == "hybrid":
        # (a) recover from duration_hours where present
        if "duration_hours" in out.columns:
            dh = out["duration_hours"]
            dh_mask = missing_mask & dh.notna()
            duration_days.loc[dh_mask] = (dh.loc[dh_mask] / 24.0).astype("Float64")
            duration_source.loc[dh_mask] = "duration_field"
            duration_imputed.loc[dh_mask] = True
        # (b) impute ongoing events to snapshot date
        still_missing = duration_days.isna()
        if "shutdown_status" in out.columns:
            ongoing_mask = still_missing & out["shutdown_status"].eq("Ongoing")
            impute_ongoing = (snap - out["start_date"]).dt.days.clip(lower=0).astype("Float64")
            duration_days.loc[ongoing_mask] = impute_ongoing.loc[ongoing_mask]
            duration_source.loc[ongoing_mask] = "snapshot_date"
            duration_imputed.loc[ongoing_mask] = True
        # (c) the rest stay missing with flag
        duration_imputed.loc[duration_days.isna()] = True
    else:
        raise ValueError(f"Unknown missing_strategy: {missing_strategy!r}")

    out["duration_days"] = duration_days
    out["duration_source"] = duration_source
    out["duration_imputed"] = duration_imputed
    return out
