"""가상 주간 입력과 평가용 공표표를 다시 만든다. 후보 모델을 사용하지 않는다."""

import csv
from datetime import date, timedelta
from pathlib import Path


def published_order(available, weights):
    """가상 발행처의 고정 등급표. 원점수 20점마다 한 등급, 공란은 중간 등급."""
    grades_by_symbol = {}
    for symbol, values in available.items():
        if values.count(None) > 1:
            continue
        grades = [2 if x is None else min(x // 20, 4) for x in values]
        grades_by_symbol[symbol] = sum(w * g for w, g in zip(weights, grades))
    return sorted(grades_by_symbol, key=lambda s: (-grades_by_symbol[s], s))[:3]


def build(folder):
    factor_rows, macro_rows, close_rows, reference_rows = [], [], [], []
    closes = [10000 + 370 * j for j in range(8)]
    rotation = [(60, 25, 15), (15, 60, 25), (25, 15, 60)]
    cycle_path = (-2, -1, 1, 2, 1, 0, -1, 0)
    for week in range(18):
        friday = date(2024, 3, 1) + timedelta(weeks=week)
        thursday = friday - timedelta(days=1)
        monday = friday + timedelta(days=3)
        cycle = cycle_path[week % len(cycle_path)]
        release = monday if week % 3 == 1 else thursday
        macro_rows.append((friday - timedelta(days=2), release, cycle))

        available = {}
        for j, price in enumerate(closes):
            symbol = f"F{j + 1:02}"
            value = 8 + (7 * week + 13 * j + 2 * j * j) % 81
            quality = 5 + 5 * ((3 * week + 7 * j + j * j) % 19)
            trend = 5 + (4 * week * week + 11 * j + 2 * week * j) % 91
            values = (value, None if (week + j) % 6 == 0 else quality,
                      None if (week + 2 * j) % 9 == 0 else trend)
            arrives = monday if (2 * week + j) % 13 == 0 else friday
            factor_rows.append((thursday, arrives, symbol, *values))
            if arrives <= friday:
                available[symbol] = values
            close_rows.append((monday, symbol, price))
            noise = ((week + 1) * (j + 3) * 19) % 151 - 75
            change_bp = cycle * (value - quality) + trend - 50 + noise
            closes[j] = (price * (10000 + change_bp) + 5000) // 10000

        if week >= 10:
            weights = rotation[friday.isocalendar().week % 3]
            picks = published_order(available, weights)
            reference_rows.append((friday, *weights, *picks))

    files = [
        ("factors.csv", ("observed_on", "available_on", "symbol", "value", "quality", "trend"), factor_rows),
        ("macro.csv", ("observed_on", "available_on", "cycle"), macro_rows),
        ("closes.csv", ("session", "symbol", "close"), close_rows),
        ("reference.csv", ("signal_date", "value_pct", "quality_pct", "trend_pct",
                           "pick_1", "pick_2", "pick_3"), reference_rows),
    ]
    for name, header, records in files:
        with (folder / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(records)


if __name__ == "__main__":
    build(Path(__file__).resolve().parent)
