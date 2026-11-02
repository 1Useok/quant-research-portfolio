"""Build daily news ranks using only information available at the cutoff."""

import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import NamedTuple

KST = timezone(timedelta(hours=9))
OPEN = time(9)
CUTOFF = time(15, 15)
TOP_N = 5


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def words(text):
    return re.findall(r"[가-힣a-z0-9]+", normalize(text))


class BaselineNB(NamedTuple):
    log_prior_odds: float
    word_log_odds: dict[str, float]

    def score(self, headline):
        odds = self.log_prior_odds + sum(self.word_log_odds.get(w, 0.0) for w in words(headline))
        return (1.0 + math.tanh(odds / 2.0)) / 2.0


def train_baseline(examples, first_session):
    """Fit a Laplace-smoothed multinomial NB on previously resolved labels."""
    counts = [Counter(), Counter()]
    documents = [0, 0]
    for row in examples:
        if date.fromisoformat(row["label_end"]) >= first_session:
            continue
        outcome = float(row["synthetic_return"])
        if not math.isfinite(outcome):
            raise ValueError("Training returns must be finite.")
        label = int(outcome > 0)
        counts[label].update(words(row["headline"]))
        documents[label] += 1
    vocabulary = counts[0].keys() | counts[1].keys()
    if not all(documents) or not vocabulary:
        raise ValueError("Training needs text and both return classes before the first session.")
    denominators = [counts[k].total() + len(vocabulary) for k in (0, 1)]
    weights = {}
    for word in vocabulary:
        positive = (counts[1][word] + 1) / denominators[1]
        negative = (counts[0][word] + 1) / denominators[0]
        weights[word] = math.log(positive / negative)
    return BaselineNB(math.log(documents[1] / documents[0]), weights)


class ArticleDecision(NamedTuple):
    article_id: str
    published_kst: str
    symbol: str
    decision: str
    score: float | None


class Signal(NamedTuple):
    session: date
    rank: int
    symbol: str
    article_count: int
    mean_score: float


def build_signals(articles, companies, sessions, model, top_n=TOP_N):
    names = defaultdict(set)
    for company in companies:
        for alias in company["aliases"].split("|"):
            names[normalize(alias)].add(company["symbol"])

    # Compare actual instants, even if input rows use different UTC offsets.
    dated = []
    for row in articles:
        stamp = datetime.fromisoformat(row["published_at"])
        if stamp.tzinfo is None:
            raise ValueError(f"Missing timezone on article {row['article_id']}")
        dated.append((stamp.astimezone(KST), row["article_id"], normalize(row["headline"])))

    seen = set()
    by_day = defaultdict(lambda: defaultdict(list))
    decisions = []
    for stamp, article_id, headline in sorted(dated):
        day = stamp.date()
        matches = {symbol for w in words(headline) for symbol in names.get(w, ())}
        symbol = next(iter(matches)) if len(matches) == 1 else ""
        key = (day, symbol, headline)
        score = None
        if day not in sessions:
            reason = "non_session"
        elif not OPEN <= stamp.time() <= CUTOFF:
            reason = "outside_window"
        elif len(matches) != 1:
            reason = "multi_company" if matches else "unmatched"
        elif key in seen:
            reason = "duplicate"
        else:
            seen.add(key)
            score = model.score(headline)
            by_day[day][symbol].append(score)
            reason = "accepted"
        decisions.append(ArticleDecision(article_id, stamp.isoformat(), symbol, reason, score))

    signals = []
    for day, companies_that_day in sorted(by_day.items()):
        ranked = [(symbol, len(scores), sum(scores) / len(scores))
                  for symbol, scores in companies_that_day.items()]
        ranked.sort(key=lambda item: (-item[2], item[0]))
        for rank, (symbol, count, score) in enumerate(ranked[:top_n], start=1):
            signals.append(Signal(day, rank, symbol, count, score))
    return decisions, signals
