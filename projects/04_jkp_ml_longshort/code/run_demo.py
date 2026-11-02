"""Run the synthetic JKP research-to-paper-target pipeline."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from data_pipeline import build_panel, read_inputs
from model import annual_predictions, build_labels
from portfolio import form_targets, realized_returns

ROOT = Path(__file__).resolve().parent


def run(data, as_of=None):
    calendar, market, accounts, audit, duplicates = read_inputs(data, as_of)
    panel, monthly = build_panel(calendar, market, accounts)
    labels = build_labels(monthly)
    predictions, fits = annual_predictions(panel, labels)
    targets = form_targets(predictions)
    returns = realized_returns(targets, market, calendar)
    cutoff = calendar.signal_eom.max()
    latest = targets.loc[targets.signal_eom.eq(cutoff)].copy()
    if latest.empty:
        raise ValueError("No targets for the declared snapshot date.")
    audit["snapshot_eom"] = cutoff
    tables = {"input_audit": audit, "feature_panel": panel, "labels": labels, "annual_fits": fits,
              "predictions": predictions, "target_weights": targets, "backtest": returns,
              "latest_paper_targets": latest}
    return cutoff.date().isoformat(), tables, duplicates


def publish(output, snapshot, tables):
    """Expose all files together, and reuse a byte-identical completed run."""
    output.mkdir(parents=True, exist_ok=True)
    destination = output / snapshot
    with TemporaryDirectory(dir=output) as scratch:
        stage = Path(scratch) / "complete"
        stage.mkdir()
        for name, table in tables.items():
            table.to_csv(stage / f"{name}.csv", index=False, lineterminator="\n")
        try:
            stage.rename(destination)
        except OSError:
            if not destination.is_dir():
                raise
            expected = {f.name for f in stage.iterdir()}
            if expected != {f.name for f in destination.iterdir()} or any(
                    (stage / name).read_bytes() != (destination / name).read_bytes() for name in expected):
                raise FileExistsError(f"A different snapshot already exists at {destination}")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs")
    parser.add_argument("--as-of", help="Completed synthetic month-end, e.g. 2024-11-30")
    args = parser.parse_args()
    snapshot, tables, duplicates = run(args.data, args.as_of)
    dest = publish(args.out, snapshot, tables)
    latest = tables["latest_paper_targets"]
    print(f"Synthetic snapshot {snapshot} | {len(tables['feature_panel'])} stock-month rows | "
          f"{duplicates} identical input overlaps")
    print(f"{(tables['annual_fits'].status == 'trained').sum()} annual models | "
          f"{len(tables['backtest'])} completed holding months")
    print(latest[["effective_date", "security_id", "side", "weight"]].to_string(index=False))
    print(f"CSV output: {dest}")


if __name__ == "__main__":
    main()
