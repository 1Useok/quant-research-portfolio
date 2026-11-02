"""확장 창 학습 + 검증 효용으로 ridge 선택 + 비용 포함 시뮬레이션."""

from math import sqrt

from model import GAMMA, Learner, adjustment_m, kappa_of

RIDGES = (0.003, 0.03, 0.3, 3.0)     # 상대 ridge 후보
VAL = 24                              # 검증 창(월)
FIRST_DECISION = 60                   # 첫 결정월: 학습 36개월 + 검증 24개월


def utility(nets, gamma=GAMMA):
    n = len(nets)
    mean = sum(nets) / n
    return mean - gamma / 2 * sum((v - mean) ** 2 for v in nets) / n


class Backtest:
    def __init__(self, panel, gamma=GAMMA, p=32):
        self.panel, self.gamma = panel, gamma
        self.learner = Learner(panel, p=p, gamma=gamma)
        self._aims, self._m = {}, {}

    def _m_list(self, wealth, aware, s):
        if not aware or wealth <= 0:
            return [0.0] * len(self.panel.stocks)
        key = (wealth, s)
        if key not in self._m:
            self._m[key] = [adjustment_m(self.gamma, v, kappa_of(wealth, a))
                            for v, a in zip(self.learner.var[s], self.panel.adv[s])]
        return self._m[key]

    def _step(self, prev, aim, m, wealth, s):
        """s월 말에 결정한 비중, 비용(부 대비), 총수익, 순수익(다음 달 수익률 기준)."""
        w = [mi * p + (1 - mi) * a for mi, p, a in zip(m, prev, aim)]
        cost = sum(0.5 * kappa_of(wealth, adv) * (x - p) ** 2
                   for x, p, adv in zip(w, prev, self.panel.adv[s])) if wealth > 0 else 0.0
        gross = sum(x * r for x, r in zip(w, self.panel.ret[s + 1]))
        return w, cost, gross, gross - cost

    def _drift(self, w, s, net):
        return [x * (1 + r) / (1 + net) for x, r in zip(w, self.panel.ret[s + 1])]

    def _val_aims(self, t, ridge):
        key = (t, ridge)
        if key not in self._aims:
            self._aims[key] = [self.learner.aim(t - VAL, ridge, s) for s in range(t - VAL, t)]
        return self._aims[key]

    def validation_utility(self, t, ridge, wealth, aware):
        """t월에 알 수 있는 정보만으로: t-VAL 이전 자료로 학습한 aim을 최근 VAL개월에 적용."""
        prev = [0.0] * len(self.panel.stocks)
        nets = []
        for s, aim in zip(range(t - VAL, t), self._val_aims(t, ridge)):
            w, _, _, net = self._step(prev, aim, self._m_list(wealth, aware, s), wealth, s)
            prev = self._drift(w, s, net)
            nets.append(net)
        return utility(nets, self.gamma)

    def run(self, wealth, aware, last=None):
        """wealth: 운용자산(억원). 0이면 비용 0. aware=False면 매달 aim으로 전부 거래(비용 무시 Markowitz)."""
        last = len(self.panel.ret) - 2 if last is None else last
        prev = [0.0] * len(self.panel.stocks)
        records = []
        for t in range(FIRST_DECISION, last + 1):
            utils = [self.validation_utility(t, r, wealth, aware) for r in RIDGES]
            ridge = RIDGES[max(range(len(RIDGES)), key=utils.__getitem__)]
            aim = self.learner.aim(t, ridge, t)
            w, cost, gross, net = self._step(prev, aim, self._m_list(wealth, aware, t), wealth, t)
            records.append({"month": t + 1, "ridge": ridge, "weights": w, "prev": prev,
                            "cost": cost, "gross": gross, "net": net})
            prev = self._drift(w, t, net)
        return records


def summarize(records, gamma=GAMMA):
    nets = [r["net"] for r in records]
    n = len(nets)
    mean = sum(nets) / n
    sd = sqrt(sum((v - mean) ** 2 for v in nets) / n)
    turnover = sum(sum(abs(a - b) for a, b in zip(r["weights"], r["prev"])) for r in records) / n
    return {
        "months": n,
        "net_return_ann": 12 * mean,
        "vol_ann": sqrt(12) * sd,
        "net_sharpe": sqrt(12) * mean / sd if sd else 0.0,
        "utility_ann": 12 * utility(nets, gamma),
        "turnover_month": turnover,
        "cost_ann": 12 * sum(r["cost"] for r in records) / n,
        "gross_exposure": sum(sum(abs(x) for x in r["weights"]) for r in records) / n,
    }
