import csv
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import make_sample  # noqa: E402
from backtest import FIRST_DECISION, Backtest, summarize  # noqa: E402
from model import Learner, adjustment_m, kappa_of, load_panel  # noqa: E402
from run_demo import WEALTHS, compute, write_outputs  # noqa: E402

PANEL_PATH = ROOT / "data" / "panel.csv"


class DemoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = load_panel(PANEL_PATH)
        cls.runs = compute(cls.panel)
        cls.stats = {k: summarize(v) for k, v in cls.runs.items()}

    def test_sample_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "panel.csv"
            make_sample.write(path)
            self.assertEqual(path.read_bytes(), PANEL_PATH.read_bytes())

    def test_backtest_is_deterministic(self):
        again = compute(self.panel, last=FIRST_DECISION + 5, wealths=(100,))
        for key, rec in again.items():
            self.assertEqual([r["weights"] for r in rec], [r["weights"] for r in self.runs[key][:6]])

    def test_no_look_ahead(self):
        """결정월 cut 이후의 특성·수익률·ADV를 바꿔도 cut 이전 결정(비중)은 그대로다."""
        cut = FIRST_DECISION + 8
        p = self.panel
        n_stock = len(p.stocks)
        changed = replace(
            p,
            x=[row if t <= cut else [[-v for v in xi] for xi in row] for t, row in enumerate(p.x)],
            ret=[row if t <= cut else [0.3 * (-1) ** i for i in range(n_stock)] for t, row in enumerate(p.ret)],
            adv=[row if t <= cut else [1.0] * n_stock for t, row in enumerate(p.adv)],
        )
        for aware in (False, True):
            base = Backtest(p).run(100, aware, cut - 1)       # 결정월 cut-1의 수익은 cut월 수익률을 쓴다.
            alt = Backtest(changed).run(100, aware, cut - 1)
            self.assertEqual([r["weights"] for r in base], [r["weights"] for r in alt])
            self.assertEqual([r["ridge"] for r in base], [r["ridge"] for r in alt])

    def test_zero_cost_converges(self):
        self.assertEqual(adjustment_m(10.0, 0.005, 0.0), 0.0)
        blind, aware = self.runs[(0, False)], self.runs[(0, True)]
        self.assertEqual([r["weights"] for r in blind], [r["weights"] for r in aware])

    def test_m_properties(self):
        lo, hi = adjustment_m(10.0, 0.005, 1.0), adjustment_m(10.0, 0.005, 20.0)
        self.assertTrue(0.0 < lo < hi < 1.0)                  # 비용이 클수록 천천히 움직인다.
        self.assertGreater(adjustment_m(10.0, 0.005, 5.0), adjustment_m(10.0, 0.02, 5.0))  # 위험이 크면 더 빨리

    def test_cost_aware_trades_less_and_earns_more_net(self):
        for wealth in WEALTHS[1:]:
            blind, aware = self.stats[(wealth, False)], self.stats[(wealth, True)]
            self.assertLess(aware["turnover_month"], blind["turnover_month"])
            self.assertLess(aware["cost_ann"], blind["cost_ann"])
        # 비용이 오를수록 비용 무시 전략의 순효용은 떨어진다.
        util = [self.stats[(w, False)]["utility_ann"] for w in WEALTHS]
        self.assertEqual(util, sorted(util, reverse=True))
        top = WEALTHS[-1]
        self.assertGreater(self.stats[(top, True)]["utility_ann"], self.stats[(top, False)]["utility_ann"])

    def test_cost_matches_input_formula(self):
        """비용 = 0.1 * q^2 / ADV 를 부(富) 대비로 환산한 값과 기록이 일치한다."""
        wealth = 100
        for r in self.runs[(wealth, True)][:10]:
            s = r["month"] - 1                                  # 결정월
            expect = sum(0.1 * (wealth * (w - p)) ** 2 / adv / wealth
                         for w, p, adv in zip(r["weights"], r["prev"], self.panel.adv[s]))
            self.assertAlmostEqual(r["cost"], expect, places=12)
            self.assertAlmostEqual(kappa_of(wealth, 50.0), 0.2 * wealth / 50.0)

    def test_ledger_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_outputs(self.panel, self.runs, Path(tmp))
            with (Path(tmp) / "nav.csv").open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertTrue((Path(tmp) / "frontier.csv").exists())
            self.assertEqual(len(rows), sum(len(v) for v in self.runs.values()))
        by_key = {}
        for row in rows:
            by_key.setdefault((row["wealth_eok"], row["strategy"]), []).append(row)
        for series in by_key.values():
            nav = 1.0
            for row in series:
                self.assertAlmostEqual(float(row["gross_return"]) - float(row["cost"]), float(row["net_return"]), places=5)
                nav *= 1 + float(row["net_return"])
                self.assertAlmostEqual(nav, float(row["nav"]), places=3)

    def test_weights_use_recorded_prev_and_drift(self):
        """첫 결정은 0에서 시작하고, 다음 달 prev는 수익률로 표류한 이전 비중이다."""
        rec = self.runs[(100, True)]
        self.assertTrue(all(v == 0.0 for v in rec[0]["prev"]))
        s = rec[0]["month"] - 1
        for i, prev in enumerate(rec[1]["prev"]):
            expect = rec[0]["weights"][i] * (1 + self.panel.ret[s + 1][i]) / (1 + rec[0]["net"])
            self.assertAlmostEqual(prev, expect, places=12)

    def test_learner_prefers_real_signal(self):
        """진짜 신호가 있는 합성 자료에서는 비용 0 표본외 순샤프가 양수다."""
        self.assertGreater(self.stats[(0, True)]["net_sharpe"], 0.3)


if __name__ == "__main__":
    unittest.main()
