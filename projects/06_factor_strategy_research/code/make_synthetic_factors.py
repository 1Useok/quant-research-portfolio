"""Generate the synthetic factor-return sample used by factor_selection.py.

Everything here is random toy data (fixed seed). It is NOT WorldQuant Brain
output and says nothing about real alpha performance.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

FACTORS = [
    # factor_id, family, turnover, coverage, drift (daily), loading on common shock
    ("F001", "value_quality", 0.041, 0.92, 0.0006, 0.8),
    ("F002", "momentum", 0.087, 0.88, 0.0005, 0.2),
    ("F003", "liquidity", 0.054, 0.81, 0.0004, 0.1),
    ("F004", "seasonality", 0.033, 0.76, 0.0003, 0.0),
    ("F005", "value_quality", 0.046, 0.90, 0.0006, 0.8),  # near-duplicate of F001
    ("F006", "momentum", 0.210, 0.85, 0.0007, 0.2),       # high turnover
    ("F007", "reversal", 0.062, 0.79, 0.0004, -0.3),
    ("F008", "liquidity", 0.058, 0.83, 0.0000, 0.0),      # no edge
]


def business_days(start: date, n: int) -> list[date]:
    days, d = [], start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def main(out_dir: Path) -> None:
    rng = random.Random(42)
    days = business_days(date(2025, 1, 2), 252)
    common = [rng.gauss(0, 0.004) for _ in days]
    own = {f[0]: [rng.gauss(0, 0.004) for _ in days] for f in FACTORS}
    rows = ["date,factor_id,daily_return"]
    for fid, _, _, _, drift, load in FACTORS:
        for i, d in enumerate(days):
            r = drift + load * common[i] + 0.6 * own[fid][i]
            if fid == "F005":  # share most of F001's noise
                r = drift + load * common[i] + 0.6 * own["F001"][i] * 0.9 + 0.1 * own[fid][i]
            rows.append(f"{d.isoformat()},{fid},{r:.6f}")
    (out_dir / "sample_factor_returns.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    meta = ["factor_id,family,turnover,coverage"]
    meta += [f"{fid},{fam},{to},{cov}" for fid, fam, to, cov, _, _ in FACTORS]
    (out_dir / "sample_factor_metadata.csv").write_text("\n".join(meta) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(__file__).resolve().parents[1] / "input_sample")
