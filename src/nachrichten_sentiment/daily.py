from __future__ import annotations

from datetime import date

from nachrichten_sentiment.models import Article, DailyRow
from nachrichten_sentiment.timeutil import expected_batch_ids_for_berlin_day


def _class_counts(items: list[Article]) -> tuple[int, int, int, int, float | None]:
    """Positiv, neutral, negativ, ohne Wert und Mittelwert über die übergebenen Artikel."""
    positive = sum(1 for item in items if item.sentiment_label == "positive")
    neutral = sum(1 for item in items if item.sentiment_label == "neutral")
    negative = sum(1 for item in items if item.sentiment_label == "negative")
    without = sum(1 for item in items if item.sentiment is None)
    scores = [item.sentiment for item in items if item.sentiment is not None]
    mean = (sum(scores) / len(scores)) if scores else None
    return positive, neutral, negative, without, mean


CANDLE_DIGITS = 4


def _candle(items: list[Article]) -> tuple[float, float, float, float, int] | None:
    """Kerze aus den Stimmungs-Mittelwerten je 15-Minuten-Satz, chronologisch nach batch_id."""
    by_batch: dict[str, list[float]] = {}
    for item in items:
        if item.sentiment is not None:
            by_batch.setdefault(item.batch_id, []).append(item.sentiment)
    if not by_batch:
        return None
    means = [round(sum(v) / len(v), CANDLE_DIGITS) for _, v in sorted(by_batch.items())]
    return (means[0], max(means), min(means), means[-1], len(means))


def aggregate_daily(
    articles: list[Article],
    day: date,
    processed_batch_ids: set[str],
    missing_at_source: set[str] | frozenset[str] = frozenset(),
) -> DailyRow:
    day_key = day.isoformat()
    of_day = [item for item in articles if item.day_berlin == day_key]
    # Standard-Zählweise: Klassen, Werte ohne Stimmung und Mittelwert nur über Nicht-Duplikate
    # (eine Meldung je Cluster). Die *_all-Felder zählen alle URL-eindeutigen Artikel inkl. Nahduplikate.
    distinct = [item for item in of_day if not item.is_near_duplicate]
    positive, neutral, negative, without, mean = _class_counts(distinct)
    positive_all, neutral_all, negative_all, without_all, mean_all = _class_counts(of_day)
    expected = set(expected_batch_ids_for_berlin_day(day))
    coverage = "complete" if expected <= processed_batch_ids else "gap"
    # "Quelle fehlt" nur, wenn jeder nicht verarbeitete Satz des Tages bei GDELT dauerhaft fehlt.
    unprocessed = expected - processed_batch_ids
    gap_reason = "source_missing" if unprocessed and unprocessed <= missing_at_source else None
    return DailyRow(
        date=day_key,
        count_unique_url=len(of_day),
        count_after_near_dup_collapse=len(distinct),
        count_positive=positive,
        count_neutral=neutral,
        count_negative=negative,
        count_without_sentiment=without,
        sentiment_mean=mean,
        coverage=coverage,
        gap_reason=gap_reason,
        count_positive_all=positive_all,
        count_neutral_all=neutral_all,
        count_negative_all=negative_all,
        count_without_sentiment_all=without_all,
        sentiment_mean_all=mean_all,
        ohlc=_candle(distinct),
        ohlc_all=_candle(of_day),
    )
