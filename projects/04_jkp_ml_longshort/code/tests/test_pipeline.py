import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from data_pipeline import FEATURES, KEY, read_inputs
from model import RF_MONTHLY
from portfolio import realized_returns
from run_demo import publish, run

DATA = Path(__file__).resolve().parents[1] / "data"


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.date, cls.tables, cls.overlap = run(DATA)
        cls.calendar, cls.market, cls.accounts, _, _ = read_inputs(DATA)

    def test_only_registered_nonconflicting_observations_enter_the_snapshot(self):
        self.assertEqual(self.overlap, 1)
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "data"
            shutil.copytree(DATA, copy)
            registry = pd.read_csv(copy / "registry.csv")
            pd.concat([registry, registry.tail(1)]).to_csv(copy / "registry.csv", index=False)
            (copy / "unregistered.csv").write_text("ignore this uncommitted batch", encoding="utf-8")
            _, market, _, _, overlap = read_inputs(copy)
            assert_frame_equal(self.market, market)
            self.assertEqual(overlap, 18)
            delta = pd.read_csv(copy / "market_delta.csv")
            delta.loc[0, "last_close"] += 1
            delta.to_csv(copy / "market_delta.csv", index=False)
            with self.assertRaisesRegex(ValueError, "Conflicting market"):
                read_inputs(copy)
        with self.assertRaisesRegex(ValueError, "No registered"):
            read_inputs(DATA, "2025-01-31")

    def test_report_lags_and_four_characteristics_from_source_accounts(self):
        panel = self.tables["feature_panel"]
        sec = panel[panel.security_id == "SIM12"].set_index("signal_eom")
        self.assertEqual(sec.loc["2024-03-31", "annual_period"], pd.Timestamp("2022-12-31"))
        self.assertEqual(sec.loc["2024-04-30", "annual_period"], pd.Timestamp("2023-12-31"))
        self.assertEqual(sec.loc["2024-11-30", "quarter_period"], pd.Timestamp("2024-06-30"))
        row = sec.loc["2024-12-31"]
        statements = self.accounts[self.accounts.security_id == "SIM12"]
        annual = statements[statements.frequency == "A"].set_index("fiscal_end")
        quarter = statements[statements.frequency == "Q"].set_index("fiscal_end")
        prices = self.market[self.market.security_id == "SIM12"].set_index("signal_eom")
        current = prices.loc["2024-12-31"]
        expected = [annual.loc["2023-12-31", "book_equity"] / (current.last_close * current.shares),
                    annual.loc["2023-12-31", "assets"] / annual.loc["2022-12-31", "assets"] - 1,
                    quarter.loc["2024-09-30", "quarter_income"] / quarter.loc["2024-06-30", "assets"],
                    prices.loc["2024-11-30", "last_close"] / prices.loc["2024-06-30", "last_close"] - 1]
        np.testing.assert_allclose(row[FEATURES].to_numpy(dtype=float), expected)
        self.assertFalse(panel.duplicated(KEY).any())
        self.assertTrue((panel.signal_eom < panel.effective_date).all())

    def test_labels_and_training_cutoffs_are_separate_from_score_eligibility(self):
        labels = self.tables["labels"].set_index(KEY)
        panel = self.tables["feature_panel"]
        keys = panel.loc[panel.signal_eom.eq("2023-12-31") & panel.security_id.eq("SIM12"), KEY]
        label = labels.loc[tuple(keys.iloc[0])]
        prices = self.market[self.market.security_id == "SIM12"].set_index("signal_eom").sort_index()
        returns = prices.loc["2023-12-31":"2024-12-31", "last_close"].pct_change().dropna() - RF_MONTHLY
        expected = int(np.sqrt(12) * returns.mean() / returns.std(ddof=1) >= 0.5)
        self.assertEqual((label.target, label.label_end), (expected, pd.Timestamp("2024-12-31")))
        fits = self.tables["annual_fits"].query("status == 'trained'")
        self.assertTrue((fits.last_label_end <= fits.training_cutoff).all())
        latest = self.tables["latest_paper_targets"].set_index(KEY)
        self.assertTrue(labels.loc[latest.index, "target"].isna().all())
        self.assertEqual(set(latest.index.get_level_values("effective_date")), {pd.Timestamp("2025-01-02")})
        self.assertFalse({"target", "label_end", "monthly_return"}.intersection(panel.columns))

    def test_later_batch_does_not_change_earlier_scores_or_portfolios(self):
        _, old, overlaps = run(DATA, "2024-11-30")
        self.assertEqual(overlaps, 0)
        for name in ("feature_panel", "predictions", "target_weights"):
            full = self.tables[name]
            previous = full[full.signal_eom <= pd.Timestamp("2024-11-30")]
            assert_frame_equal(old[name].sort_values(KEY).reset_index(drop=True),
                               previous.sort_values(KEY).reset_index(drop=True), check_exact=True)
        full = self.tables["backtest"].iloc[:len(old["backtest"])]
        assert_frame_equal(old["backtest"], full, check_exact=True)

    def test_next_open_execution_costs_and_drifted_turnover(self):
        targets = self.tables["target_weights"]
        groups = targets.groupby("effective_date").weight
        np.testing.assert_allclose(groups.sum(), 0)
        np.testing.assert_allclose(groups.apply(lambda w: w.abs().sum()), 1)
        track = self.tables["backtest"]
        first, second = track.iloc[0], track.iloc[1]
        p = self.market.pivot(index="signal_eom", columns="security_id", values="first_open")
        p.index = self.calendar.set_index("signal_eom").first_session.reindex(p.index).to_numpy()
        start_w = targets[targets.effective_date == first.entry].set_index("security_id").weight
        end_assets = start_w * (p.loc[first.exit, start_w.index] / p.loc[first.entry, start_w.index])
        expected_net = end_assets.sum() - start_w.sum() - 0.001 - 0.5 * 0.02 * (first.exit-first.entry).days / 365
        self.assertAlmostEqual(first.net_return, expected_net)
        next_w = targets[targets.effective_date == second.entry].set_index("security_id").weight
        turnover = next_w.subtract(end_assets / (1 + expected_net), fill_value=0).abs().sum()
        self.assertAlmostEqual(second.turnover, turnover)
        self.assertAlmostEqual(track.net_nav.iloc[-1], (1 + track.net_return).prod())
        self.assertLess(track.exit.max(), self.tables["latest_paper_targets"].effective_date.min())
        # A missing selected execution price must surface, not silently remove that name.
        bad_market = self.market.copy()
        period = self.calendar.loc[self.calendar.first_session.eq(first.exit), "signal_eom"].iloc[0]
        mask = bad_market.security_id.eq(start_w.index[0]) & bad_market.signal_eom.eq(period)
        bad_market.loc[mask, "first_open"] = np.nan
        with self.assertRaisesRegex(ValueError, "opening price"):
            realized_returns(targets, bad_market, self.calendar)

    def test_snapshot_publish_is_repeatable_and_detects_an_existing_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = publish(Path(tmp), self.date, self.tables)
            self.assertEqual(dest, publish(Path(tmp), self.date, self.tables))
            evidence = dest / "backtest.csv"
            evidence.write_text("independent edit", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                publish(Path(tmp), self.date, self.tables)
            self.assertEqual(evidence.read_text(encoding="utf-8"), "independent edit")


if __name__ == "__main__":
    unittest.main()
