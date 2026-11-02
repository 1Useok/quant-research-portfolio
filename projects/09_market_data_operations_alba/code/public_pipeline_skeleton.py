"""Public-safe skeleton for the market data operations pipeline.

This file intentionally does not contain credentials, vendor endpoints, or
production paths. It shows the orchestration shape only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class PipelineConfig:
    trade_date: str
    input_dir: Path
    output_dir: Path


def load_universe(config: PipelineConfig) -> pd.DataFrame:
    return pd.read_csv(config.input_dir / "sample_universe.csv")


def load_minute_bars(config: PipelineConfig) -> pd.DataFrame:
    return pd.read_csv(config.input_dir / "sample_minute_bar.csv")


def validate_minute_bars(bars: pd.DataFrame) -> dict[str, bool]:
    return {
        "nonempty": not bars.empty,
        "volume_nonnegative": bool((bars["volume"] >= 0).all()),
        "ohlc_valid": bool(
            (
                (bars["high"] >= bars[["open", "close", "low"]].max(axis=1))
                & (bars["low"] <= bars[["open", "close", "high"]].min(axis=1))
            ).all()
        ),
    }


def run_quality_report(config: PipelineConfig) -> pd.DataFrame:
    universe = load_universe(config)
    bars = load_minute_bars(config)
    checks = validate_minute_bars(bars)
    rows = [
        {"check_name": "universe_nonempty", "status": not universe.empty},
        *[
            {"check_name": name, "status": status}
            for name, status in checks.items()
        ],
    ]
    return pd.DataFrame(rows)


if __name__ == "__main__":
    cfg = PipelineConfig(
        trade_date="2025-01-08",
        input_dir=Path("../input_sample"),
        output_dir=Path("../output_sample"),
    )
    print(run_quality_report(cfg))

