import csv
import hashlib
import io
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, redirect_stdout
from pathlib import Path

from market_store import connect, publish, rollback_latest
from run_demo import DATA, run_demo


class StoreTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.store = self.folder / "test.sqlite"
        self.db = connect(self.store)
        self.addCleanup(self.db.close)
        self.base = publish(self.db, "market", DATA / "market_base.csv")

    def source(self, name, contents):
        path = self.folder / name
        path.write_text(contents, encoding="utf-8")
        return path

    def register_delta(self):
        return publish(self.db, "market", DATA / "market_delta.csv")

    def test_date_bound_by_turnover_and_amounts_converted_once(self):
        feed = DATA / "investor_flow.csv"
        with self.assertRaisesRegex(ValueError, "found 0"):
            publish(self.db, "flows", feed)
        self.register_delta()
        receipt = publish(self.db, "flows", feed)
        self.assertEqual(receipt.sha256, hashlib.sha256(feed.read_bytes()).hexdigest())
        self.assertEqual(receipt.added, 9)
        self.assertEqual(self.db.execute(
            "SELECT session, buy_krw, sell_krw, net_krw FROM flows WHERE symbol='SIM01' AND investor='insurance'"
        ).fetchone(), ("2025-02-04", 700000, 450000, 250000))

    def test_conflict_does_not_publish_other_rows_or_batch(self):
        source = self.source("mixed.csv", "session,symbol,turnover_krw\n"
                             "2025-02-03,SIM99,100\n2025-02-03,SIM01,1\n")
        with self.assertRaisesRegex(ValueError, "Conflicting observation"):
            publish(self.db, "market", source)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM market").fetchone(), (3,))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM batches").fetchone(), (1,))

    def test_partial_overlap_rollback_removes_only_new_observations(self):
        source = self.source("overlap.csv", "session,symbol,turnover_krw\n"
                             "2025-02-03,SIM01,2500000\n2025-02-03,SIM99,100\n")
        result = publish(self.db, "market", source)
        self.assertEqual((result.added, result.duplicates), (1, 1))
        rollback_latest(self.db, result.batch_id)
        rows = self.db.execute("SELECT symbol, batch_id FROM market ORDER BY symbol").fetchall()
        self.assertEqual(rows, [(symbol, self.base.batch_id) for symbol in ("SIM01", "SIM02", "SIM03")])

    def test_cannot_guess_ambiguous_session(self):
        self.register_delta()
        text = (DATA / "market_delta.csv").read_text(encoding="utf-8").replace("02-04", "02-05")
        publish(self.db, "market", self.source("same_amounts.csv", text))
        with self.assertRaisesRegex(ValueError, "found 2"):
            publish(self.db, "flows", DATA / "investor_flow.csv")

    def test_inconsistent_net_and_wrong_anchor_are_rejected(self):
        self.register_delta()
        original = (DATA / "investor_flow.csv").read_text(encoding="utf-8")
        for text in (original.replace("70,45,25", "70,45,26"), original.replace("275,", "2750000,")):
            with self.assertRaises(ValueError):
                publish(self.db, "flows", self.source("bad.csv", text))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM flows").fetchone(), (0,))

    def test_replay_and_rollback_preserve_provenance_across_restart(self):
        delta = self.register_delta()
        first = publish(self.db, "flows", DATA / "investor_flow.csv")
        with closing(connect(self.store)) as second:
            replay = publish(second, "flows", DATA / "investor_flow.csv")
            self.assertEqual((replay.batch_id, replay.added, replay.duplicates), (None, 0, 9))
            with self.assertRaises(ValueError):
                rollback_latest(second, delta.batch_id)
            rollback_latest(second, first.batch_id)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM flows").fetchone(), (0,))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM market").fetchone(), (6,))
        restored = publish(self.db, "flows", DATA / "investor_flow.csv")
        self.assertGreater(restored.batch_id, first.batch_id)
        self.assertEqual(restored.sha256, first.sha256)
        self.assertEqual(self.db.execute("SELECT active FROM batches ORDER BY id").fetchall(),
                         [(1,), (1,), (0,), (1,)])

    def test_two_writers_publish_the_same_delta_once(self):
        def submit(_):
            with closing(connect(self.store)) as writer:
                return publish(writer, "market", DATA / "market_delta.csv").added

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(submit, range(2))), [0, 3])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM batches").fetchone(), (2,))

    def test_demo_exports_are_repeatable(self):
        out = self.folder / "demo"
        with redirect_stdout(io.StringIO()):
            run_demo(out)
        first = (out / "run_audit.csv").read_bytes()
        with redirect_stdout(io.StringIO()):
            run_demo(out)
        self.assertEqual(first, (out / "run_audit.csv").read_bytes())
        with (out / "investor_flow.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 9)
        self.assertTrue(all(int(r["buy_krw"]) - int(r["sell_krw"]) == int(r["net_krw"]) for r in rows))


if __name__ == "__main__":
    unittest.main()
