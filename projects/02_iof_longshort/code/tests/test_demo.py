import csv
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from datetime import date
from pathlib import Path

from backtest import current_sides, refresh, simulate
from signals import Auction, Close, read_inputs, select

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def on(rows, day):
    return [r for r in rows if r["entry_date"] == day]


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        output = ROOT / "outputs"
        output.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=output)
        cls.addClassCleanup(temp.cleanup)
        cls.work = Path(temp.name)
        cls.export = cls.work / "검산 장부"
        command = [sys.executable, str(ROOT / "run_demo.py"), "--out", str(cls.export)]
        subprocess.run(command, cwd=cls.work, check=True, capture_output=True, encoding="utf-8")
        cls.signals, cls.orders, cls.holdings, cls.daily = (
            read_csv(cls.export / (name + ".csv")) for name in ("signals", "orders", "holdings", "daily")
        )

    def test_denominators_and_cap_cutoff_before_missing_scores(self):
        first = {r["symbol"]: r for r in on(self.signals, "2025-03-25")}
        a = first["SIM01"]
        self.assertEqual((a["month_a"], a["month_b"]), ("2025-02", "2024-02"))
        self.assertEqual([float(a[k]) for k in ("mean_a", "mean_b", "flow", "iof")],
                         [1_300_000, 1_000_000, -8000, -0.008])
        self.assertEqual((a["target"], first["SIM02"]["target"]), ("long", "short"))
        self.assertLess(float(first["SIM03"]["iof"]), float(a["iof"]))
        self.assertEqual(first["SIM03"]["long_rank"], "")  # A < B
        self.assertEqual((first["SIM05"]["cap_rank"], first["SIM12"]["cap_rank"]), ("5", ""))
        boundary = on(self.signals, "2025-04-01")[0]
        self.assertEqual((boundary["month_a"], boundary["month_b"]), ("2025-02", "2024-02"))
        april = {r["symbol"]: r for r in on(self.signals, "2025-04-04")}
        self.assertEqual((april["SIM01"]["month_a"], april["SIM01"]["month_b"]), ("2025-03", "2024-03"))
        self.assertEqual([s for s, r in april.items() if r["in_universe"] == "1"],
                         ["SIM01", "SIM02", "SIM03", "SIM05"])
        self.assertEqual((april["SIM03"]["flow"], april["SIM05"]["mean_b"]), ("", ""))
        self.assertEqual([s for s, r in april.items() if r["iof"]], ["SIM01", "SIM02"])

    def test_ranks_buffer_and_single_sleeve_conflict(self):
        ranked = {r["symbol"]: r for r in on(self.signals, "2025-04-02")}
        self.assertEqual((ranked["SIM02"]["long_rank"], ranked["SIM02"]["target"]), ("2", "long"))
        self.assertEqual((ranked["SIM01"]["short_rank"], ranked["SIM01"]["target"]), ("2", "short"))
        short = next(r for r in on(self.signals, "2025-04-03") if r["target"] == "short")
        self.assertLess(float(short["flow"]), 0)
        self.assertLess(float(short["mean_a"]), float(short["mean_b"]))
        closes = {s: Close("KSE", 100, -1) for s in "GFEDCBA"}
        means = {(m, s): v for m, v in (("2024-12", 10), ("2023-12", 5)) for s in closes}
        targets, audit = select(date(2025, 1, 2), closes, means, {"long": None, "short": None})
        self.assertEqual(targets, {"long": "A", "short": "B"})
        self.assertEqual([r["symbol"] for r in audit if r["in_universe"]], ["A", "B", "C"])

    def test_next_open_and_later_information_cannot_replace_a_pick(self):
        means, closes, auctions = read_inputs(ROOT / "data")
        t, entry, end = sorted(closes)[:3]
        means["2025-03", "SIM01"] = 1  # 신호월의 미완성 시총
        closes[entry] = {s: Close("OTHER", 1, 0) for s in closes[entry]}
        del auctions[entry].prices["SIM01"]
        auctions[entry].borrowable.clear()
        result = simulate(means, {d: closes[d] for d in (t, entry, end)}, auctions)
        self.assertEqual([(r["symbol"], r["target"]) for r in result["signals"] if r["target"]],
                         [("SIM01", "long"), ("SIM02", "short")])
        self.assertEqual([r["status"] for r in result["orders"]], ["no_open", "no_locate"])
        self.assertEqual(result["holdings"], [])
        self.assertEqual(result["daily"][0]["nav_end"], 100_000)

    def test_first_fill_cost_and_netting_across_sleeves(self):
        first, crossed = self.daily[:2]
        self.assertEqual([float(r["filled_qty"]) for r in on(self.orders, "2025-03-25")], [100, -50])
        self.assertEqual([float(first[k]) for k in ("traded", "turnover", "trade_cost", "borrow_fee",
                                                    "gross_pnl", "cash_after", "nav_end")],
                         [20_000, 0.2, 20, 1, 300, 99_979, 100_279])
        holdings = on(self.holdings, "2025-03-26")
        self.assertEqual(sum(float(r["qty"]) < 0 for r in holdings), 2)
        self.assertAlmostEqual(float(crossed["long_value"]), 300)
        self.assertEqual((float(crossed["short_value"]), float(crossed["borrow_fee"])), (0, 0))
        self.assertAlmostEqual(float(crossed["trade_cost"]), 20.0558)

    def test_blocked_and_partial_orders_stale_mark_and_recovery(self):
        failed = on(self.orders, "2025-03-27")
        self.assertEqual([(r["symbol"], r["status"]) for r in failed],
                         [("SIM04", "no_open"), ("SIM03", "no_locate")])
        self.assertEqual(on(self.daily, "2025-03-27")[0]["traded"], "0")
        locked = [r for r in on(self.orders, "2025-04-01") if r["side"] == "long"]
        self.assertEqual([(r["status"], float(r["filled_qty"]), float(r["qty_after"])) for r in locked],
                         [("no_open", 0, 100), ("slot_locked", 0, 0)])
        carried = next(r for r in on(self.holdings, "2025-04-01")
                       if r["sleeve"] == "1" and r["symbol"] == "SIM01")
        self.assertEqual([carried[k] for k in ("qty", "entry_mark", "entry_stale", "end_mark", "end_stale")],
                         ["100", "104", "1", "108", "0"])
        available = sum(float(r["qty"]) for r in on(self.holdings, "2025-04-03") if r["symbol"] == "SIM02")
        partial = next(r for r in on(self.orders, "2025-04-04") if r["symbol"] == "SIM02")
        self.assertEqual(partial["status"], "partial_locate")
        self.assertGreater(available, 0)
        self.assertAlmostEqual(float(partial["filled_qty"]), -available)
        self.assertLess(available, abs(float(partial["target_value"]) / float(partial["open"])))

    def test_partial_exit_keeps_slot_but_no_locate_allows_cover(self):
        books = [{"A": 10}, {"A": -6}, {}, {}, {}]
        auction = Auction(prices={"A": 100, "B": 50})
        orders = refresh(books, 0, current_sides(books[0]), {"long": "B", "short": None}, auction, 1000)
        self.assertEqual([(r["status"], r["filled_qty"]) for r in orders],
                         [("partial_locate", -4), ("slot_locked", 0)])
        self.assertEqual(books[:2], [{"A": 6}, {"A": -6}])
        cover = refresh(books, 1, current_sides(books[1]), {"long": None, "short": None}, auction, 1000)
        self.assertEqual((cover[0]["status"], cover[0]["filled_qty"]), ("filled", 6))
        self.assertEqual(books[:2], [{"A": 6}, {}])

    def test_rebuild_every_interval_from_fills_and_input_prices(self):
        prices = defaultdict(dict)
        for row in read_csv(ROOT / "data" / "sessions.csv"):
            opening = prices[row["date"]]
            if row["open"] and float(row["open"]) > 0:
                opening[row["symbol"]] = float(row["open"])
        days = sorted(prices)
        marks, last = {}, {}
        for day in days:
            last = {**last, **prices[day]}
            marks[day] = last
        cash, previous_nav = 100_000.0, 100_000.0
        book = defaultdict(float)  # (슬리브, 종목)별 체결만 누적
        for i, row in enumerate(self.daily):
            signal, entry, end = days[i:i + 3]
            with self.subTest(entry=entry):
                self.assertEqual([row[k] for k in ("signal_date", "entry_date", "mark_date", "sleeve")],
                                 [signal, entry, end, str(1 + i % 5)])
                self.assertAlmostEqual(float(row["cash_before"]), cash)
                self.assertAlmostEqual(float(row["nav_start"]), previous_nav)
                principal = defaultdict(float)
                for order in on(self.orders, entry):
                    key = order["sleeve"], order["symbol"]
                    self.assertEqual(key[0], row["sleeve"])
                    self.assertAlmostEqual(float(order["qty_before"]), book[key])
                    filled = float(order["filled_qty"])
                    if filled:
                        self.assertEqual(float(order["open"]), prices[entry][key[1]])
                        principal[key[1]] += filled * prices[entry][key[1]]
                    book[key] += filled
                    self.assertAlmostEqual(float(order["qty_after"]), book[key])

                holdings = {(r["sleeve"], r["symbol"]): r for r in on(self.holdings, entry)}
                self.assertEqual(set(holdings), {k for k, q in book.items() if abs(q) > 1e-8})
                net = defaultdict(float)
                for key, h in holdings.items():
                    s = key[1]
                    self.assertAlmostEqual(float(h["qty"]), book[key])
                    for day, prefix in ((entry, "entry"), (end, "end")):
                        self.assertEqual(float(h[prefix + "_mark"]), marks[day][s])
                        self.assertEqual(int(h[prefix + "_stale"]), int(s not in prices[day]))
                    net[s] += book[key]
                traded = sum(abs(v) for v in principal.values())
                long = sum(max(0, q) * marks[entry][s] for s, q in net.items())
                short = sum(max(0, -q) * marks[entry][s] for s, q in net.items())
                fee, borrow = traded * 0.001, short * 0.0001
                cash -= sum(principal.values()) + fee + borrow
                pnl = sum(q * (marks[end][s] - marks[entry][s]) for s, q in net.items())
                nav = cash + sum(q * marks[end][s] for s, q in net.items())
                expected = dict(traded=traded, turnover=traded / previous_nav, trade_cost=fee,
                                long_value=long, short_value=short, borrow_fee=borrow, gross_pnl=pnl,
                                net_pnl=pnl - fee - borrow, cash_after=cash, nav_end=nav,
                                net_return=nav / previous_nav - 1)
                for key, value in expected.items():
                    self.assertAlmostEqual(float(row[key]), value, places=7, msg=key)
                previous_nav = nav
        self.assertEqual(len(self.daily), len(days) - 2)
        compounded = math.prod(1 + float(r["net_return"]) for r in self.daily)
        self.assertAlmostEqual(100_000 * compounded, previous_nav)
        self.assertAlmostEqual(previous_nav, 99_917.11442746855)

    def test_default_cli_reproduces_csv_after_input_reversal(self):
        repo = self.work / "standalone"
        (repo / "data").mkdir(parents=True)
        for name in ("signals.py", "backtest.py", "run_demo.py"):
            shutil.copyfile(ROOT / name, repo / name)
        for path in (ROOT / "data").glob("*.csv"):
            header, *body = path.read_text(encoding="utf-8").splitlines()
            (repo / "data" / path.name).write_text("\n".join([header, *reversed(body)]) + "\n", encoding="utf-8")
        proc = subprocess.run([sys.executable, "run_demo.py"], cwd=repo, check=True,
                              capture_output=True, encoding="utf-8")
        self.assertIn("99,917.11", proc.stdout)
        names = {"signals.csv", "orders.csv", "holdings.csv", "daily.csv"}
        self.assertEqual({p.name for p in (repo / "outputs").iterdir()}, names)
        for name in names:
            self.assertEqual((repo / "outputs" / name).read_bytes(), (self.export / name).read_bytes())
        panel = repo / "data" / "sessions.csv"
        duplicate = panel.read_text(encoding="utf-8").splitlines()[-1]
        with panel.open("a", encoding="utf-8") as stream:
            stream.write(duplicate + "\n")
        with self.assertRaisesRegex(ValueError, "중복"):
            read_inputs(repo / "data")


if __name__ == "__main__":
    unittest.main()
