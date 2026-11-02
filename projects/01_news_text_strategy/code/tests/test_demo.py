import unittest
from collections import defaultdict
from datetime import date
from pathlib import Path

from backtest import STARTING_CASH, Quote, market_by_session, simulate
from run_demo import read_rows
from signals import Signal, build_signals, train_baseline

DATA = Path(__file__).resolve().parents[1] / "data"
FRI, MON, TUE = map(date.fromisoformat, ["2025-02-07", "2025-02-10", "2025-02-11"])


class NewsTests(unittest.TestCase):
    def test_labels_must_have_resolved_before_the_first_session(self):
        rows = read_rows(DATA / "training.csv")
        cutoff = date(2025, 2, 3)
        future = [dict(label_end=day, headline="수주 확대", synthetic_return="-0.99")
                  for day in ("2025-02-03", "2025-02-04")]
        before = train_baseline(rows, cutoff)
        self.assertEqual(before, train_baseline(rows + future, cutoff))
        self.assertGreater(before.score("수주 확대"), before.score("납기 지연"))
        self.assertAlmostEqual(before.score("미관측단어"), 0.5)

    def test_eligibility_scoring_and_deterministic_ranks(self):
        market = market_by_session(read_rows(DATA / "market.csv"))
        model = train_baseline(read_rows(DATA / "training.csv"), min(market))
        news = read_rows(DATA / "news.csv")
        companies = read_rows(DATA / "companies.csv")
        audit, picks = build_signals(news, companies, set(market), model)
        self.assertEqual((audit, picks), build_signals(reversed(news), companies, set(market), model))
        decisions = {row.article_id: row for row in audit}
        self.assertEqual(decisions["N008"].decision, "accepted")     # Exactly 15:15:00 KST.
        self.assertEqual(decisions["X002"].decision, "outside_window")
        self.assertEqual(decisions["X001"].decision, "duplicate")
        self.assertEqual(decisions["X003"].decision, "multi_company")
        self.assertEqual(decisions["X004"].decision, "unmatched")
        self.assertEqual(decisions["X005"].decision, "outside_window")
        self.assertEqual(decisions["X006"].decision, "non_session")
        self.assertEqual(decisions["X007"].published_kst, "2025-02-03T13:25:00+09:00")
        opening = [s for s in picks if s.session == min(market)]
        self.assertEqual([s.symbol for s in opening], ["SIM01", "SIM03", "SIM02", "SIM04", "SIM05"])
        self.assertEqual(opening[0].article_count, 1)
        self.assertEqual(opening[2].article_count, 2)
        self.assertEqual(opening[3].mean_score, opening[4].mean_score)


class LedgerTests(unittest.TestCase):
    def test_flat_market_roundtrips_charge_fees_on_both_fills(self):
        market = {d: {"A": Quote(100, 100)} for d in (FRI, MON, TUE)}
        picks = [Signal(d, 1, "A", 1, 0.7) for d in (FRI, MON)]
        orders, daily, _ = simulate(market, picks, 30, top_n=1)
        r = 0.0015
        self.assertAlmostEqual(daily[-1].nav, STARTING_CASH * ((1-r) / (1+r))**2)
        self.assertEqual([o.session for o in orders], [FRI, MON, MON, TUE])
        self.assertTrue(all(d.cash >= 0 for d in daily))

    def test_missing_vwap_delays_exit_and_blocks_the_new_rank(self):
        market = {FRI: {"A": Quote(100, 100)}, MON: {"A": Quote(110, None), "B": Quote(20, 20)},
                  TUE: {"A": Quote(125, 120)}}
        picks = [Signal(FRI, 1, "A", 1, 0.8), Signal(MON, 1, "B", 1, 0.7)]
        orders, days, _ = simulate(market, picks, 0, top_n=1)
        self.assertEqual([o.status for o in orders], ["filled", "pending_vwap", "occupied_slot", "filled"])
        self.assertEqual((orders[-1].symbol, orders[-1].price), ("A", 120))
        self.assertAlmostEqual(days[1].nav, STARTING_CASH * 1.1)
        self.assertAlmostEqual(days[-1].nav, STARTING_CASH * 1.2)

    def test_unresolved_position_is_marked_at_last_close_at_sample_end(self):
        market = {FRI: {"A": Quote(100, 100)}, MON: {"A": Quote(None, None)}}
        orders, days, total = simulate(market, [Signal(FRI, 1, "A", 1, 0.8)], 0, top_n=1)
        self.assertEqual(orders[-1].status, "pending_vwap")
        self.assertEqual((total.sell_fills, total.final_open_slots), (0, 1))
        self.assertEqual((days[-1].nav, days[-1].cash), (STARTING_CASH, 0))

    def test_session_vwap_uses_value_over_volume(self):
        row = dict(session=FRI.isoformat(), symbol="A", close="108", traded_value="5250", volume="50")
        self.assertEqual(market_by_session([row])[FRI]["A"], Quote(108, 105))
        empty = dict(row, traded_value="0", volume="0")
        self.assertIsNone(market_by_session([empty])[FRI]["A"].vwap)
        with self.assertRaises(ValueError):
            market_by_session([dict(row, volume="0")])

    def test_sample_orders_rebuild_each_daily_nav(self):
        market = market_by_session(read_rows(DATA / "market.csv"))
        model = train_baseline(read_rows(DATA / "training.csv"), min(market))
        _, picks = build_signals(read_rows(DATA / "news.csv"), read_rows(DATA / "companies.csv"),
                                set(market), model)
        orders, days, summary = simulate(market, picks, 30)
        self.assertEqual((summary.buy_fills, summary.sell_fills, summary.final_open_slots), (41, 41, 0))
        self.assertTrue(any(o.status == "missing_close" for o in orders))
        cash = STARTING_CASH
        units = defaultdict(float)
        marks = {}
        for d in days:
            for o in orders:
                if o.session == d.session and o.status == "filled":
                    signed_units = o.quantity if o.side == "buy" else -o.quantity
                    units[o.symbol] += signed_units
                    cash -= signed_units * o.price + o.fee
            marks.update({s: q.close for s, q in market[d.session].items() if q.close is not None})
            holdings = sum(qty * marks[s] for s, qty in units.items())
            self.assertAlmostEqual(cash, d.cash, places=6)
            self.assertAlmostEqual(cash + holdings, d.nav, places=6)


if __name__ == "__main__":
    unittest.main()
