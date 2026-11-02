"""Read registered snapshots and build firm characteristics at their availability dates."""
from pathlib import Path

import numpy as np
import pandas as pd

FEATURES = ["be_me", "at_gr1", "niq_at", "ret_6_1"]
KEY = ["security_id", "effective_date"]


def read_inputs(root, as_of=None):
    registry = pd.read_csv(root / "registry.csv", parse_dates=["published_through"])
    if list(registry.kind).count("base") != 1 or not registry.kind.isin(["base", "delta"]).all():
        raise ValueError("Expected one base snapshot and registered deltas.")
    cutoff = pd.Timestamp(as_of) if as_of else registry.published_through.max()
    if cutoff != cutoff + pd.offsets.MonthEnd(0):
        raise ValueError("Use a calendar month-end as the decision date.")
    calendar = pd.read_csv(root / "calendar.csv", parse_dates=["signal_eom", "first_session", "last_session"])
    calendar = calendar.sort_values("signal_eom").reset_index(drop=True)
    periods = pd.period_range(calendar.signal_eom.min(), calendar.signal_eom.max(), freq="M")
    if not calendar.signal_eom.dt.to_period("M").equals(pd.Series(periods)):
        raise ValueError("The known session calendar must have one row per consecutive month.")
    if not (calendar.first_session.le(calendar.last_session)
            & calendar.last_session.le(calendar.signal_eom)
            & calendar.first_session.dt.to_period("M").eq(calendar.signal_eom.dt.to_period("M"))).all():
        raise ValueError("Invalid session bounds.")
    calendar["effective_date"] = calendar.first_session.shift(-1)
    frames, audit = [], []
    for batch in registry.itertuples(index=False):
        if batch.kind == "delta" and batch.published_through > cutoff:
            continue
        if Path(batch.file).name != batch.file or not batch.file.endswith(".csv"):
            raise ValueError("Registry entries must name a local CSV file.")
        frame = pd.read_csv(root / batch.file, parse_dates=["signal_eom"])
        if frame.signal_eom.max() > batch.published_through:
            raise ValueError(f"Batch contains observations after its coverage date: {batch.file}")
        frame = frame[frame.signal_eom <= cutoff]
        frames.append(frame)
        audit.append({"file": batch.file, "kind": batch.kind, "batch_coverage": batch.published_through,
                      "rows_read_asof": len(frame)})
    raw = pd.concat(frames, ignore_index=True)
    market = raw.drop_duplicates().copy()
    if market.duplicated(["security_id", "signal_eom"]).any():
        raise ValueError("Conflicting market values for the same security and month.")
    if market.empty or market.signal_eom.max() != cutoff or not market.signal_eom.isin(calendar.signal_eom).all():
        raise ValueError("No registered market snapshot or calendar for the requested month-end.")
    observations = market[["last_close", "first_open", "shares"]]
    if observations.le(0).any().any() or np.isinf(observations.to_numpy()).any():
        raise ValueError("Observed prices and shares must be finite and positive.")
    calendar = calendar[calendar.signal_eom.between(market.signal_eom.min(), cutoff)].copy()
    if calendar.effective_date.isna().any():
        raise ValueError("Next month's first session must be in the published calendar.")
    accounts = pd.read_csv(root / "financial.csv", parse_dates=["fiscal_end"])
    accounts = accounts[accounts.fiscal_end <= cutoff].copy()
    if accounts.duplicated(["security_id", "fiscal_end", "frequency"]).any():
        raise ValueError("Conflicting financial statements.")
    return calendar, market, accounts, pd.DataFrame(audit), len(raw) - len(market)


def financial_blocks(accounts):
    blocks = []
    for frequency, lag, prior_months in [("A", 4, 12), ("Q", 3, 3)]:
        reports = accounts[accounts.frequency == frequency].copy()
        # Match the exact prior period. A missing quarter/year cannot shorten the lag.
        prior = reports[["security_id", "fiscal_end", "assets"]].rename(columns={"assets": "prior_assets"})
        prior["fiscal_end"] += pd.offsets.MonthEnd(prior_months)
        reports = reports.merge(prior, on=["security_id", "fiscal_end"], how="left", validate="one_to_one")
        denominator = reports.prior_assets.where(reports.prior_assets > 0)
        if frequency == "A":
            reports["at_gr1"] = reports.assets / denominator - 1
            values, period = ["book_equity", "at_gr1"], "annual_period"
        else:
            reports["niq_at"] = reports.quarter_income / denominator
            values, period = ["niq_at"], "quarter_period"
        reports[period] = reports.fiscal_end
        reports["available_on"] = reports.fiscal_end + pd.offsets.MonthEnd(lag)
        blocks.append(reports[["security_id", "available_on", period, *values]].sort_values("available_on"))
    return blocks


def build_panel(calendar, market, accounts):
    grid = pd.MultiIndex.from_product([sorted(market.security_id.unique()), calendar.signal_eom],
                                      names=["security_id", "signal_eom"])
    panel = market.set_index(["security_id", "signal_eom"]).reindex(grid).reset_index()
    panel = panel.merge(calendar, on="signal_eom", validate="many_to_one")
    closes = panel.groupby("security_id", sort=False).last_close
    panel["monthly_return"] = closes.pct_change(fill_method=None)
    panel["ret_6_1"] = panel.groupby("security_id", sort=False).monthly_return.transform(
        lambda r: (1 + r.shift(1)).rolling(5, min_periods=5).apply(np.prod, raw=True) - 1)
    panel["market_cap"] = panel.last_close * panel.shares
    panel = panel.sort_values("signal_eom")
    for block, vintage in zip(financial_blocks(accounts), ["annual_available", "quarter_available"]):
        panel = pd.merge_asof(panel, block.rename(columns={"available_on": vintage}), by="security_id",
                              left_on="signal_eom", right_on=vintage, direction="backward")
    panel["be_me"] = panel.book_equity.where(panel.book_equity > 0) / panel.market_cap
    panel = panel.sort_values(["security_id", "signal_eom"]).reset_index(drop=True)
    if panel.duplicated(KEY).any() or not (panel.last_session <= panel.signal_eom).all() or not (
            panel.signal_eom < panel.effective_date).all():
        raise ValueError("Panel keys or trading dates are inconsistent.")
    columns = [*KEY, "signal_eom", "last_session", "annual_period", "annual_available", "quarter_period",
               "quarter_available", "market_cap", *FEATURES]
    return panel[columns], panel[["security_id", "effective_date", "signal_eom", "monthly_return"]]
