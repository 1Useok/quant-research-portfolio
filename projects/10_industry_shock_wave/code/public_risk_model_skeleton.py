"""Public-safe skeleton for industry shock-wave risk scoring."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_io_matrix(input_dir: Path) -> pd.DataFrame:
    return pd.read_csv(input_dir / "sample_io_matrix.csv")


def load_firm_panel(input_dir: Path) -> pd.DataFrame:
    return pd.read_csv(input_dir / "sample_firm_panel.csv")


def compute_industry_exposure(io_matrix: pd.DataFrame) -> pd.DataFrame:
    return (
        io_matrix.groupby("buyer_industry", as_index=False)["input_share"]
        .sum()
        .rename(columns={"buyer_industry": "industry", "input_share": "direct_input_exposure"})
    )


def score_firm_risk(firms: pd.DataFrame, exposure: pd.DataFrame) -> pd.DataFrame:
    scored = firms.merge(exposure, on="industry", how="left")
    scored["direct_input_exposure"] = scored["direct_input_exposure"].fillna(0.0)
    scored["risk_score"] = 100 * (
        0.45 * scored["financial_score"]
        + 0.35 * scored["market_signal"]
        + 0.20 * scored["direct_input_exposure"]
    )
    return scored


if __name__ == "__main__":
    base = Path("../input_sample")
    risk = score_firm_risk(load_firm_panel(base), compute_industry_exposure(load_io_matrix(base)))
    print(risk[["firm_id", "industry", "risk_score"]])

