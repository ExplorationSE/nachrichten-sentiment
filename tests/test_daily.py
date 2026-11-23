from datetime import date

import pytest

from nachrichten_sentiment.daily import aggregate_daily
from nachrichten_sentiment.models import Article
from nachrichten_sentiment.timeutil import expected_batch_ids_for_berlin_day


def _article(**kwargs) -> Article:
    base = dict(
        gkg_record_id="id",
        url="https://example.com/id",
        url_normalized="https://example.com/id",
        source_domain="example.com",
        title="t",
        title_source="gkg",
        batch_id="20150219000000",
        batch_utc="2015-02-19T00:00:00Z",
        day_berlin="2015-02-19",
        sentiment=0.5,
        sentiment_label="positive",
        p_positive=0.6,
        p_neutral=0.3,
        p_negative=0.1,
        is_near_duplicate=False,
        near_duplicate_of=None,
    )
    base.update(kwargs)
    return Article(**base)  # type: ignore[arg-type]


def test_aggregate_counts_invariant_and_mean():
    day = date(2015, 2, 19)
    articles = [
        _article(gkg_record_id="p", sentiment_label="positive", sentiment=0.8, url_normalized="https://e.com/p"),
        _article(gkg_record_id="n", sentiment_label="neutral", sentiment=0.0, url_normalized="https://e.com/n"),
        _article(gkg_record_id="d", sentiment_label="negative", sentiment=-0.2, url_normalized="https://e.com/d"),
        _article(gkg_record_id="x", sentiment=None, sentiment_label=None, title_source="missing", title="", url_normalized="https://e.com/x"),
        _article(gkg_record_id="dup", sentiment_label="positive", sentiment=0.8, is_near_duplicate=True, near_duplicate_of="p", url_normalized="https://e.com/dup"),
    ]
    processed = set(expected_batch_ids_for_berlin_day(day))
    row = aggregate_daily(articles, day, processed)
    assert row.count_unique_url == 5
    assert row.count_positive == 2
    assert row.count_neutral == 1
    assert row.count_negative == 1
    assert row.count_without_sentiment == 1
    assert row.count_positive + row.count_neutral + row.count_negative + row.count_without_sentiment == row.count_unique_url
    assert row.count_after_near_dup_collapse == 4
    assert row.sentiment_mean == pytest.approx(0.35)
    assert row.coverage == "complete"
    assert row.date == "2015-02-19"


def test_empty_complete_day_is_zero_and_missing_batches_are_gaps():
    day = date(2015, 2, 19)
    complete = aggregate_daily([], day, set(expected_batch_ids_for_berlin_day(day)))
    assert complete.count_unique_url == 0
    assert complete.sentiment_mean is None
    assert complete.coverage == "complete"
    gap = aggregate_daily([], day, set())
    assert gap.coverage == "gap"
    assert gap.count_unique_url == 0


def test_gap_reason_marks_days_with_source_missing_batches():
    day = date(2015, 2, 19)
    expected = expected_batch_ids_for_berlin_day(day)
    processed = set(expected[1:])
    missing_row = aggregate_daily([], day, processed, missing_at_source={expected[0]})
    assert missing_row.coverage == "gap"
    assert missing_row.gap_reason == "source_missing"
    plain_gap = aggregate_daily([], day, processed, missing_at_source=set())
    assert plain_gap.coverage == "gap"
    assert plain_gap.gap_reason is None
    complete = aggregate_daily([], day, set(expected), missing_at_source={"20990101000000"})
    assert complete.coverage == "complete"
    assert complete.gap_reason is None


def test_gap_reason_only_when_all_unprocessed_batches_are_missing_at_source():
    day = date(2015, 2, 19)
    expected = expected_batch_ids_for_berlin_day(day)
    processed = set(expected[2:])  # expected[0] fehlt an der Quelle, expected[1] ist offen
    mixed = aggregate_daily([], day, processed, missing_at_source={expected[0]})
    assert mixed.coverage == "gap"
    assert mixed.gap_reason is None
    both = aggregate_daily([], day, processed, missing_at_source={expected[0], expected[1]})
    assert both.gap_reason == "source_missing"
