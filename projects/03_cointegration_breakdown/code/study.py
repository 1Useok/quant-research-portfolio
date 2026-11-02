"""합성 시세의 월말 선정, 종가 경보, 양다리 시가 체결."""

from itertools import combinations

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import adfuller, coint


FORMATION = 120
WINDOWS = (("validation", "2030-07"), ("evaluation", "2030-08"))
SPECS = ("primary_bh", "exploratory_raw")
HOLD = 10
FEE_BPS = 10
ALARM = 5.0

PERIOD = ["split", "formation_start", "formation_end"]
SCREEN = ["symbol", "valid_closes", "adf_level_p", "adf_diff_p", "eligible"]
PAIR = [
    "a", "b", "eg_stat", "eg_p", "bh_q", "alpha", "beta", "spread_mean", "spread_sd",
    "ar_const", "ar_phi", "innovation_sd", "half_life", "stable", *SPECS,
]
EVENT = [
    "split", "spec", "formation_end", "a", "b", "beta", "signal_date", "direction",
    "z", "change_5", "change_20", "cusum", "status", "entry_due", "exit_due",
    "entry_date", "entry_a", "entry_b", "qty_a", "qty_b", "fee_entry_a", "fee_entry_b",
    "exit_date", "exit_delay_sessions", "exit_a", "exit_b", "fee_exit_a", "fee_exit_b",
    "pnl_a", "pnl_b", "gross_return", "net_return",
]


def read_prices(path):
    rows = pd.read_csv(path, encoding="utf-8", dtype={"date": str, "symbol": str},
                       keep_default_na=False, na_values=[""])
    rows["date"] = pd.to_datetime(rows.date, format="%Y-%m-%d")
    if rows[["date", "symbol"]].isna().any().any():
        raise ValueError("날짜와 종목은 필수입니다.")
    if rows.duplicated(["date", "symbol"]).any():
        raise ValueError("중복된 날짜·종목입니다.")
    panels = []
    for field in ("open", "close"):
        rows[field] = pd.to_numeric(rows[field], errors="raise")
        valid = rows[field].dropna()
        if not (np.isfinite(valid) & (valid > 0)).all():
            raise ValueError(f"{field}에는 양수 가격 또는 빈칸만 허용합니다.")
        panel = rows.pivot(index="date", columns="symbol", values=field)
        panels.append(panel.sort_index().sort_index(axis=1))
    return tuple(panels)


def line_fit(x, y):
    design = np.column_stack((np.ones(len(x)), x))
    return np.linalg.lstsq(design, y, rcond=None)[0]  # 절편, 기울기


def select_pairs(log_history):
    screens, eligible = [], []
    for symbol, series in log_history.items():
        level = series.to_numpy()
        diff = np.diff(level)
        n = int(series.count())
        level_p = diff_p = np.nan
        if n == len(level) and np.ptp(level) > 0 and np.ptp(diff) > 0:
            level_p = adfuller(level, regression="c", maxlag=2, autolag="AIC")[1]
            diff_p = adfuller(diff, regression="c", maxlag=2, autolag="AIC")[1]
        passed = level_p >= 0.05 and diff_p < 0.05
        screens.append(dict(symbol=symbol, valid_closes=n, adf_level_p=level_p,
                            adf_diff_p=diff_p, eligible=passed))
        if passed:
            eligible.append(symbol)

    fits = []
    for a, b in combinations(sorted(eligible), 2):
        y, x = log_history[a].to_numpy(), log_history[b].to_numpy()
        stat, p, _ = coint(y, x, trend="c", maxlag=2, autolag="AIC")
        alpha, beta = line_fit(x, y)
        residual = y - (alpha + beta * x)
        ar_const, phi = line_fit(residual[:-1], residual[1:])
        innovations = residual[1:] - (ar_const + phi * residual[:-1])
        spread_sd, innovation_sd = residual.std(ddof=1), innovations.std(ddof=2)
        half_life = np.log(0.5) / np.log(phi) if 0 < phi < 1 else np.nan
        stable = (0.25 <= beta <= 4 and 2 <= half_life <= 60
                  and min(spread_sd, innovation_sd) > 1e-9)
        fits.append(dict(a=a, b=b, eg_stat=stat, eg_p=p, alpha=alpha, beta=beta,
                         spread_mean=residual.mean(), spread_sd=spread_sd, ar_const=ar_const,
                         ar_phi=phi, innovation_sd=innovation_sd, half_life=half_life, stable=stable))
    if fits:
        qvalues = multipletests([row["eg_p"] for row in fits], method="fdr_bh")[1]
        for row, q in zip(fits, qvalues):
            row.update(bh_q=q, primary_bh=row["stable"] and q <= 0.05,
                       exploratory_raw=row["stable"] and row["eg_p"] < 0.05)
    return screens, fits


def first_break(logs, fit):
    residual = (logs[fit["a"]] - (fit["alpha"] + fit["beta"] * logs[fit["b"]])).to_numpy()
    up = down = 0.0
    for t in range(FORMATION, len(residual)):
        current = residual[t]
        if not np.isfinite(current):
            break  # 일수와 누적경보를 결측 너머로 이어 붙이지 않는다.
        prediction = fit["ar_const"] + fit["ar_phi"] * residual[t - 1]
        shock = (current - prediction) / fit["innovation_sd"]
        up = max(0.0, up + shock - 0.5)
        down = max(0.0, down - shock - 0.5)
        z = (current - fit["spread_mean"]) / fit["spread_sd"]
        direction = 1 if z > 0 else -1
        score = up if direction > 0 else down
        m5, m20 = current - residual[t - 5], current - residual[t - 20]
        if abs(z) >= 2 and direction * m5 > 0 and direction * m20 > 0 and score > ALARM:
            return dict(signal_date=logs.index[t], direction=direction, z=z,
                        change_5=m5, change_20=m20, cusum=score)
    return None


def execute(opens, fit, signal):
    quotes = opens[[fit["a"], fit["b"]]]
    entry = quotes.index.get_loc(signal["signal_date"]) + 1
    due = entry + HOLD
    record = {}
    if entry < len(quotes):
        record["entry_due"] = quotes.index[entry]
    if due >= len(quotes):
        return dict(record, status="outside_window")
    record["exit_due"] = quotes.index[due]
    start = quotes.iloc[entry].to_numpy()
    if np.isnan(start).any():
        return dict(record, status="no_entry_open")

    beta = fit["beta"]
    weights = signal["direction"] * np.array([1.0, -beta]) / (1 + beta)
    qty = weights / start  # 진입 총 절대금액 1. 이후 주식 수를 고정한다.
    fee_rate = FEE_BPS / 10_000
    entry_fees = abs(qty) * start * fee_rate
    record.update(entry_date=quotes.index[entry], entry_a=start[0], entry_b=start[1],
                  qty_a=qty[0], qty_b=qty[1], fee_entry_a=entry_fees[0], fee_entry_b=entry_fees[1])
    joint_opens = quotes.iloc[due:].dropna()
    if joint_opens.empty:
        return dict(record, status="unresolved_exit")
    exit_date = joint_opens.index[0]
    end = joint_opens.iloc[0].to_numpy()
    pnl = qty * (end - start)
    exit_fees = abs(qty) * end * fee_rate
    return dict(record, status="closed", exit_date=exit_date,
                exit_delay_sessions=quotes.index.get_loc(exit_date) - due,
                exit_a=end[0], exit_b=end[1], fee_exit_a=exit_fees[0], fee_exit_b=exit_fees[1],
                pnl_a=pnl[0], pnl_b=pnl[1], gross_return=pnl.sum(),
                net_return=pnl.sum() - entry_fees.sum() - exit_fees.sum())


def run_study(opens, closes):
    screens, pairs, events, summary = [], [], [], []
    for split, month in WINDOWS:
        sessions = closes.loc[month].index
        history = closes.loc[closes.index < sessions[0]].tail(FORMATION)
        if len(history) != FORMATION:
            raise ValueError(f"{month} 관찰 전 {FORMATION}거래일이 필요합니다.")
        period = dict(split=split, formation_start=history.index[0], formation_end=history.index[-1])
        screened, fits = select_pairs(np.log(history))
        screens.extend({**period, **row} for row in screened)
        pairs.extend({**period, **row} for row in fits)
        logs = np.log(pd.concat([history, closes.loc[sessions]]))
        month_events = []
        for fit in fits:
            specs = [spec for spec in SPECS if fit[spec]]
            if not specs:
                continue
            signal = first_break(logs, fit)
            if signal is None:
                continue
            result = execute(opens.loc[sessions], fit, signal)
            for spec in specs:
                month_events.append(dict(split=split, spec=spec, formation_end=period["formation_end"],
                                         a=fit["a"], b=fit["b"], beta=fit["beta"], **signal, **result))
        events.extend(month_events)
        for spec in SPECS:
            signals = [row for row in month_events if row["spec"] == spec]
            closed = [row for row in signals if row["status"] == "closed"]
            summary.append(dict(
                **period, spec=spec, window_start=sessions[0], window_end=sessions[-1],
                sessions=len(sessions), eg_tests=len(fits), selected_pairs=sum(f[spec] for f in fits),
                signals=len(signals), closed_trades=len(closed),
                outside_window=sum(r["status"] == "outside_window" for r in signals),
                no_entry_open=sum(r["status"] == "no_entry_open" for r in signals),
                unresolved_exit=sum(r["status"] == "unresolved_exit" for r in signals),
                fee_bps=FEE_BPS,
                mean_gross_return=np.mean([r["gross_return"] for r in closed]) if closed else None,
                mean_net_return=np.mean([r["net_return"] for r in closed]) if closed else None,
            ))
    return {
        "screen": pd.DataFrame(screens, columns=PERIOD + SCREEN),
        "pairs": pd.DataFrame(pairs, columns=PERIOD + PAIR),
        "events": pd.DataFrame(events, columns=EVENT).sort_values(["signal_date", "a", "b", "spec"]),
        "summary": pd.DataFrame(summary),
    }
