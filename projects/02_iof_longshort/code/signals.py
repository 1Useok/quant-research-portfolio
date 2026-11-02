"""합성 마감 자료로 익일 개장 전에 갱신할 한 슬리브의 목표 종목을 고른다."""

import csv
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Close:
    market: str
    cap: float | None
    flow: float | None


@dataclass
class Auction:
    prices: dict = field(default_factory=dict)
    borrowable: set = field(default_factory=set)


def rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        yield from csv.DictReader(stream)


def number(text):
    if not text.strip():
        return None
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("유한한 숫자 또는 빈 칸이 필요합니다.")
    return value


def read_inputs(folder):
    means = {}
    for row in rows(folder / "cap_months.csv"):
        month = date.fromisoformat(row["month"] + "-01").strftime("%Y-%m")
        key = month, row["symbol"]
        if key in means:
            raise ValueError(f"월별 시총 중복 {key}")
        total, days = number(row["cap_sum"]), int(row["observations"])
        means[key] = total / days if total is not None and total > 0 and days > 0 else None

    closes, auctions = defaultdict(dict), defaultdict(Auction)
    for row in rows(folder / "sessions.csv"):
        day, symbol = date.fromisoformat(row["date"]), row["symbol"]
        if symbol in closes[day]:
            raise ValueError(f"거래일·종목 중복 {day} {symbol}")
        flows = [number(row[key]) for key in ("insurance", "trust", "pension")]
        flow = sum(flows) if None not in flows else None
        closes[day][symbol] = Close(row["market"], number(row["cap"]), flow)

        auction = auctions[day]
        price = number(row["open"])
        if price is not None and price > 0:
            auction.prices[symbol] = price
        if row["borrow_ok"] not in ("", "0", "1"):
            raise ValueError(f"대차 플래그 오류 {day} {symbol}")
        if row["borrow_ok"] == "1":
            auction.borrowable.add(symbol)
    return means, closes, auctions


def past_month(day, lag):
    year, month = divmod(day.year * 12 + day.month - 1 - lag, 12)
    return f"{year:04d}-{month + 1:02d}"


def buffered(ranking, incumbent, forbidden):
    if incumbent in ranking[:2] and incumbent not in forbidden:
        return incumbent
    return next((s for s in ranking if s not in forbidden), None)


def select(day, closes, means, held):
    month_a, month_b = past_month(day, 1), past_month(day, 13)
    eligible = [s for s, c in closes.items()
                if c.market in ("KSE", "KOSDAQ") and c.cap is not None and c.cap > 0]
    eligible.sort(key=lambda s: (-closes[s].cap, s))
    cap_ranks = {s: i for i, s in enumerate(eligible, 1)}
    cutoff = (3 * len(eligible) + 9) // 10  # 상위 30%, 올림
    audit, scores, longs = {}, {}, []
    for symbol, close in sorted(closes.items()):
        a, b = means.get((month_a, symbol)), means.get((month_b, symbol))
        cap_rank = cap_ranks.get(symbol)
        in_universe = cap_rank is not None and cap_rank <= cutoff
        if in_universe and a is not None and b is not None and close.flow is not None:
            scores[symbol] = close.flow / b
            if close.flow < 0 and a > b:
                longs.append(symbol)
        audit[symbol] = dict(symbol=symbol, cap_rank=cap_rank, in_universe=int(in_universe),
                             month_a=month_a, mean_a=a, month_b=month_b, mean_b=b,
                             flow=close.flow, iof=scores.get(symbol), long_rank=None,
                             short_rank=None, target=None)

    longs.sort(key=lambda s: (scores[s], s))
    shorts = sorted(scores, key=lambda s: (-scores[s], s))
    long = buffered(longs, held["long"], {held["short"]})
    short = buffered(shorts, held["short"], {held["long"], long})
    targets = {"long": long, "short": short}
    for side, ranking in (("long", longs), ("short", shorts)):
        for rank, symbol in enumerate(ranking, 1):
            audit[symbol][side + "_rank"] = rank
        if targets[side] is not None:
            audit[targets[side]]["target"] = side
    return targets, list(audit.values())
