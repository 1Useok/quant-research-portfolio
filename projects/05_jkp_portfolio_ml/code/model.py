"""랜덤 푸리에 특성 + 효용 최대화 ridge(Portfolio-ML 방식)와 부분조정 계수 m."""

import csv
import random
from dataclasses import dataclass
from math import cos, sin, sqrt
from operator import mul
from pathlib import Path

GAMMA = 10.0          # 위험회피
RHO = 0.99            # 월 할인계수
COST_COEF = 0.1       # 거래비용 = 0.1 * q^2 / ADV (q: 거래금액)
VAR_PRIOR, VAR_PRIOR_N = 0.07 ** 2, 12


@dataclass(frozen=True)
class Panel:
    stocks: list
    x: list      # x[t][i] = 횡단면 표준화한 특성 3개 (t월 말)
    ret: list    # ret[t][i] = t월 수익률
    adv: list    # adv[t][i] = t월 일평균 거래대금(억원)


def load_panel(path):
    with Path(path).open(encoding="utf-8", newline="") as src:
        rows = list(csv.DictReader(src))
    stocks = sorted({r["stock"] for r in rows})
    index = {s: i for i, s in enumerate(stocks)}
    n_months = max(int(r["month"]) for r in rows) + 1
    if len(rows) != n_months * len(stocks):
        raise ValueError("월·종목 격자가 완전하지 않습니다.")
    x = [[None] * len(stocks) for _ in range(n_months)]
    ret = [[0.0] * len(stocks) for _ in range(n_months)]
    adv = [[0.0] * len(stocks) for _ in range(n_months)]
    for r in rows:
        t, i = int(r["month"]), index[r["stock"]]
        x[t][i] = [float(r["x1"]), float(r["x2"]), float(r["x3"])]
        ret[t][i], adv[t][i] = float(r["ret"]), float(r["adv"])
    for t in range(n_months):                     # 같은 달 안에서만 표준화한다.
        for k in range(3):
            col = [v[k] for v in x[t]]
            mu = sum(col) / len(col)
            sd = sqrt(sum((c - mu) ** 2 for c in col) / len(col)) or 1.0
            for v in x[t]:
                v[k] = (v[k] - mu) / sd
    return Panel(stocks, x, ret, adv)


def causal_variance(panel):
    """var[t][i]: t월까지 수익률만 쓴 수축 분산(미래 정보 없음)."""
    ss, out = [0.0] * len(panel.stocks), []
    for t, rets in enumerate(panel.ret):
        ss = [a + r * r for a, r in zip(ss, rets)]
        out.append([(a + VAR_PRIOR_N * VAR_PRIOR) / (t + 1 + VAR_PRIOR_N) for a in ss])
    return out


def rff_features(x_row, freqs):
    """x_row: 특성 3개. freqs: 고정 난수 주파수. 반환 길이 2*len(freqs)."""
    ang = [sum(w * v for w, v in zip(f, x_row)) for f in freqs]
    s = 1.0 / sqrt(len(freqs))
    return [s * cos(a) for a in ang] + [s * sin(a) for a in ang]


def solve_spd(a, b):
    """Cholesky로 a x = b를 푼다(a는 대칭 양정치)."""
    n = len(a)
    low = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = a[i][j] - sum(map(mul, low[i][:j], low[j][:j]))
            low[i][j] = sqrt(s) if i == j else s / low[j][j]
    y = [0.0] * n
    for i in range(n):
        y[i] = (b[i] - sum(map(mul, low[i][:i], y[:i]))) / low[i][i]
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (y[i] - sum(low[j][i] * x[j] for j in range(i + 1, n))) / low[i][i]
    return x


class Learner:
    """k개월(0..k-1월의 특성 → 다음 달 수익률 쌍)로 aim 포트폴리오 계수 theta를 학습한다.

    aim_i = z_i' theta,  theta = argmax  theta'b - gamma/2 theta'A theta - lam/2 |theta|^2
    b = 평균 sum_i z_i r_i,  A = 평균 sum_i var_i z_i z_i'  (JKMP의 정적 aim 문제, 대각 위험).
    """

    def __init__(self, panel, p=32, seed=7, gamma=GAMMA, bandwidth=1.0):
        self.panel, self.gamma, self.p = panel, gamma, p
        rnd = random.Random(seed)
        freqs = [[bandwidth * rnd.gauss(0, 1) for _ in range(3)] for _ in range(p // 2)]
        self.var = causal_variance(panel)
        self.z = [[rff_features(xi, freqs) for xi in month] for month in panel.x]
        self.cum_a, self.cum_b = [[[0.0] * p for _ in range(p)]], [[0.0] * p]
        for s in range(len(self.z) - 1):
            a = [row[:] for row in self.cum_a[-1]]
            b = self.cum_b[-1][:]
            for zi, vi, ri in zip(self.z[s], self.var[s], panel.ret[s + 1]):
                for u in range(p):
                    c = vi * zi[u]
                    a[u] = [x + c * y for x, y in zip(a[u], zi)]
                b = [x + ri * y for x, y in zip(b, zi)]
            self.cum_a.append(a)
            self.cum_b.append(b)
        self._theta = {}

    def theta(self, k, ridge):
        """ridge는 gamma*A의 평균 대각에 곱하는 상대 크기."""
        key = (k, ridge)
        if key not in self._theta:
            a = [[self.gamma * v / k for v in row] for row in self.cum_a[k]]
            lam = ridge * sum(a[u][u] for u in range(self.p)) / self.p
            for u in range(self.p):
                a[u][u] += lam
            self._theta[key] = solve_spd(a, [v / k for v in self.cum_b[k]])
        return self._theta[key]

    def aim(self, k, ridge, t):
        th = self.theta(k, ridge)
        return [sum(map(mul, zi, th)) for zi in self.z[t]]


def adjustment_m(gamma, var, kappa, rho=RHO):
    """대각 이차비용의 동적 해 w_t = m w_prev + (1-m) aim 의 m.

    비용 = kappa/2 * dw^2 (비중 단위), 위험 항 g = gamma*var.
    가치함수 계수 P는 rho P^2 + (g + kappa(1-rho)) P - kappa g = 0 의 양근이고 m = kappa/(kappa+g+rho P).
    kappa=0이면 m=0이라 비용을 무시한 Markowitz와 같다.
    """
    if kappa <= 0:
        return 0.0
    g = gamma * var
    c = g + kappa * (1 - rho)
    p = (-c + sqrt(c * c + 4 * rho * kappa * g)) / (2 * rho)
    return kappa / (kappa + g + rho * p)


def kappa_of(wealth, adv):
    """비용 0.1*(W dw)^2/ADV 를 부 대비 비중 단위로 쓰면 kappa/2 dw^2, kappa = 0.2 W/ADV."""
    return 2 * COST_COEF * wealth / adv
