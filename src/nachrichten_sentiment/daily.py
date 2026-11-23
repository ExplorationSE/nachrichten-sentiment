from __future__ import annotations

from datetime import date

from nachrichten_sentiment.models import Article, DailyRow
from nachrichten_sentiment.timeutil import expected_batch_ids_for_berlin_day


def aggregate_daily(
    articles: list[Article],
    day: date,
    processed_batch_ids: set[str],
    missing_at_source: set[str] | frozenset[str] = frozenset(),
) -> DailyRow:
    day_key = day.isoformat()
    of_day = [item for item in articles if item.day_berlin == day_key]
    positives = [item for item in of_day if item.sentiment_label == "positive"]
    neutrals = [item for item in of_day if item.sentiment_label == "neutral"]
    negatives = [item for item in of_day if item.sentiment_label == "negative"]
    missing = [item for item in of_day if item.sentiment is None]
    scores = [item.sentiment for item in of_day if item.sentiment is not None]
    expected = set(expected_batch_ids_for_berlin_day(day))
    coverage = "complete" if expected <= processed_batch_ids else "gap"
    gap_reason = "source_missing" if coverage == "gap" and not expected.isdisjoint(missing_at_source) else None
    return DailyRow(
        date=day_key,
        count_unique_url=len(of_day),
        count_after_near_dup_collapse=sum(1 for item in of_day if not item.is_near_duplicate),
        count_positive=len(positives),
        count_neutral=len(neutrals),
        count_negative=len(negatives),
        count_without_sentiment=len(missing),
        sentiment_mean=(sum(scores) / len(scores)) if scores else None,
        coverage=coverage,
        gap_reason=gap_reason,
    )
