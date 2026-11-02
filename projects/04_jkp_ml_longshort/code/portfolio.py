"""Convert scores to next-session paper targets and mark completed holding periods."""
import math

import numpy as np
import pandas as pd

SIDE_COUNT = 2
TRADE_COST = 0.0010  # One-way fee per unit of traded notional.
BORROW_APR = 0.02


def form_targets(predictions):
    books = []
    for day, group in predictions.groupby("effective_date", sort=True):
        eligible = group.sort_values(["market_cap", "security_id"], ascending=[False, True])
        eligible = eligible.head(math.ceil(len(eligible) * 0.6))
        if len(eligible) < 2 * SIDE_COUNT:
            raise ValueError(f"Too few eligible securities on {day.date()}")
        ranks = eligible.sort_values(["probability", "market_cap", "security_id"], ascending=[False, False, True])
        longs = ranks.head(SIDE_COUNT).assign(side="long", weight=0.5 / SIDE_COUNT)
        shorts = ranks.tail(SIDE_COUNT).assign(side="short", weight=-0.5 / SIDE_COUNT)
        books.append(pd.concat([longs, shorts]))
    return pd.concat(books, ignore_index=True)


def realized_returns(targets, market, calendar, trade_cost=TRADE_COST, borrow_apr=BORROW_APR):
    if trade_cost < 0 or borrow_apr < 0:
        raise ValueError("Costs must be nonnegative.")
    sessions = calendar.set_index("signal_eom").first_session
    opening = market.pivot(index="signal_eom", columns="security_id", values="first_open")
    opening.index = sessions.reindex(opening.index).to_numpy()
    following = dict(zip(calendar.first_session, calendar.effective_date))
    nav = peak = 1.0
    carried = pd.Series(dtype=float)
    periods = []
    for entry, basket in targets.groupby("effective_date", sort=True):
        exit_day = following.get(entry)
        if entry > opening.index.max() or (exit_day is not None and exit_day > opening.index.max()):
            break  # The latest targets are publishable before their holding returns exist.
        if entry not in opening.index or exit_day not in opening.index:
            raise ValueError(f"Missing historical price session for {entry.date()}")
        weight = basket.set_index("security_id").weight
        prices = opening.loc[[entry, exit_day], weight.index]
        if not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any():
            raise ValueError(f"Missing or invalid opening price for a selected name at {entry.date()}")
        asset_return = prices.iloc[1] / prices.iloc[0] - 1
        dollars = weight * nav
        traded = dollars.subtract(carried, fill_value=0).abs().sum()
        turnover = traded / nav
        fees = turnover * trade_cost
        borrow = -weight[weight < 0].sum() * borrow_apr * (exit_day - entry).days / 365
        gross = float(weight @ asset_return)
        net = gross - fees - borrow
        nav *= 1 + net
        if nav <= 0:
            raise ValueError("The simulated book exhausted its capital.")
        peak = max(peak, nav)
        periods.append({"entry": entry, "exit": exit_day, "gross_return": gross, "turnover": turnover,
                        "trade_cost": fees, "borrow_cost": borrow, "net_return": net,
                        "net_nav": nav, "drawdown": nav / peak - 1})
        carried = dollars * (1 + asset_return)
    return pd.DataFrame(periods, columns=["entry", "exit", "gross_return", "turnover", "trade_cost",
                                          "borrow_cost", "net_return", "net_nav", "drawdown"])
