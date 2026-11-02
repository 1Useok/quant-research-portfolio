"""합성 패널을 결정적으로 만들어 data/panel.csv에 쓴다. python make_sample.py"""

import csv
import math
import random
from pathlib import Path

N_STOCKS, N_MONTHS, SEED = 30, 120, 20240601
PHI = (0.90, 0.70, 0.95)          # 세 특성의 월 자기상관
HERE = Path(__file__).resolve().parent


def true_mean(x):
    """알려진 비선형 기대수익률(월). 특성 3개의 표준화 값 x를 받는다."""
    return 0.004 * (x[0] + 0.8 * math.sin(1.5 * x[1]) + 0.6 * x[0] * x[2])


def generate(seed=SEED, n_stocks=N_STOCKS, n_months=N_MONTHS):
    rnd = random.Random(seed)
    sigma = [0.07 * math.exp(0.25 * rnd.gauss(0, 1)) for _ in range(n_stocks)]
    adv_base = [40.0 * math.exp(0.7 * rnd.gauss(0, 1)) for _ in range(n_stocks)]   # 억원/일 가정
    x = [[rnd.gauss(0, 1) for _ in PHI] for _ in range(n_stocks)]
    adv_dev = [0.0] * n_stocks
    rows = []
    for t in range(n_months):
        prev = x
        x = [[PHI[k] * prev[i][k] + math.sqrt(1 - PHI[k] ** 2) * rnd.gauss(0, 1) for k in range(3)]
             for i in range(n_stocks)]
        for i in range(n_stocks):
            adv_dev[i] = 0.9 * adv_dev[i] + 0.2 * rnd.gauss(0, 1)
            ret = true_mean(prev[i]) + sigma[i] * rnd.gauss(0, 1)   # 이달 수익률은 전월말 특성의 함수
            rows.append((t, f"S{i + 1:02d}", *(round(v, 4) for v in x[i]), round(ret, 5),
                         round(adv_base[i] * math.exp(adv_dev[i]), 2)))
    return rows


def write(path=HERE / "data" / "panel.csv"):
    with Path(path).open("w", encoding="utf-8", newline="") as out:
        w = csv.writer(out, lineterminator="\n")
        w.writerow("month stock x1 x2 x3 ret adv".split())
        w.writerows(generate())


if __name__ == "__main__":
    write()
