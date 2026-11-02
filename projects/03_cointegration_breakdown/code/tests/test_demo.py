import csv
import subprocess
import sys
import unittest
from itertools import combinations
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
import pandas as pd
from statsmodels.tsa.adfvalues import mackinnonp
from statsmodels.tsa.stattools import adfuller

from make_sample import write_prices
from study import read_prices, run_study


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "prices.csv"


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.opens, cls.closes = read_prices(INPUT)
        cls.tables = run_study(cls.opens, cls.closes)

    def test_fixture_order_duplicates_and_blanks(self):
        with TemporaryDirectory(dir=ROOT) as tmp:
            path = Path(tmp) / "prices.csv"
            write_prices(path)
            self.assertEqual(path.read_bytes(), INPUT.read_bytes())
            rows = pd.read_csv(path).iloc[::-1]
            self.assertEqual(len(rows), 171 * 6)
            rows.to_csv(path, index=False)
            opens, closes = read_prices(path)
            pd.testing.assert_frame_equal(opens, self.opens)
            pd.testing.assert_frame_equal(closes, self.closes)
            self.assertTrue(pd.isna(opens.at[pd.Timestamp("2030-07-29"), "SIM_C"]))
            pd.concat([rows, rows.iloc[:1]]).to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "중복"):
                read_prices(path)
            rows.iloc[0, rows.columns.get_loc("close")] = 0
            rows.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "양수"):
                read_prices(path)

    def test_unit_roots_and_full_monthly_bh_family(self):
        for split, end, count in (("validation", "2030-06-28", 15), ("evaluation", "2030-07-31", 10)):
            hist = np.log(self.closes.loc[:end].tail(120))
            screen = self.tables["screen"].query("split == @split").set_index("symbol")
            eligible = []
            for symbol, level in hist.items():
                pl, pdiff = [adfuller(x, maxlag=2, autolag="AIC")[1] for x in (level, np.diff(level))]
                self.assertAlmostEqual(screen.at[symbol, "adf_level_p"], pl)
                self.assertAlmostEqual(screen.at[symbol, "adf_diff_p"], pdiff)
                self.assertEqual(screen.at[symbol, "eligible"], pl >= .05 and pdiff < .05)
                if pl >= .05 and pdiff < .05:
                    eligible.append(symbol)
            pairs = self.tables["pairs"].query("split == @split").set_index(["a", "b"])
            self.assertEqual(set(pairs.index), set(combinations(eligible, 2)))
            self.assertEqual(len(pairs), count)
            self.assertTrue((pairs.formation_start == hist.index[0]).all())
            self.assertTrue((pairs.formation_end == hist.index[-1]).all())
            pvalues = {}
            for (a, b), pair in pairs.iterrows():
                beta, alpha = np.polyfit(hist[b], hist[a], 1)
                residual = hist[a] - alpha - beta * hist[b]
                tau = adfuller(residual, regression="n", maxlag=2, autolag="AIC")[0]
                # 잔차의 tau에 상수 포함 2변수 공적분 귀무분포를 적용한다.
                pvalues[a, b] = mackinnonp(tau, regression="c", N=2)
                self.assertAlmostEqual(pair.eg_stat, tau)
                self.assertAlmostEqual(pair.eg_p, pvalues[a, b])
                self.assertAlmostEqual(pair.beta, beta)
                self.assertAlmostEqual(pair.alpha, alpha)
                lag, current = residual.to_numpy()[:-1], residual.to_numpy()[1:]
                phi, intercept = np.polyfit(lag, current, 1)
                half = np.log(0.5) / np.log(phi) if 0 < phi < 1 else np.nan
                scale = (current - intercept - phi * lag).std(ddof=2)
                self.assertEqual(pair.stable, .25 <= beta <= 4 and 2 <= half <= 60
                                 and min(residual.std(ddof=1), scale) > 1e-9)
            ordered = sorted(pvalues, key=pvalues.get)
            ranked = [count * pvalues[key] / rank for rank, key in enumerate(ordered, 1)]
            for i, key in enumerate(ordered):
                pair = pairs.loc[key]
                q = min(1.0, *ranked[i:])
                self.assertAlmostEqual(pair.bh_q, q)
                self.assertEqual(pair.primary_bh, pair.stable and q <= .05)
                self.assertEqual(pair.exploratory_raw, pair.stable and pvalues[key] < .05)

    def test_first_directional_alarm_from_past_closes(self):
        for month, side in (("2030-07", -1), ("2030-08", 1)):
            watch = self.closes.loc[month].index
            history = self.closes[self.closes.index < watch[0]].tail(120)
            prices = np.log(self.closes.loc[history.index[0]:watch[-1]])
            beta, alpha = np.polyfit(np.log(history.SIM_D), np.log(history.SIM_C), 1)
            spread = (prices.SIM_C - alpha - beta * prices.SIM_D).to_numpy()
            train = spread[:120]
            phi, intercept = np.polyfit(train[:-1], train[1:], 1)
            scale = np.std(train[1:] - phi * train[:-1] - intercept, ddof=2)
            upper = lower = 0.0
            for i in range(120, len(spread)):
                error = (spread[i] - phi * spread[i - 1] - intercept) / scale
                upper = max(0, upper + error - .5)
                lower = min(0, lower + error + .5)
                z = (spread[i] - train.mean()) / train.std(ddof=1)
                m5, m20 = spread[i] - spread[i - 5], spread[i] - spread[i - 20]
                if ((z >= 2 and min(m5, m20) > 0 and upper > 5)
                        or (z <= -2 and max(m5, m20) < 0 and lower < -5)):
                    break
            else:
                self.fail(f"{month} 독립 계산에서 경보가 발생하지 않았습니다.")
            matches = self.tables["events"].query("a == 'SIM_C' and b == 'SIM_D' and spec == 'exploratory_raw'")
            row = matches[matches.signal_date.isin(watch)].iloc[0]
            self.assertEqual(row.signal_date, prices.index[i])
            self.assertEqual(row.direction, side)
            self.assertEqual(side, np.sign(z))
            np.testing.assert_allclose([row.z, row.change_5, row.change_20, row.cusum],
                                       [z, m5, m20, upper if side > 0 else -lower])

    def test_future_prices_do_not_select_pairs_or_move_an_earlier_alarm(self):
        cutoff = pd.Timestamp("2030-08-02")
        opens, closes = self.opens.copy(), self.closes.copy()
        closes.loc[closes.index > cutoff, "SIM_C"] *= 0.7
        opens.loc["2030-08-20", "SIM_D"] *= 1.1
        changed = run_study(opens, closes)
        for name in ("screen", "pairs"):
            pd.testing.assert_frame_equal(self.tables[name], changed[name])
        before, after = self.tables["events"], changed["events"]
        pd.testing.assert_frame_equal(before.query("split == 'validation'"), after.query("split == 'validation'"))
        cols = ["signal_date", "spec", "a", "b", "direction", "beta", "z", "change_5", "change_20", "cusum"]
        pd.testing.assert_frame_equal(before.loc[before.signal_date <= cutoff, cols].reset_index(drop=True),
                                      after.loc[after.signal_date <= cutoff, cols].reset_index(drop=True))
        self.assertNotAlmostEqual(before.loc[before.signal_date == cutoff, "net_return"].item(),
                                  after.loc[after.signal_date == cutoff, "net_return"].item())

    def test_session_dates_and_four_fill_cash_flows(self):
        # 원시 CSV의 날짜와 시가로 두 다리의 현금 장부를 따로 합산한다.
        quotes = pd.read_csv(INPUT).pivot(index="date", columns="symbol", values="open").sort_index()
        events = self.tables["events"]
        with patch("study.FEE_BPS", 0):
            free = run_study(self.opens, self.closes)["events"]
        identity = ["spec", "a", "b", "signal_date", "entry_date", "exit_date", "status"]
        pd.testing.assert_frame_equal(free[identity], events[identity])
        filled = events[events.status == "closed"]
        self.assertEqual(set(filled.direction), {-1, 1})
        self.assertEqual(set(filled.exit_delay_sessions), {0, 1})
        for row in filled.itertuples():
            dates = quotes.index.tolist()
            entry = dates.index(row.signal_date.date().isoformat()) + 1
            due = entry + 10
            joint = quotes.loc[dates[due]:, [row.a, row.b]].dropna()
            self.assertEqual(row.entry_date, pd.Timestamp(dates[entry]))
            self.assertEqual(row.exit_due, pd.Timestamp(dates[due]))
            self.assertEqual(row.exit_date, pd.Timestamp(joint.index[0]))
            self.assertEqual(row.exit_delay_sessions, dates.index(joint.index[0]) - due)
            start = quotes.loc[dates[entry], [row.a, row.b]].to_numpy()
            end = joint.iloc[0].to_numpy()
            np.testing.assert_array_equal([row.entry_a, row.entry_b], start)
            np.testing.assert_array_equal([row.exit_a, row.exit_b], end)
            # 진입 총액 1, B 대 A의 절대 금액비 beta, 청산 때 같은 수량.
            past = np.log(self.closes.loc[:row.formation_end, [row.a, row.b]].tail(120))
            beta = np.polyfit(past[row.b], past[row.a], 1)[0]
            qty = row.direction * np.array([1, -beta]) / (1 + beta) / start
            np.testing.assert_allclose([row.qty_a, row.qty_b], qty)
            at_entry, at_exit = -qty * start, qty * end
            self.assertAlmostEqual(sum(abs(at_entry)), 1)
            self.assertAlmostEqual(at_entry[1] / at_entry[0], -row.beta)
            self.assertEqual(np.sign(qty[0]), row.direction)
            fills = [*at_entry, *at_exit]
            fees = [abs(cash) / 1000 for cash in fills]
            np.testing.assert_allclose([row.fee_entry_a, row.fee_entry_b, row.fee_exit_a, row.fee_exit_b], fees)
            np.testing.assert_allclose([row.pnl_a, row.pnl_b], at_entry + at_exit)
            self.assertAlmostEqual(row.gross_return, sum(fills))
            self.assertAlmostEqual(row.net_return, sum(fills) - sum(fees))
            self.assertAlmostEqual(free.at[row.Index, "net_return"] - row.net_return, sum(fees))
        eval_trade = filled.query("split == 'evaluation'").iloc[0]
        self.assertEqual(str(eval_trade.entry_date.date()), "2030-08-05")
        self.assertEqual(str(eval_trade.exit_date.date()), "2030-08-20")
        for row in events.query("status == 'outside_window'").itertuples():
            month = quotes.loc[quotes.index.str.startswith(row.signal_date.strftime("%Y-%m"))]
            self.assertLess(len(month) - month.index.get_loc(str(row.signal_date.date())) - 1, 11)
            self.assertTrue(pd.isna(row.entry_date) and pd.isna(row.net_return))

    def test_missing_entry_and_unresolved_exit_stay_in_ledger(self):
        opens = self.opens.copy()
        opens.loc["2030-07-29":"2030-07-31", "SIM_D"] = np.nan
        opens.loc["2030-08-05", "SIM_D"] = np.nan
        tables = run_study(opens, self.closes)
        trades = tables["events"].query("a == 'SIM_C' and b == 'SIM_D' and spec == 'exploratory_raw'")
        july, august = list(trades.itertuples())
        self.assertEqual(july.status, "unresolved_exit")
        self.assertEqual(july.entry_date, pd.Timestamp("2030-07-12"))
        self.assertTrue(pd.isna(july.exit_date) and pd.isna(july.net_return))
        self.assertEqual(august.status, "no_entry_open")
        self.assertTrue(pd.isna(august.entry_date) and pd.isna(august.qty_a))
        self.assertTrue(tables["summary"].mean_net_return.isna().all())
        self.assertEqual(tables["summary"].closed_trades.sum(), 0)

    def test_missing_close_and_empty_family(self):
        closes = self.closes.copy()
        closes.loc["2030-07-10", "SIM_F"] = np.nan  # 8월 선정 창 안의 결측
        closes.loc["2030-08-01", "SIM_C"] = np.nan  # 8월 감시 시작 직후의 결측
        tables = run_study(self.opens, closes)
        screen = tables["screen"].query("split == 'evaluation' and symbol == 'SIM_F'").iloc[0]
        self.assertEqual(screen.valid_closes, 119)
        self.assertFalse(screen.eligible)
        self.assertEqual(len(tables["pairs"].query("split == 'evaluation'")), 6)
        self.assertTrue(tables["events"].query("split == 'evaluation' and a == 'SIM_C' and b == 'SIM_D'").empty)
        flat = run_study(self.opens, self.closes * 0 + 100)
        self.assertTrue(flat["pairs"].empty and flat["events"].empty)
        self.assertTrue(flat["summary"][["eg_tests", "signals", "closed_trades"]].eq(0).all().all())
        self.assertTrue(flat["summary"].mean_gross_return.isna().all())

    def test_cli_csvs_and_zero_trade_mean(self):
        with TemporaryDirectory(dir=ROOT) as tmp:
            out = Path(tmp) / "result"
            result = subprocess.run([sys.executable, str(ROOT / "run_demo.py"), "--out", str(out)],
                                    cwd=tmp, capture_output=True, encoding="utf-8", check=True)
            self.assertIn("산출 불가", result.stdout)
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["events.csv", "pairs.csv", "screen.csv", "summary.csv"])
            with (out / "summary.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([(r["split"], r["spec"]) for r in rows], [
                ("validation", "primary_bh"), ("validation", "exploratory_raw"),
                ("evaluation", "primary_bh"), ("evaluation", "exploratory_raw")])
            counts = ["sessions", "eg_tests", "selected_pairs", "signals", "outside_window", "closed_trades"]
            self.assertEqual([[int(r[c]) for c in counts] for r in rows],
                             [[22, 15, 6, 1, 0, 1], [22, 15, 6, 1, 0, 1],
                              [21, 10, 3, 2, 2, 0], [21, 10, 6, 5, 4, 1]])
            self.assertEqual((rows[2]["mean_gross_return"], rows[2]["mean_net_return"]), ("", ""))
            self.assertAlmostEqual(float(rows[0]["mean_net_return"]), -0.000875864295)
            self.assertAlmostEqual(float(rows[3]["mean_net_return"]), 0.005902539923)


if __name__ == "__main__":
    unittest.main()
