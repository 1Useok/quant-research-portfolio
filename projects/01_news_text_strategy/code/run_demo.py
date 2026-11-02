"""Run the fictional news portfolio example with the Python standard library."""

import argparse
import csv
from pathlib import Path

from backtest import DailyNAV, Order, Summary, market_by_session, simulate
from signals import ArticleDecision, Signal, build_signals, train_baseline

ROOT = Path(__file__).resolve().parent


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_table(path, record_type, records):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(record_type._fields)
        writer.writerows(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data", help="Input CSV directory")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs", help="Output CSV directory")
    parser.add_argument("--cost-bps", nargs="+", type=float, default=[0, 20, 30],
                        help="All-in round-trip cost scenarios in basis points")
    args = parser.parse_args()
    market = market_by_session(read_rows(args.data / "market.csv"))
    model = train_baseline(read_rows(args.data / "training.csv"), min(market))
    decisions, picks = build_signals(read_rows(args.data / "news.csv"),
                                    read_rows(args.data / "companies.csv"), set(market), model)
    orders, nav, summaries = [], [], []
    for cost in dict.fromkeys(args.cost_bps):
        events, days, summary = simulate(market, picks, cost)
        orders.extend(events)
        nav.extend(days)
        summaries.append(summary)

    args.out.mkdir(parents=True, exist_ok=True)
    for filename, record_type, records in [
        ("article_audit", ArticleDecision, decisions), ("signals", Signal, picks),
        ("orders", Order, orders), ("nav", DailyNAV, nav), ("summary", Summary, summaries),
    ]:
        write_table(args.out / f"{filename}.csv", record_type, records)

    print(f"Synthetic data | {len(market)} sessions | {len(decisions)} articles | {len(picks)} ranked slots")
    print("round-trip cost   total return    max drawdown     buys / sells")
    for s in summaries:
        print(f"{s.roundtrip_bps:8g} bp      {s.total_return:8.2%}        {s.max_drawdown:8.2%}"
              f"       {s.buy_fills:3d} / {s.sell_fills}")
    print(f"CSV output: {args.out}")


if __name__ == "__main__":
    main()
