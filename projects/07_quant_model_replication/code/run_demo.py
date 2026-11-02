"""합성 DDQM2 축소 시연을 실행하고 날짜별 검산표를 쓴다."""

import argparse
import csv
import math
from datetime import date
from pathlib import Path

from replica import (FACTORS, K, basket_return, fit_asof, holding_dates, load_market,
                     macro_at, make_labels, percentiles, ranking, read_rows)

ROOT = Path(__file__).resolve().parent
PAIRS = (("reference", "replay"), ("reference", "predicted"), ("replay", "predicted"))
MACRO_FIELDS = ("macro_observed_on", "macro_available_on", "cycle")


def write_table(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        for row in rows:
            writer.writerow(round(v, 10) if isinstance(v, float) else v for v in row)


def reference_inputs(row):
    weights = {f: float(row[f + "_pct"]) / 100 for f in FACTORS}
    picks = [row[f"pick_{i}"] for i in range(1, K + 1)]
    if min(weights.values()) < 0 or not math.isclose(sum(weights.values()), 1):
        raise ValueError("공표 비중은 음수 없이 합이 100%여야 합니다")
    if "" in picks or len(set(picks)) != K:
        raise ValueError("공표 종목 수 또는 중복을 확인하세요")
    return weights, picks


def compare(day, orders, left, right):
    a, b = orders[left], orders[right]
    common = sorted(set(a) & set(b))
    return dict(signal_date=day, pair=f"{left}/{right}", left_order=" ".join(a),
                right_order=" ".join(b), common_symbols=" ".join(common),
                overlap_n=len(common), same_rank_n=sum(x == y for x, y in zip(a, b)))


def run(data_dir, out):
    books, macro, closes = load_market(data_dir)
    labels = make_labels(books, macro, closes)
    predictions = {}
    for day in sorted(books):
        event = macro_at(macro, day)
        result = fit_asof(labels, day, event)
        if result is not None:
            predictions[day] = (event, *result)

    # 공표표는 모든 주의 예측이 끝난 뒤 평가 구간에만 결합한다.
    references = read_rows(data_dir / "reference.csv", "signal_date")
    if not references:
        raise ValueError("공표 대조일이 없습니다")
    weights, rankings, checks, returns = [], [], [], []
    for row in references:
        day = date.fromisoformat(row["signal_date"])
        if day not in predictions or len(books[day]) < K:
            raise ValueError(f"{day} 학습 표본 또는 선정 가능 종목이 부족합니다")
        event, fits, predicted = predictions[day]
        published, picks = reference_inputs(row)
        ranks = percentiles(books[day])
        orders = {"reference": picks}
        entry, end = holding_dates(day)
        for f in FACTORS:
            fit = fits[f]
            weights.append((day, *event, f, fit.train_n, fit.last_label.signal,
                            fit.last_label.end, fit.forecast_pp, predicted[f], published[f]))
        for mode, allocation in (("replay", published), ("predicted", predicted)):
            ranked = ranking(ranks, allocation)
            held = [s for s, _ in ranked[:K]]
            orders[mode] = held
            for pos, (symbol, score) in enumerate(ranked, 1):
                rankings.append((day, mode, pos, symbol, *(ranks[symbol][f] for f in FACTORS),
                                 score, 1 / K if pos <= K else 0))
            returns.append((day, mode, entry, end, " ".join(held),
                            basket_return(closes, held, entry, end)))
        checks.extend(compare(day, orders, a, b) for a, b in PAIRS)

    peaks = {}
    for row in checks:
        pair = row["pair"]
        peaks[pair] = max(peaks.get(pair, 0), row["overlap_n"])
    for row in checks:
        row["is_peak"] = int(row["overlap_n"] == peaks[row["pair"]])

    out.mkdir(parents=True, exist_ok=True)
    write_table(out / "labels.csv",
                ("signal_date", *MACRO_FIELDS, "factor", "entry_date", "label_end",
                 "leaders", "universe_n", "excess_pp"),
                ((r.signal, *(r.macro or (None, None, None)), r.factor, r.entry, r.end,
                  " ".join(r.leaders), r.universe_n, r.excess_pp) for r in labels))
    write_table(out / "weights.csv",
                ("signal_date", *MACRO_FIELDS, "factor", "train_n", "last_train_signal",
                 "last_label_end", "forecast_excess_pp", "predicted_weight", "published_weight"), weights)
    write_table(out / "rankings.csv",
                ("signal_date", "mode", "rank", "symbol", *[f + "_rank" for f in FACTORS],
                 "score", "holding_weight"), rankings)
    write_table(out / "overlap.csv", checks[0].keys(), (r.values() for r in checks))
    write_table(out / "returns.csv",
                ("signal_date", "mode", "entry_date", "exit_date", "holdings", "gross_return_pct"), returns)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs", help="결과 CSV 디렉터리")
    args = parser.parse_args()
    checks = run(ROOT / "data", args.out)
    for left, right in PAIRS:
        pair = f"{left}/{right}"
        rows = [r for r in checks if r["pair"] == pair]
        hits = sum(r["overlap_n"] for r in rows)
        peaks = [r for r in rows if r["is_peak"]]
        dates = ", ".join(str(r["signal_date"]) for r in peaks)
        print(f"{pair}  {hits}/{K * len(rows)}  peak {peaks[0]['overlap_n']}/{K}  {dates}")


if __name__ == "__main__":
    main()
