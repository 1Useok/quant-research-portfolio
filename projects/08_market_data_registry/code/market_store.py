"""Validated, append-only market and investor-flow observations in SQLite."""

import csv
import hashlib
import io
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path


MARKET_COLUMNS = ("session", "symbol", "turnover_krw")
FLOW_COLUMNS = ("symbol", "investor", "market_turnover_10k", "buy_10k", "sell_10k", "net_10k")


@dataclass(frozen=True)
class Receipt:
    batch_id: int | None
    added: int
    duplicates: int
    sha256: str


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=10)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY,
            domain TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            rows_added INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS market (
            session TEXT NOT NULL,
            symbol TEXT NOT NULL,
            turnover_krw INTEGER NOT NULL,
            batch_id INTEGER NOT NULL REFERENCES batches(id),
            PRIMARY KEY (session, symbol)
        );
        CREATE TABLE IF NOT EXISTS flows (
            session TEXT NOT NULL,
            symbol TEXT NOT NULL,
            investor TEXT NOT NULL,
            buy_krw INTEGER NOT NULL,
            sell_krw INTEGER NOT NULL,
            net_krw INTEGER NOT NULL,
            batch_id INTEGER NOT NULL REFERENCES batches(id),
            PRIMARY KEY (session, symbol, investor),
            FOREIGN KEY (session, symbol) REFERENCES market(session, symbol)
        );
    """)
    return db


def read_source(path, columns):
    payload = path.read_bytes()
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
    if reader.fieldnames != list(columns):
        raise ValueError("Unexpected CSV columns")
    rows = list(reader)
    if not rows or any(None in row or any(not (v or "").strip() for v in row.values()) for row in rows):
        raise ValueError("Empty or incomplete CSV")
    return rows, hashlib.sha256(payload).hexdigest()


def market_records(rows):
    for row in rows:
        session = row["session"]
        turnover = int(row["turnover_krw"])
        if date.fromisoformat(session).isoformat() != session or turnover < 0:
            raise ValueError("Invalid market session or turnover")
        yield (session, row["symbol"].strip()), (turnover,)


def flow_records(db, rows):
    # The flow feed has no trusted session. The matched notional comes from the
    # independent daily market file, not from an import timestamp.
    anchors = {}
    parsed = []
    for row in rows:
        symbol = row["symbol"].strip()
        turnover, buy, sell, net = (int(row[k]) * 10_000 for k in FLOW_COLUMNS[2:])
        if min(turnover, buy, sell) < 0 or max(buy, sell) > turnover or net != buy - sell:
            raise ValueError(f"Inconsistent investor amounts for {symbol}")
        if anchors.setdefault(symbol, turnover) != turnover:
            raise ValueError(f"Conflicting market anchors for {symbol}")
        parsed.append((symbol, row["investor"].strip(), buy, sell, net))

    matches = [
        {r[0] for r in db.execute("SELECT session FROM market WHERE symbol=? AND turnover_krw=?", anchor)}
        for anchor in anchors.items()
    ]
    sessions = set.intersection(*matches)
    if len(sessions) != 1:
        raise ValueError(f"Expected exactly one matching market session, found {len(sessions)}")
    session, = sessions
    for symbol, investor, buy, sell, net in parsed:
        yield (session, symbol, investor), (buy, sell, net)


def publish(db, domain: str, source: Path) -> Receipt:
    if domain not in {"market", "flows"}:
        raise ValueError(f"Unknown domain {domain}")
    rows, digest = read_source(source, MARKET_COLUMNS if domain == "market" else FLOW_COLUMNS)
    with db:
        db.execute("BEGIN IMMEDIATE")
        if domain == "market":
            records = market_records(rows)
            lookup = "SELECT turnover_krw FROM market WHERE session=? AND symbol=?"
            insert = "INSERT INTO market VALUES (?, ?, ?, ?)"
        else:
            records = flow_records(db, rows)
            lookup = "SELECT buy_krw, sell_krw, net_krw FROM flows WHERE session=? AND symbol=? AND investor=?"
            insert = "INSERT INTO flows VALUES (?, ?, ?, ?, ?, ?, ?)"

        pending = {}
        duplicates = 0
        for key, amounts in records:
            previous = pending.get(key)
            if previous is None:
                previous = db.execute(lookup, key).fetchone()
            if previous is None:
                pending[key] = amounts
            elif previous != amounts:
                raise ValueError(f"Conflicting observation at {key}")
            else:
                duplicates += 1
        if not pending:
            return Receipt(None, 0, duplicates, digest)

        batch_id = db.execute(
            "INSERT INTO batches(domain, sha256, rows_added) VALUES (?, ?, ?)", (domain, digest, len(pending))
        ).lastrowid
        db.executemany(insert, ((*key, *amounts, batch_id) for key, amounts in pending.items()))
        return Receipt(batch_id, len(pending), duplicates, digest)


def rollback_latest(db, batch_id: int):
    """Undo one active publication, retaining its provenance in the batch table."""
    with db:
        db.execute("BEGIN IMMEDIATE")
        latest = db.execute("SELECT id, domain FROM batches WHERE active=1 ORDER BY id DESC LIMIT 1").fetchone()
        if latest is None or latest[0] != batch_id:
            raise ValueError("Rollback requires the latest active batch id")
        table = "market" if latest[1] == "market" else "flows"
        db.execute(f"DELETE FROM {table} WHERE batch_id=?", (batch_id,))
        db.execute("UPDATE batches SET active=0 WHERE id=?", (batch_id,))
