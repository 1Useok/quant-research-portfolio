"""python run_demo.py [--out DIR]"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from study import read_prices, run_study


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="합성 공적분 붕괴 신호와 양다리 체결 검산")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs", help="결과 CSV 폴더")
    args = parser.parse_args()
    tables = run_study(*read_prices(ROOT / "data" / "prices.csv"))
    args.out.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(args.out / f"{name}.csv", index=False, encoding="utf-8",
                     date_format="%Y-%m-%d", float_format="%.12g", lineterminator="\n")
    for row in tables["summary"].itertuples():
        net = "산출 불가" if pd.isna(row.mean_net_return) else f"{row.mean_net_return:+.3%}"
        print(f"합성 {row.split} / {row.spec} | 검정 {row.eg_tests}쌍 | 선정 {row.selected_pairs}쌍"
              f" | 신호 {row.signals}건 | 청산 {row.closed_trades}건 | 평균 순수익 {net}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
