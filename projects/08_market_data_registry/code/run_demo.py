"""Publish two market days, replay a flow feed, and demonstrate a clean rollback."""

import argparse
import csv
import os
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from market_store import connect, publish, rollback_latest


DATA = Path(__file__).resolve().parent / "data"


def write_csv(path, headers, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)


def run_demo(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    # Build the demonstration from scratch in a private SQLite file on every run.
    with TemporaryDirectory(dir=out) as temp:
        stage = Path(temp)
        steps = []
        with closing(connect(stage / "sample_store.sqlite")) as db:
            def register(label, domain, name):
                receipt = publish(db, domain, DATA / name)
                steps.append((label, receipt.batch_id, receipt.added, receipt.duplicates))
                return receipt

            register("base", "market", "market_base.csv")
            register("delta", "market", "market_delta.csv")
            first = register("flow", "flows", "investor_flow.csv")
            replay = register("replay", "flows", "investor_flow.csv")
            rollback_latest(db, first.batch_id)
            steps.append(("rollback", first.batch_id, 0, 0))
            register("republish", "flows", "investor_flow.csv")
            market_count = db.execute("SELECT COUNT(*) FROM market").fetchone()[0]
            flow_count = db.execute("SELECT COUNT(*) FROM flows").fetchone()[0]
            for filename, query in (
                ("registry.csv", "SELECT * FROM batches ORDER BY id"),
                ("market.csv", "SELECT * FROM market ORDER BY session, symbol"),
                ("investor_flow.csv", "SELECT * FROM flows ORDER BY session, symbol, investor"),
            ):
                cursor = db.execute(query)
                write_csv(stage / filename, [column[0] for column in cursor.description], cursor)
        write_csv(stage / "run_audit.csv", ("step", "batch_id", "inserted", "duplicates"), steps)
        for artifact in sorted(stage.iterdir()):
            os.replace(artifact, out / artifact.name)
    print(f"Market rows {market_count} | investor flow rows {flow_count} | replay duplicates {replay.duplicates}")
    print(f"Registry, signed investor amounts and replay audit in {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("outputs"))
    run_demo(parser.parse_args().out)
