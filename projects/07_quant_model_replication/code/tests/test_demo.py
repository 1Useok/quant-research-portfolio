import csv
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

from data.make_sample import build
from replica import FACTORS, K, fit_asof, load_market, macro_at, make_labels
from run_demo import run

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def read(path, **match):
    with path.open(encoding="utf-8", newline="") as stream:
        return [r for r in csv.DictReader(stream) if all(r[k] == v for k, v in match.items())]


def rewrite(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class ReplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(dir=ROOT)
        cls.addClassCleanup(tmp.cleanup)
        cls.work = Path(tmp.name)
        cls.base = cls.work / "baseline"
        run(DATA, cls.base)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=self.work)
        self.addCleanup(tmp.cleanup)
        self.scratch = Path(tmp.name)
        self.data = self.scratch / "data"
        self.data.mkdir()
        self.out = self.scratch / "recheck"

    def copy_inputs(self):
        for src in DATA.glob("*.csv"):
            shutil.copyfile(src, self.data / src.name)

    def test_offline_cli_regeneration_and_input_order(self):
        build(self.data)
        for src in DATA.glob("*.csv"):
            self.assertEqual(src.read_bytes(), (self.data / src.name).read_bytes())
        for module in ("run_demo.py", "replica.py"):
            shutil.copyfile(ROOT / module, self.scratch / module)
        cmd = [sys.executable, "-B", "run_demo.py"]
        first = subprocess.check_output(cmd, cwd=self.scratch)
        for table in self.data.glob("*.csv"):
            rewrite(table, read(table)[::-1])
        again = subprocess.check_output(cmd + ["--out", str(self.out)], cwd=self.scratch)
        self.assertEqual(first, again)
        expected = {"labels.csv", "weights.csv", "rankings.csv", "overlap.csv", "returns.csv"}
        for folder in (self.scratch / "outputs", self.out):
            self.assertEqual({p.name for p in folder.iterdir()}, expected)
            for name in expected:
                self.assertEqual((folder / name).read_bytes(), (self.base / name).read_bytes())
                dates = [r["signal_date"] for r in read(folder / name)]
                self.assertEqual(dates, sorted(dates))

    def test_releases_missing_factors_and_ties(self):
        books, events, _ = load_market(DATA)
        day = date(2024, 5, 10)
        latest = macro_at(events, day)
        self.assertEqual((latest.observed_on, latest.cycle), (date(2024, 5, 1), -1))
        self.assertEqual(macro_at(events, date(2024, 5, 13)).observed_on, date(2024, 5, 8))
        self.assertNotIn("F07", books[day])                 # 다음 월요일에 도착
        self.assertNotIn("F04", books[date(2024, 3, 22)])  # 세 팩터 중 두 개 공란
        table = {r["symbol"]: r for r in read(self.base / "rankings.csv",
                                              signal_date=str(day), mode="replay")}
        self.assertEqual(table["F03"]["value_rank"], table["F06"]["value_rank"])
        self.assertAlmostEqual(float(table["F03"]["value_rank"]), 2.5 / 6)
        self.assertEqual(float(table["F05"]["trend_rank"]), 0.5)
        self.assertEqual(float(table["F05"]["score"]), 100 * (0.15 + 0.60 + 0.25 / 2))

    def test_factor_label_from_closes_and_maturity_boundary(self):
        books, events, closes = load_market(DATA)
        labels = make_labels(books, events, closes)
        day = date(2024, 5, 10)
        label = next(r for r in labels if r.signal == day and r.factor == "value")
        self.assertEqual((label.entry, label.end), (date(2024, 5, 13), date(2024, 5, 20)))
        self.assertEqual(label.leaders, ("F05", "F01"))
        ids = "F01 F02 F03 F04 F05 F06 F08".split()
        moves = {s: 100 * (closes[label.end, s] / closes[label.entry, s] - 1) for s in ids}
        self.assertAlmostEqual(label.excess_pp, (moves["F05"] + moves["F01"]) / 2 - mean(moves.values()))
        # 종료일 당일은 훈련에서 제외하고 다음 날부터 이 라벨을 허용한다.
        fits, _ = fit_asof(labels, label.end, macro_at(events, label.end))
        after = label.end + timedelta(days=1)
        newer, _ = fit_asof(labels, after, macro_at(events, after))
        self.assertLess(fits["value"].last_label.end, label.end)
        self.assertEqual(newer["value"].last_label, label)
        self.assertEqual(newer["value"].train_n, fits["value"].train_n + 1)

    def test_forecasts_from_mature_history_only(self):
        labels = read(self.base / "labels.csv")
        releases = read(DATA / "macro.csv")
        for r in labels:
            known = [m for m in releases if m["available_on"] <= r["signal_date"] and m["cycle"]]
            latest = max(known, key=lambda m: (m["observed_on"], m["available_on"]))
            self.assertEqual((r["macro_observed_on"], r["macro_available_on"], float(r["cycle"])),
                             (latest["observed_on"], latest["available_on"], float(latest["cycle"])))
        for ref in read(DATA / "reference.csv"):
            day = ref["signal_date"]
            weights = read(self.base / "weights.csv", signal_date=day)
            masses = {}
            for w in weights:
                self.assertLessEqual(w["macro_available_on"], day)
                history = [r for r in labels if r["factor"] == w["factor"]
                           and r["label_end"] < day and r["excess_pp"] and r["cycle"]]
                n = len(history)
                self.assertEqual(n, int(w["train_n"]))
                self.assertEqual(w["last_label_end"], max(r["label_end"] for r in history))
                self.assertEqual(w["last_train_signal"], max(r["signal_date"] for r in history))
                x = [float(r["cycle"]) for r in history]
                y = [float(r["excess_pp"]) for r in history]
                xy = sum(a * b for a, b in zip(x, y))
                slope = (n * xy - sum(x) * sum(y)) / (n * (1 + sum(a * a for a in x)) - sum(x) ** 2)
                estimate = (sum(y) - slope * sum(x)) / n + slope * float(w["cycle"])
                self.assertAlmostEqual(estimate, float(w["forecast_excess_pp"]), places=8)
                masses[w["factor"]] = math.exp(estimate)
            for w in weights:
                self.assertAlmostEqual(masses[w["factor"]] / sum(masses.values()),
                                       float(w["predicted_weight"]), places=8)

    def test_fixed_reference_from_calendar_and_raw_factor_grades(self):
        rotation = [(60, 25, 15), (15, 60, 25), (25, 15, 60)]
        for ref in read(DATA / "reference.csv"):
            day = date.fromisoformat(ref["signal_date"])
            weights = rotation[day.isocalendar().week % 3]
            self.assertEqual(tuple(int(ref[f + "_pct"]) for f in FACTORS), weights)
            observed = str(day - timedelta(days=1))
            desk_scores = {}
            for r in read(DATA / "factors.csv", observed_on=observed):
                if r["available_on"] > str(day) or sum(bool(r[f]) for f in FACTORS) < 2:
                    continue
                grades = [sum(int(r[f]) >= edge for edge in (20, 40, 60, 80)) if r[f] else 2
                          for f in FACTORS]
                desk_scores[r["symbol"]] = sum(w * g for w, g in zip(weights, grades))
            top = sorted(desk_scores, key=lambda s: (-desk_scores[s], s))[:K]
            self.assertEqual(top, [ref[f"pick_{i}"] for i in (1, 2, 3)])

    def test_changing_reference_cannot_change_predictions(self):
        self.copy_inputs()
        refs = read(self.data / "reference.csv")
        refs[0].update(value_pct="0", quality_pct="0", trend_pct="100",
                       pick_1="F01", pick_2="F02", pick_3="F03")
        rewrite(self.data / "reference.csv", refs)
        run(self.data, self.out)
        for name in ("rankings.csv", "returns.csv"):
            self.assertEqual(read(self.base / name, mode="predicted"), read(self.out / name, mode="predicted"))
        for before, after in zip(read(self.base / "weights.csv"), read(self.out / "weights.csv"), strict=True):
            self.assertEqual({k: v for k, v in before.items() if k != "published_weight"},
                             {k: v for k, v in after.items() if k != "published_weight"})
        day = refs[0]["signal_date"]
        self.assertNotEqual(read(self.base / "overlap.csv", signal_date=day),
                            read(self.out / "overlap.csv", signal_date=day))
        self.assertNotEqual(read(self.base / "rankings.csv", signal_date=day, mode="replay"),
                            read(self.out / "rankings.csv", signal_date=day, mode="replay"))

    def test_future_data_and_missing_close_leave_signal_intact(self):
        self.copy_inputs()
        edits = [("macro.csv", {"observed_on": "2024-05-08"}, {"cycle": "50"}),
                 ("factors.csv", {"observed_on": "2024-05-09", "symbol": "F07"}, {"value": "999"}),
                 ("closes.csv", {"session": "2024-05-13", "symbol": "F05"}, {"close": ""})]
        for name, match, change in edits:
            rows = read(self.data / name)
            row = next(r for r in rows if all(r[k] == v for k, v in match.items()))
            row.update(change)
            rewrite(self.data / name, rows)
        run(self.data, self.out)
        day = "2024-05-10"
        for name in ("weights.csv", "rankings.csv"):
            self.assertEqual(read(self.base / name, signal_date=day), read(self.out / name, signal_date=day))
        for row in read(self.out / "overlap.csv", signal_date=day):
            original, = read(self.base / "overlap.csv", signal_date=day, pair=row["pair"])
            self.assertEqual(row["common_symbols"], original["common_symbols"])
        self.assertTrue(all(r["gross_return_pct"] == "" for r in read(self.out / "returns.csv", signal_date=day)))
        for signal in ("2024-05-03", day):
            label, = read(self.out / "labels.csv", signal_date=signal, factor="value")
            self.assertEqual(label["excess_pp"], "")
        before, = read(self.base / "weights.csv", signal_date="2024-05-17", factor="value")
        after, = read(self.out / "weights.csv", signal_date="2024-05-17", factor="value")
        self.assertEqual(int(after["train_n"]), int(before["train_n"]) - 1)

    def test_scores_orders_intersections_and_peaks(self):
        checks = read(self.base / "overlap.csv")
        for ref in read(DATA / "reference.csv"):
            day = ref["signal_date"]
            orders = {"reference": [ref[f"pick_{i}"] for i in (1, 2, 3)]}
            weights = read(self.base / "weights.csv", signal_date=day)
            for mode, key in (("predicted", "predicted_weight"), ("replay", "published_weight")):
                ranked = read(self.base / "rankings.csv", signal_date=day, mode=mode)
                for i, row in enumerate(ranked, 1):
                    score = sum(float(w[key]) * float(row[w["factor"] + "_rank"]) * 100 for w in weights)
                    self.assertAlmostEqual(float(row["score"]), score, places=7)
                    self.assertEqual(int(row["rank"]), i)
                    self.assertAlmostEqual(float(row["holding_weight"]), 1 / K if i <= K else 0)
                self.assertEqual(ranked, sorted(ranked, key=lambda r: (-float(r["score"]), r["symbol"])))
                orders[mode] = [r["symbol"] for r in ranked[:K]]
            for row in (r for r in checks if r["signal_date"] == day):
                a, b = (orders[mode] for mode in row["pair"].split("/"))
                self.assertEqual((row["left_order"].split(), row["right_order"].split()), (a, b))
                common = set(a) & set(b)
                self.assertEqual(row["common_symbols"].split(), sorted(common))
                self.assertEqual(int(row["overlap_n"]), len(common))
                self.assertEqual(int(row["same_rank_n"]), sum(a.index(s) == b.index(s) for s in common))
        for pair, totals in (("reference/replay", (21, 13)), ("reference/predicted", (20, 7)),
                             ("replay/predicted", (19, 12))):
            rows = [r for r in checks if r["pair"] == pair]
            self.assertEqual(len(rows), 8)
            self.assertEqual(tuple(sum(int(r[k]) for r in rows) for k in ("overlap_n", "same_rank_n")), totals)
            peak = max(int(r["overlap_n"]) for r in rows)
            for r in rows:
                self.assertEqual(r["is_peak"] == "1", int(r["overlap_n"]) == peak)

    def test_post_trade_returns_and_replication_measure_different_things(self):
        prices = {(r["session"], r["symbol"]): int(r["close"]) for r in read(DATA / "closes.csv")}
        for r in read(self.base / "returns.csv"):
            day = date.fromisoformat(r["signal_date"])
            buy, sell = r["entry_date"], r["exit_date"]
            self.assertEqual((buy, sell), (str(day + timedelta(days=3)), str(day + timedelta(days=10))))
            ids = r["holdings"].split()
            ranked = read(self.base / "rankings.csv", signal_date=str(day), mode=r["mode"])
            self.assertEqual(ids, [row["symbol"] for row in ranked[:K]])
            if day == date(2024, 6, 28):
                self.assertEqual(r["gross_return_pct"], "")
            else:
                actual = 100 * (mean(prices[sell, s] / prices[buy, s] for s in ids) - 1)
                self.assertAlmostEqual(actual, float(r["gross_return_pct"]), places=8)
        day = "2024-05-17"
        replay, predicted = read(self.base / "returns.csv", signal_date=day)
        hits = {r["pair"]: int(r["overlap_n"]) for r in read(self.base / "overlap.csv", signal_date=day)}
        self.assertGreater(hits["reference/replay"], hits["reference/predicted"])
        self.assertLess(float(replay["gross_return_pct"]), float(predicted["gross_return_pct"]))


if __name__ == "__main__":
    unittest.main()
