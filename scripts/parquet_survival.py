"""Kaplan-Meier survival analysis from the posts_type1.parquet export.

Usage:
    python scripts/parquet_survival.py
    python scripts/parquet_survival.py --parquet data/posts_type1.parquet
    python scripts/parquet_survival.py --observation-end 2026-04-21
    python scripts/parquet_survival.py --exclude-comments
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import math

from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import (
    logrank_test,
    proportional_hazard_test,
    survival_difference_at_fixed_point_in_time_test,
)

OBSERVATION_END_DEFAULT = "2026-04-21"

HORIZONS_DAYS = {
    "6 months": 182,
    "1 year":   365,
    "2 years":  730,
    "5 years":  1825,
}


def load_and_prepare(
    parquet_path: Path,
    observation_end: pd.Timestamp,
    exclude_comments: bool = False,
    min_lifespan_days: float = 1.0,
) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path)

    df["start"] = pd.to_datetime(df["hl_FirstAcceptedAnswerCreationDate"], utc=True)

    if exclude_comments:
        signals = pd.concat([
            pd.to_datetime(df["hl_FirstAcceptedAnswerOvertakeDate"], utc=True),
            pd.to_datetime(df["hl_FirstAcceptedAnswerFirstVelocityFlipDate"], utc=True),
            pd.to_datetime(df["hl_FirstAcceptedAnswerFirstBountyAfterAcceptanceDate"], utc=True),
        ], axis=1).min(axis=1)
        df["event_at"] = signals
    else:
        df["event_at"] = pd.to_datetime(df["hl_FirstAcceptedAnswerDeathDate"], utc=True)

    df = df[df["start"].notna()].copy()

    df["event_observed"] = (df["event_at"].notna() & (df["event_at"] <= observation_end)).astype(int)

    censor_time = df["event_at"].where(df["event_observed"] == 1, observation_end)
    df["duration_days"] = (censor_time - df["start"]).dt.total_seconds() / 86_400

    # drop durations below minimum lifespan (timestamps rounded to midnight make
    # sub-day durations unreliable)
    df = df[df["duration_days"] >= min_lifespan_days].copy()

    def _bucket(row) -> str | None:
        if row.get("hl_IsStableBucket") is True or row.get("hl_IsStableBucket") == 1:
            return "stable"
        if row.get("hl_IsEphemeralBucket") is True or row.get("hl_IsEphemeralBucket") == 1:
            return "ephemeral"
        return None

    df["bucket"] = df.apply(_bucket, axis=1)
    return df


def time_at_pct_dead(kmf: KaplanMeierFitter, pct: float) -> float | None:
    threshold = 1.0 - pct
    curve = kmf.survival_function_.reset_index()
    time_col, surv_col = curve.columns[0], curve.columns[1]
    below = curve[curve[surv_col] <= threshold]
    return None if below.empty else float(below.iloc[0][time_col])


def half_life(kmf: KaplanMeierFitter) -> float | None:
    return time_at_pct_dead(kmf, 0.5)


def compute_rmst(kmf: KaplanMeierFitter, tau: float) -> float:
    import numpy as np
    sf = kmf.survival_function_.reset_index()
    time_col, surv_col = sf.columns[0], sf.columns[1]
    sf = sf[sf[time_col] <= tau].copy()
    times = [0.0] + list(sf[time_col].values) + [tau]
    surv  = [1.0] + list(sf[surv_col].values) + [float(sf[surv_col].iloc[-1]) if not sf.empty else 1.0]
    return float(np.trapezoid(surv, times))


def survival_at(kmf: KaplanMeierFitter, t: float) -> float:
    return float(kmf.predict(t))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--parquet",
        default=str(Path(__file__).resolve().parents[1] / "data" / "posts_type1.parquet"),
    )
    parser.add_argument("--observation-end", default=OBSERVATION_END_DEFAULT)
    parser.add_argument(
        "--exclude-comments", action="store_true",
        help="Use only overtake, velocity-flip and bounty signals.",
    )
    parser.add_argument(
        "--min-lifespan", type=float, default=1.0,
        help="Minimum lifespan in days (default 1.0).",
    )
    args = parser.parse_args()

    observation_end = pd.Timestamp(args.observation_end, tz="UTC")
    parquet_path = Path(args.parquet)

    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

    df = load_and_prepare(
        parquet_path, observation_end,
        exclude_comments=args.exclude_comments,
        min_lifespan_days=args.min_lifespan,
    )
    if args.exclude_comments:
        print("(comment onset excluded — using overtake, velocity-flip, bounty only)\n")

    bucketed = df[df["bucket"].notna()].copy()
    ephemeral = bucketed[bucketed["bucket"] == "ephemeral"]
    stable    = bucketed[bucketed["bucket"] == "stable"]

    print(f"Observation end : {observation_end.date()}")
    print(f"Total questions : {len(df):,}")
    print(f"  ephemeral     : {len(ephemeral):,}  (events: {ephemeral['event_observed'].sum():,})")
    print(f"  stable        : {len(stable):,}  (events: {stable['event_observed'].sum():,})")
    print()

    # ── Kaplan-Meier ──────────────────────────────────────────────────────────
    kmf_e = KaplanMeierFitter(label="ephemeral").fit(
        ephemeral["duration_days"], ephemeral["event_observed"]
    )
    kmf_s = KaplanMeierFitter(label="stable").fit(
        stable["duration_days"], stable["event_observed"]
    )

    logrank = logrank_test(
        ephemeral["duration_days"], stable["duration_days"],
        event_observed_A=ephemeral["event_observed"],
        event_observed_B=stable["event_observed"],
    )

    print(f"Log-rank p-value: {logrank.p_value:.4e} (p < 0.0001)" if logrank.p_value < 0.0001 else f"Log-rank p-value: {logrank.p_value:.4f}")
    print()

    # ── Cumulative incidence at fixed horizons ────────────────────────────────
    print("=== Cumulative incidence 1-S(t) at fixed horizons ===")
    print(f"{'horizon':20s}  {'ephemeral':>10}  {'stable':>10}  {'p-value':>10}")
    for label, t in HORIZONS_DAYS.items():
        ci_e = 1 - survival_at(kmf_e, t)
        ci_s = 1 - survival_at(kmf_s, t)
        try:
            res = survival_difference_at_fixed_point_in_time_test(t, kmf_e, kmf_s)
            pval = "p < 0.0001" if res.p_value < 0.0001 else f"{res.p_value:.4f}"
        except Exception:
            pval = "n/a"
        print(f"{label:20s}  {ci_e:>10.4%}  {ci_s:>10.4%}  {pval:>10}")
    print()

    # ── Cox proportional hazards + PH test + C-index ─────────────────────────
    bucketed["is_ephemeral"] = (bucketed["bucket"] == "ephemeral").astype(int)
    cox_data = bucketed[["duration_days", "event_observed", "is_ephemeral"]].copy()
    cox = CoxPHFitter()
    cox.fit(cox_data, duration_col="duration_days", event_col="event_observed")

    hr    = cox.hazard_ratios_["is_ephemeral"]
    ci    = cox.confidence_intervals_.loc["is_ephemeral"]
    pval  = cox.summary["p"]["is_ephemeral"]
    ci_lo = math.exp(ci["95% lower-bound"])
    ci_hi = math.exp(ci["95% upper-bound"])
    print("=== Cox proportional hazards ===")
    print(f"Hazard ratio (ephemeral vs stable): {hr:.3f}")
    print(f"95% CI: [{ci_lo:.3f}, {ci_hi:.3f}]")
    print(f"p-value: {'p < 0.0001' if pval < 0.0001 else f'{pval:.4f}'}")
    print(f"C-index (discrimination): {cox.concordance_index_:.4f}")
    print()

    # ── Proportional hazards assumption test (Schoenfeld residuals) ───────────
    print("=== Proportional hazards test (Schoenfeld residuals) ===")
    try:
        ph = proportional_hazard_test(cox, cox_data, time_transform="rank")
        p_ph = ph.summary["p"]["is_ephemeral"]
        print(f"p-value for is_ephemeral: {'p < 0.0001' if p_ph < 0.0001 else f'{p_ph:.4f}'}")
        if p_ph < 0.05:
            print("=> WARNING: PH assumption may be violated (p < 0.05) — HR changes over time")
        else:
            print("=> PH assumption holds (p >= 0.05) — HR is stable over time")
    except Exception as e:
        print(f"Could not run PH test: {e}")
    print()

    # ── RMST ─────────────────────────────────────────────────────────────────
    tau = min(ephemeral["duration_days"].max(), stable["duration_days"].max())
    rmst_e = compute_rmst(kmf_e, tau)
    rmst_s = compute_rmst(kmf_s, tau)
    print(f"=== RMST (tau = {tau:.0f} days) ===")
    print(f"  ephemeral : {rmst_e:.1f} days")
    print(f"  stable    : {rmst_s:.1f} days")
    print(f"  difference: {rmst_e - rmst_s:.1f} days  (ephemeral − stable)")
    print()

    # ── Sensitivity analysis (different min_lifespan thresholds) ─────────────
    print("=== Sensitivity analysis (HR across min_lifespan thresholds) ===")
    print(f"{'min lifespan':15s}  {'events (e/s)':>14}  {'HR':>8}  {'95% CI':>20}  {'p-value':>10}")
    for threshold in [1, 7, 30]:
        s_df = load_and_prepare(
            parquet_path, observation_end,
            exclude_comments=args.exclude_comments,
            min_lifespan_days=threshold,
        )
        s_bkt = s_df[s_df["bucket"].notna()].copy()
        s_bkt["is_ephemeral"] = (s_bkt["bucket"] == "ephemeral").astype(int)
        s_cox = CoxPHFitter()
        s_cox.fit(s_bkt[["duration_days", "event_observed", "is_ephemeral"]],
                  duration_col="duration_days", event_col="event_observed")
        s_hr   = s_cox.hazard_ratios_["is_ephemeral"]
        s_ci   = s_cox.confidence_intervals_.loc["is_ephemeral"]
        s_pval = s_cox.summary["p"]["is_ephemeral"]
        s_lo   = math.exp(s_ci["95% lower-bound"])
        s_hi   = math.exp(s_ci["95% upper-bound"])
        n_e = int(s_bkt[s_bkt["bucket"] == "ephemeral"]["event_observed"].sum())
        n_s = int(s_bkt[s_bkt["bucket"] == "stable"]["event_observed"].sum())
        pstr = "p < 0.0001" if s_pval < 0.0001 else f"{s_pval:.4f}"
        print(f"{f'{threshold} day(s)':15s}  {f'{n_e}/{n_s}':>14}  {s_hr:>8.3f}  [{s_lo:.3f}, {s_hi:.3f}]{' ':>8}  {pstr:>10}")


if __name__ == "__main__":
    main()
