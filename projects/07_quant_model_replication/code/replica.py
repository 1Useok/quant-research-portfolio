"""시점별 입력, 성숙 라벨 학습, 횡단면 순위. 공표표는 이 모듈에 들어오지 않는다."""

import csv
import math
from bisect import bisect_left, bisect_right
from datetime import date, timedelta
from operator import itemgetter
from statistics import fmean
from typing import NamedTuple

FACTORS = ("value", "quality", "trend")
K = 3


class Macro(NamedTuple):
    observed_on: date
    available_on: date
    cycle: float


class Label(NamedTuple):
    signal: date
    macro: Macro | None
    entry: date
    end: date
    factor: str
    leaders: tuple[str, ...]
    universe_n: int
    excess_pp: float | None


class Estimate(NamedTuple):
    train_n: int
    last_label: Label
    forecast_pp: float


def read_rows(path, *keys):
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    key = itemgetter(*keys)
    rows.sort(key=key)
    if any(key(a) == key(b) for a, b in zip(rows, rows[1:])):
        raise ValueError(f"{path.name} 중복 키 {keys}")
    return rows


def number(cell):
    if not cell.strip():
        return None
    value = float(cell)
    if not math.isfinite(value):
        raise ValueError("유한 수 또는 빈칸이 필요합니다")
    return value


def observation_dates(row):
    obs = date.fromisoformat(row["observed_on"])
    release = date.fromisoformat(row["available_on"])
    if release < obs:
        raise ValueError("가용일이 관측일보다 빠릅니다")
    return obs, release


def load_market(folder):
    books, macro, closes = {}, [], {}
    for row in read_rows(folder / "factors.csv", "observed_on", "symbol"):
        obs, release = observation_dates(row)
        if obs.weekday() != 3:
            raise ValueError("이 주간 표본의 종목 관측일은 목요일입니다")
        signal = obs + timedelta(days=1)
        book = books.setdefault(signal, {})
        values = {f: number(row[f]) for f in FACTORS}
        if release <= signal and sum(v is not None for v in values.values()) >= 2:
            book[row["symbol"]] = values
    for row in read_rows(folder / "macro.csv", "observed_on", "available_on"):
        obs, release = observation_dates(row)
        value = number(row["cycle"])
        if value is not None:
            macro.append(Macro(obs, release, value))
    for row in read_rows(folder / "closes.csv", "session", "symbol"):
        price = number(row["close"])
        if price is not None:
            if price <= 0:
                raise ValueError("종가는 양수여야 합니다")
            closes[date.fromisoformat(row["session"]), row["symbol"]] = price
    return books, macro, closes


def macro_at(events, signal):
    known = (m for m in events if m.available_on <= signal)
    return max(known, key=lambda m: (m.observed_on, m.available_on), default=None)


def holding_dates(signal):
    entry = signal + timedelta(days=3)
    return entry, entry + timedelta(weeks=1)


def basket_return(closes, symbols, entry, end):
    changes = []
    for symbol in symbols:
        buy, sell = closes.get((entry, symbol)), closes.get((end, symbol))
        if buy is None or sell is None:
            return None
        changes.append(100 * (sell / buy - 1))
    return fmean(changes) if changes else None


def make_labels(books, macro, closes):
    labels = []
    for day, book in sorted(books.items()):
        event = macro_at(macro, day)
        entry, end = holding_dates(day)
        for f in FACTORS:
            valid = [s for s in book if book[s][f] is not None]
            valid.sort(key=lambda s: (-book[s][f], s))
            leaders = tuple(valid[:2])
            base = basket_return(closes, valid, entry, end)
            excess = None
            if base is not None and len(valid) > len(leaders):
                excess = basket_return(closes, leaders, entry, end) - base
            labels.append(Label(day, event, entry, end, f, leaders, len(valid), excess))
    return labels


def fit_asof(labels, signal, event):
    if event is None:
        return None
    fits = {}
    for f in FACTORS:
        history = [r for r in labels if r.factor == f and r.end < signal
                   and r.excess_pp is not None and r.macro is not None]
        if len(history) < 4:
            return None
        x_mean = fmean(r.macro.cycle for r in history)
        y_mean = fmean(r.excess_pp for r in history)
        variance = sum((r.macro.cycle - x_mean) ** 2 for r in history)
        covariance = sum((r.macro.cycle - x_mean) * (r.excess_pp - y_mean) for r in history)
        slope = covariance / (variance + 1.0)
        forecast = y_mean + slope * (event.cycle - x_mean)
        fits[f] = Estimate(len(history), max(history, key=lambda r: r.end), forecast)
    highest = max(fit.forecast_pp for fit in fits.values())
    masses = {f: math.exp(fits[f].forecast_pp - highest) for f in FACTORS}
    total = sum(masses.values())
    return fits, {f: masses[f] / total for f in FACTORS}


def percentiles(book):
    ranks = {s: {} for s in book}
    for f in FACTORS:
        levels = sorted(v[f] for v in book.values() if v[f] is not None)
        for symbol, values in book.items():
            value = values[f]
            rank = 0.5
            if value is not None and len(levels) > 1:
                first = bisect_left(levels, value)
                last = bisect_right(levels, value) - 1
                rank = (first + last) / (2 * (len(levels) - 1))
            ranks[symbol][f] = rank
    return ranks


def ranking(ranks, weights):
    scores = []
    for symbol, values in ranks.items():
        score = 100 * math.fsum(weights[f] * values[f] for f in FACTORS)
        scores.append((symbol, round(score, 10)))
    return sorted(scores, key=lambda item: (-item[1], item[0]))
