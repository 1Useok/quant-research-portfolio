"""Correlation filter + greedy combination selector on a synthetic factor pool.

Pipeline (all on toy data from ../input_sample):
  1. per-factor annualised Sharpe (daily returns, sqrt(252), gross, no costs)
  2. screen: minimum Sharpe and maximum turnover
  3. greedy build: repeatedly add the factor that most improves the equal-weight
     combination Sharpe, stopping once no candidate improves it, and rejecting any candidate whose correlation with an already
     selected factor exceeds MAX_CORR.

All Sharpe values are in-sample, gross of costs, on synthetic data. This file
shows the selection logic only; it is not the WorldQuant Brain platform workflow.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ANN = 252
MIN_SHARPE = 0.5
MAX_TURNOVER = 0.15
MAX_CORR = 0.6


def sharpe(r: pd.Series | pd.DataFrame) -> float | pd.Series:
    return r.mean() / r.std(ddof=1) * np.sqrt(ANN)


def load(input_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    long = pd.read_csv(input_dir / "sample_factor_returns.csv", parse_dates=["date"])
    wide = long.pivot(index="date", columns="factor_id", values="daily_return")
    meta = pd.read_csv(input_dir / "sample_factor_metadata.csv").set_index("factor_id")
    return wide, meta


def screen(wide: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    stats = pd.DataFrame({"sharpe_is": sharpe(wide)}).join(meta)
    stats["passed"] = (stats["sharpe_is"] >= MIN_SHARPE) & (stats["turnover"] <= MAX_TURNOVER)
    return stats


def greedy_select(wide: pd.DataFrame, stats: pd.DataFrame, max_corr: float = MAX_CORR) -> pd.DataFrame:
    corr = wide.corr()
    pool = list(stats.index[stats["passed"]])
    chosen: list[str] = []
    rows = []
    prev = -np.inf
    while pool:
        best, best_s = None, -np.inf
        for f in pool:
            if chosen and corr.loc[f, chosen].max() > max_corr:
                continue
            s = sharpe(wide[chosen + [f]].mean(axis=1))
            if s > best_s:
                best, best_s = f, s
        if best is None or best_s <= prev:  # stop when no candidate improves the combo
            break
        prev = best_s
        mc = float(corr.loc[best, chosen].max()) if chosen else float("nan")
        chosen.append(best)
        pool.remove(best)
        rows.append(
            {
                "step": len(chosen),
                "factor_id": best,
                "family": stats.loc[best, "family"],
                "factor_sharpe_is": round(float(stats.loc[best, "sharpe_is"]), 3),
                "max_corr_to_selected": round(mc, 3) if chosen[:-1] else np.nan,
                "combo_n": len(chosen),
                "combo_sharpe_is": round(float(best_s), 3),
                "combo_turnover_avg": round(float(stats.loc[chosen, "turnover"].mean()), 4),
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1]
    wide, meta = load(base / "input_sample")
    stats = screen(wide, meta)
    print("Screen (synthetic, in-sample, gross):")
    print(stats.round(3).to_string())
    print(f"\nFactor pairs with |corr| > {MAX_CORR}:")
    c = wide.corr()
    for i, a in enumerate(c.columns):
        for b in c.columns[i + 1 :]:
            if abs(c.loc[a, b]) > MAX_CORR:
                print(f"  {a}-{b}: {c.loc[a, b]:.2f}")
    result = greedy_select(wide, stats)
    print("\nGreedy combination (synthetic, in-sample Sharpe, gross):")
    print(result.to_string(index=False))
    result.to_csv(base / "output_sample" / "sample_candidate_summary.csv", index=False)
