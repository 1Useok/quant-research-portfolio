"""Regenerate the fictional, month-end source snapshots shipped with the demo."""
from pathlib import Path

import numpy as np
import pandas as pd


def generate(root):
    rng = np.random.default_rng(4117)
    symbols = [f"SIM{i:02d}" for i in range(1, 17)]
    periods = pd.period_range("2016-01", "2025-01", freq="M")
    calendar = []
    market = []
    shares = rng.integers(4_000_000, 30_000_000, len(symbols))
    previous = rng.integers(8_000, 28_000, len(symbols)).astype(float)
    starting_caps = previous * shares
    for month in periods:
        sessions = pd.bdate_range(month.start_time, month.end_time)
        sessions = sessions[~((sessions.month == 1) & (sessions.day == 1))]
        eom = month.end_time.date()
        calendar.append((eom, sessions[0].date(), sessions[-1].date()))
        if month == periods[-1]:
            break  # The final calendar month is a schedule only.
        opening = np.round(previous * np.exp(rng.normal(0, 0.009, len(symbols))), 2)
        common_return = rng.normal(0.003, 0.025)
        closing = np.round(opening * np.exp(common_return + rng.normal(0, 0.060, len(symbols))), 2)
        market.extend((eom, sym, op, cl, issued) for sym, op, cl, issued
                      in zip(symbols, opening, closing, shares))
        previous = closing
    pd.DataFrame(calendar, columns=["signal_eom", "first_session", "last_session"]).to_csv(
        root / "calendar.csv", index=False, lineterminator="\n")
    market = pd.DataFrame(market, columns=["signal_eom", "security_id", "first_open", "last_close", "shares"])
    base = market.iloc[:-len(symbols)]
    base.to_csv(root / "market_base.csv", index=False, lineterminator="\n")
    # One identical key in both batches exercises replay / deduplication.
    pd.concat([base.tail(1), market.tail(len(symbols))]).to_csv(
        root / "market_delta.csv", index=False, lineterminator="\n")
    pd.DataFrame([("base", "market_base.csv", base.signal_eom.max()),
                  ("delta", "market_delta.csv", market.signal_eom.max())],
                 columns=["kind", "file", "published_through"]).to_csv(
                     root / "registry.csv", index=False, lineterminator="\n")

    financial = []
    assets = starting_caps * rng.uniform(0.8, 2.2, len(symbols))
    for quarter in pd.period_range("2013Q1", "2024Q4", freq="Q-DEC"):
        assets *= np.exp(rng.normal(0.008, 0.032, len(symbols)))
        equity = assets * rng.uniform(0.35, 0.82, len(symbols))
        profit = assets * rng.normal(0.009, 0.022, len(symbols))
        for i, symbol in enumerate(symbols):
            values = (round(assets[i]), round(equity[i]))
            financial.append((quarter.end_time.date(), symbol, "Q", *values, round(profit[i])))
            if quarter.quarter == 4:
                financial.append((quarter.end_time.date(), symbol, "A", *values, None))
    records = pd.DataFrame(financial, columns=["fiscal_end", "security_id", "frequency",
                                               "assets", "book_equity", "quarter_income"])
    records["quarter_income"] = records.quarter_income.astype("Int64")
    records.to_csv(root / "financial.csv", index=False, lineterminator="\n")


if __name__ == "__main__":
    generate(Path(__file__).resolve().parent)
