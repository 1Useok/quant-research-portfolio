"""Cash-funded, equal-budget close entries and next-session VWAP exits."""

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import NamedTuple

from signals import TOP_N

STARTING_CASH = 1_000_000.0


class Quote(NamedTuple):
    close: float | None
    vwap: float | None


NO_QUOTE = Quote(None, None)


def nonnegative_number(value):
    if value == "":
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Expected a finite, nonnegative observation, got {value!r}")
    return number


def market_by_session(rows):
    market = defaultdict(dict)
    for row in rows:
        day = date.fromisoformat(row["session"])
        symbol = row["symbol"]
        if symbol in market[day]:
            raise ValueError(f"Duplicate quote for {day} {symbol}")
        close = nonnegative_number(row["close"])
        amount = nonnegative_number(row["traded_value"])
        volume = nonnegative_number(row["volume"])
        if close == 0:
            raise ValueError(f"Use a blank for an unavailable close on {day} {symbol}")
        if (amount is None) != (volume is None) or (amount == 0) != (volume == 0):
            raise ValueError(f"Inconsistent traded value and volume for {day} {symbol}")
        market[day][symbol] = Quote(close, amount / volume if volume else None)
    if not market:
        raise ValueError("The sample needs at least one market session.")
    return dict(market)


@dataclass
class Position:
    symbol: str
    entry_day: date
    quantity: float
    last_close: float


class Order(NamedTuple):
    roundtrip_bps: float
    session: date
    signal_session: date
    rank: int
    symbol: str
    side: str
    status: str
    quantity: float = 0.0
    price: float | None = None
    fee: float = 0.0


class DailyNAV(NamedTuple):
    roundtrip_bps: float
    session: date
    cash: float
    holdings_value: float
    nav: float
    drawdown: float
    open_slots: int


class Summary(NamedTuple):
    roundtrip_bps: float
    total_return: float
    max_drawdown: float
    total_fees: float
    buy_fills: int
    sell_fills: int
    final_open_slots: int


def simulate(market, signals, roundtrip_bps, top_n=TOP_N):
    if not 0 <= roundtrip_bps < 20_000 or top_n < 1:
        raise ValueError("Costs must be in [0, 20000) bps and top_n must be positive.")
    rate = roundtrip_bps / 20_000
    schedule = defaultdict(list)
    for signal in signals:
        schedule[signal.session].append(signal)

    cash = peak = STARTING_CASH
    positions = {}
    orders = []
    daily = []
    last_session = max(market)
    for day, quotes in sorted(market.items()):
        # Every carried position is now due. A missing VWAP keeps its rank occupied.
        for rank, position in list(positions.items()):
            vwap = quotes.get(position.symbol, NO_QUOTE).vwap
            order_key = (roundtrip_bps, day, position.entry_day, rank, position.symbol, "sell")
            if vwap is None:
                orders.append(Order(*order_key, "pending_vwap"))
                continue
            proceeds = position.quantity * vwap
            fee = proceeds * rate
            cash += proceeds - fee
            orders.append(Order(*order_key, "filled", position.quantity, vwap, fee))
            del positions[rank]

        # Size all new orders together so an earlier rank cannot consume a later one's budget.
        available = []
        for signal in schedule[day]:
            close = quotes.get(signal.symbol, NO_QUOTE).close
            order_key = (roundtrip_bps, day, day, signal.rank, signal.symbol, "buy")
            if day == last_session:
                orders.append(Order(*order_key, "end_of_sample"))
            elif signal.rank in positions:
                orders.append(Order(*order_key, "occupied_slot"))
            elif close is None:
                orders.append(Order(*order_key, "missing_close"))
            else:
                available.append((signal, close, order_key))
        if available:
            sizing_equity = cash + sum(p.quantity * p.last_close for p in positions.values())
            budget = min(sizing_equity / top_n, cash / len(available)) / (1 + rate)
            for signal, close, order_key in available:
                if budget <= 0:
                    orders.append(Order(*order_key, "no_cash"))
                    continue
                fee = budget * rate
                quantity = budget / close
                positions[signal.rank] = Position(signal.symbol, day, quantity, close)
                cash -= budget + fee
                orders.append(Order(*order_key, "filled", quantity, close, fee))

        if cash < -1e-7:
            raise ArithmeticError(f"Negative cash balance on {day}")
        cash = max(0.0, cash)  # Sub-cent floating-point noise only.
        holdings = 0.0
        for position in positions.values():
            close = quotes.get(position.symbol, NO_QUOTE).close
            if close is not None:
                position.last_close = close
            holdings += position.quantity * position.last_close
        nav = cash + holdings
        peak = max(peak, nav)
        daily.append(DailyNAV(roundtrip_bps, day, cash, holdings, nav, nav / peak - 1, len(positions)))

    filled = [o for o in orders if o.status == "filled"]
    summary = Summary(roundtrip_bps, daily[-1].nav / STARTING_CASH - 1,
                      min(d.drawdown for d in daily), sum(o.fee for o in filled),
                      sum(o.side == "buy" for o in filled), sum(o.side == "sell" for o in filled),
                      len(positions))
    return orders, daily, summary
