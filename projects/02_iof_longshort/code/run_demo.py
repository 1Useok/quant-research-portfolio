"""합성 IOF 예제 실행 및 UTF-8 장부 출력."""

import argparse
import csv
import sys
from pathlib import Path

from backtest import INITIAL_CASH, simulate
from signals import read_inputs

ROOT = Path(__file__).resolve().parent
HEADERS = {
    "signals": "signal_date entry_date sleeve symbol cap_rank in_universe month_a mean_a "
               "month_b mean_b flow iof long_rank short_rank target",
    "orders": "signal_date entry_date sleeve side symbol action status target_value open "
              "qty_before filled_qty qty_after",
    "holdings": "entry_date mark_date sleeve symbol qty entry_mark end_mark entry_stale end_stale",
    "daily": "signal_date entry_date mark_date sleeve cash_before nav_start traded turnover "
             "trade_cost long_value short_value borrow_fee gross_pnl net_pnl cash_after nav_end net_return",
}


def write_ledgers(result, folder):
    folder.mkdir(parents=True, exist_ok=True)
    for name, header in HEADERS.items():
        with (folder / (name + ".csv")).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=header.split(), lineterminator="\n")
            writer.writeheader()
            for row in result[name]:
                writer.writerow({k: format(v or 0.0, ".15g")
                                 if isinstance(v, float) else v for k, v in row.items()})


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs", help="CSV 출력 폴더")
    args = parser.parse_args()
    result = simulate(*read_inputs(ROOT / "data"))
    write_ledgers(result, args.out)
    daily = result["daily"]
    print(f"합성 시가 구간 {len(daily)}개 | NAV {INITIAL_CASH:,.2f} -> {daily[-1]['nav_end']:,.2f}")
    print(f"거래비용 {sum(r['trade_cost'] for r in daily):,.2f} | "
          f"대차료 {sum(r['borrow_fee'] for r in daily):,.2f}")


if __name__ == "__main__":
    main()
