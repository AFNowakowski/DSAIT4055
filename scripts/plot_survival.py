"""Generate all four paper figures for the survival analysis.

Output: data/processed/comment_nlp/figures/fig{1-4}.pdf

Usage:
    py scripts/plot_survival.py --parquet data/shared/comment_nlp/posts_type1.parquet
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, KaplanMeierFitter

from parquet_survival import load_and_prepare

COL_W = 3.7
EPHEMERAL_COLOR = "#C1121F"
STABLE_COLOR    = "#2B6CB0"
COLORS = {"ephemeral": EPHEMERAL_COLOR, "stable": STABLE_COLOR}
SENS_COLOR = "#2D6A4F"

plt.rcParams.update({
    "font.family":          "serif",
    "font.size":            8,
    "axes.labelsize":       8.5,
    "xtick.labelsize":      7.5,
    "ytick.labelsize":      7.5,
    "legend.fontsize":      7.5,
    "figure.dpi":           180,
    "axes.facecolor":       "white",
    "figure.facecolor":     "white",
    "axes.edgecolor":       "#CCCCCC",
    "axes.linewidth":       0.8,
    "axes.spines.top":      False,
    "axes.spines.right":    False,
    "axes.grid":            True,
    "grid.color":           "#ECECEC",
    "grid.linewidth":       0.6,
    "xtick.color":          "#444444",
    "ytick.color":          "#444444",
    "axes.labelcolor":      "#222222",
    "text.color":           "#222222",
    "legend.frameon":       False,
    "legend.handlelength":  1.4,
})


def save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=180)
    plt.close(fig)
    print(f"Saved: {path}")


# ── Figure 1: Kaplan-Meier survival curves ───────────────────────────────────
def fig1_km(ephemeral: pd.DataFrame, stable: pd.DataFrame, out: Path) -> None:
    kmf_e = KaplanMeierFitter(label="Ephemeral").fit(
        ephemeral["duration_days"], ephemeral["event_observed"]
    )
    kmf_s = KaplanMeierFitter(label="Stable").fit(
        stable["duration_days"], stable["event_observed"]
    )

    fig, ax = plt.subplots(figsize=(COL_W, 2.7))
    kmf_e.plot_survival_function(ax=ax, color=EPHEMERAL_COLOR, ci_show=True,
                                  linewidth=2.0, ci_alpha=0.12)
    kmf_s.plot_survival_function(ax=ax, color=STABLE_COLOR, ci_show=True,
                                  linewidth=2.0, ci_alpha=0.12)

    ax.set_xlabel("Years since first acceptance")
    ax.set_ylabel("Survival probability S(t)")
    ax.set_ylim(0.993, 1.0005)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/365:.0f}"))
    ax.legend(loc="lower left")
    fig.tight_layout()
    save(fig, out)


# ── Figure 2: Cumulative incidence curves ────────────────────────────────────
def fig2_cumulative_incidence(ephemeral: pd.DataFrame, stable: pd.DataFrame, out: Path) -> None:
    kmf_e = KaplanMeierFitter(label="Ephemeral").fit(
        ephemeral["duration_days"], ephemeral["event_observed"]
    )
    kmf_s = KaplanMeierFitter(label="Stable").fit(
        stable["duration_days"], stable["event_observed"]
    )

    fig, ax = plt.subplots(figsize=(COL_W, 2.7))

    for kmf, bucket in [(kmf_e, "ephemeral"), (kmf_s, "stable")]:
        sf       = kmf.survival_function_
        ci_lower = kmf.confidence_interval_.iloc[:, 0]
        ci_upper = kmf.confidence_interval_.iloc[:, 1]
        t    = sf.index
        ci   = 1 - sf.iloc[:, 0]
        ci_lo = 1 - ci_upper
        ci_hi = 1 - ci_lower
        ax.plot(t / 365, ci * 100, color=COLORS[bucket],
                label=bucket.capitalize(), linewidth=2.0)
        ax.fill_between(t / 365, ci_lo * 100, ci_hi * 100,
                        alpha=0.12, color=COLORS[bucket])

    for days in [365, 730, 1825]:
        ax.axvline(days / 365, color="#AAAAAA", linestyle=":", linewidth=0.8)

    ax.set_xlabel("Years since first acceptance")
    ax.set_ylabel("Cumulative incidence 1−S(t) (%)")
    ax.legend(loc="upper left")
    fig.tight_layout()
    save(fig, out)


# ── Figure 3: Bar chart at fixed horizons ────────────────────────────────────
def fig3_horizon_bars(ephemeral: pd.DataFrame, stable: pd.DataFrame, out: Path) -> None:
    kmf_e = KaplanMeierFitter().fit(ephemeral["duration_days"], ephemeral["event_observed"])
    kmf_s = KaplanMeierFitter().fit(stable["duration_days"],    stable["event_observed"])

    horizons = {"6 months": 182, "1 year": 365, "2 years": 730, "5 years": 1825}
    labels = list(horizons.keys())
    ci_e = [(1 - float(kmf_e.predict(t))) * 100 for t in horizons.values()]
    ci_s = [(1 - float(kmf_s.predict(t))) * 100 for t in horizons.values()]

    x = np.arange(len(labels))
    w = 0.36

    fig, ax = plt.subplots(figsize=(COL_W, 2.7))
    bars_e = ax.bar(x - w / 2, ci_e, w, label="Ephemeral",
                    color=EPHEMERAL_COLOR, alpha=0.88, edgecolor="white", linewidth=0.5)
    bars_s = ax.bar(x + w / 2, ci_s, w, label="Stable",
                    color=STABLE_COLOR,    alpha=0.88, edgecolor="white", linewidth=0.5)

    for bar, val in zip(bars_e, ci_e):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.007,
                f"{val:.2f}%", ha="center", va="bottom",
                fontsize=5.8, color=EPHEMERAL_COLOR, fontweight="bold")
    for bar, val in zip(bars_s, ci_s):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.007,
                f"{val:.2f}%", ha="center", va="bottom",
                fontsize=5.8, color=STABLE_COLOR, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Cumulative incidence (%)")
    ax.legend()
    fig.tight_layout()
    save(fig, out)


# ── Figure 4: Sensitivity HR plot ─────────────────────────────────────────────
def fig4_sensitivity(parquet_path: Path, observation_end: pd.Timestamp, out: Path) -> None:
    thresholds = [1, 7, 30]
    hrs, lo_cis, hi_cis = [], [], []

    for threshold in thresholds:
        df = load_and_prepare(parquet_path, observation_end, min_lifespan_days=threshold)
        bkt = df[df["bucket"].notna()].copy()
        bkt["is_ephemeral"] = (bkt["bucket"] == "ephemeral").astype(int)
        cox = CoxPHFitter()
        cox.fit(bkt[["duration_days", "event_observed", "is_ephemeral"]],
                duration_col="duration_days", event_col="event_observed")
        hr = cox.hazard_ratios_["is_ephemeral"]
        ci = cox.confidence_intervals_.loc["is_ephemeral"]
        hrs.append(hr)
        lo_cis.append(math.exp(ci["95% lower-bound"]))
        hi_cis.append(math.exp(ci["95% upper-bound"]))

    fig, ax = plt.subplots(figsize=(COL_W, 2.7))
    x = np.arange(len(thresholds))
    err_lo = [hrs[i] - lo_cis[i] for i in range(len(thresholds))]
    err_hi = [hi_cis[i] - hrs[i] for i in range(len(thresholds))]

    ax.plot(x, hrs, color=SENS_COLOR, linewidth=1.4, zorder=1, linestyle="--", alpha=0.6)
    ax.errorbar(x, hrs, yerr=[err_lo, err_hi], fmt="o", color=SENS_COLOR,
                capsize=5, linewidth=1.5, markersize=7, zorder=2,
                markerfacecolor=SENS_COLOR, markeredgecolor="white", markeredgewidth=1.0)

    ax.set_ylim(2.0, max(hi_cis) + 0.7)
    ax.axhline(1.0, color="#AAAAAA", linestyle="--", linewidth=0.9)
    ax.text(x[-1] + 0.12, 1.02, "HR = 1", va="bottom", fontsize=7, color="#999999")

    for xi, hr in zip(x, hrs):
        ax.text(xi, hr + 0.22, f"{hr:.2f}", ha="center", va="bottom",
                fontsize=7.5, color=SENS_COLOR, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([f"{t} day{'s' if t > 1 else ''}" for t in thresholds])
    ax.set_ylabel("Hazard ratio (ephemeral vs. stable)")
    ax.set_xlabel("Minimum lifespan threshold")
    fig.tight_layout()
    save(fig, out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet", default="data/shared/comment_nlp/posts_type1.parquet")
    parser.add_argument("--observation-end", default="2026-04-21")
    parser.add_argument("--out-dir", default="data/processed/comment_nlp/figures")
    args = parser.parse_args()

    observation_end = pd.Timestamp(args.observation_end, tz="UTC")
    parquet_path    = Path(args.parquet)
    out_dir         = Path(args.out_dir)

    df = load_and_prepare(parquet_path, observation_end)
    bucketed  = df[df["bucket"].notna()]
    ephemeral = bucketed[bucketed["bucket"] == "ephemeral"]
    stable    = bucketed[bucketed["bucket"] == "stable"]

    fig1_km(ephemeral, stable, out_dir / "fig1_km.pdf")
    fig2_cumulative_incidence(ephemeral, stable, out_dir / "fig2_cumulative_incidence.pdf")
    fig3_horizon_bars(ephemeral, stable, out_dir / "fig3_horizon_bars.pdf")
    fig4_sensitivity(parquet_path, observation_end, out_dir / "fig4_sensitivity_hr.pdf")

    print("\nAll figures saved to", out_dir)


if __name__ == "__main__":
    main()
