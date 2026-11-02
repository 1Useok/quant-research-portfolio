"""배포용 가상 시세를 같은 바이트로 다시 만든다."""

import csv
from pathlib import Path

import numpy as np
import pandas as pd


def write_prices(path):
    dates = pd.bdate_range("2030-01-02", "2030-08-30").difference(
        pd.to_datetime(["2030-07-17", "2030-08-14"])
    )
    rng = np.random.default_rng(32)
    walks = rng.normal(0.0006, 0.010, (len(dates), 4)).cumsum(axis=0)
    noise = rng.standard_normal((len(dates), 2))
    for i in range(1, len(dates)):
        noise[i] += np.array([0.75, 0.90]) * noise[i - 1]

    # 두 쌍은 각각 공통 추세를 갖는다. C에만 평가 중 수준 이동을 넣는다.
    shift = 0.029 * (dates >= "2030-08-02")
    log_close = np.column_stack([
        4.5 + 1.15 * walks[:, 0] + 0.002 * noise[:, 0], 4.3 + walks[:, 0],
        4.7 + 0.82 * walks[:, 1] + 0.003 * noise[:, 1] + shift, 4.4 + walks[:, 1],
        4.1 + walks[:, 2], 4.8 + walks[:, 3],
    ])
    prior = np.vstack(([4.5, 4.3, 4.7, 4.4, 4.1, 4.8], log_close[:-1]))
    opens = np.exp(prior + rng.normal(0, 0.002, prior.shape))
    closes = np.exp(log_close)
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["date", "symbol", "open", "close"])
        for i, date in enumerate(dates):
            for j, symbol in enumerate(("SIM_A", "SIM_B", "SIM_C", "SIM_D", "SIM_E", "SIM_F")):
                opening = f"{opens[i, j]:.6f}"
                if date == pd.Timestamp("2030-07-29") and symbol == "SIM_C":
                    opening = ""
                writer.writerow([date.date(), symbol, opening, f"{closes[i, j]:.6f}"])


if __name__ == "__main__":
    write_prices(Path(__file__).parent / "data" / "prices.csv")
