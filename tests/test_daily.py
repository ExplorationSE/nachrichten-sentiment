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
    # Klassen, ohne-Wert-Zahl und Mittelwert zählen nur Nicht-Duplikate (dup bleibt außen vor).
    assert row.count_positive == 1
    assert row.count_neutral == 1
    assert row.count_negative == 1
    assert row.count_without_sentiment == 1
    assert row.count_after_near_dup_collapse == 4
    assert (
        row.count_positive + row.count_neutral + row.count_negative + row.count_without_sentiment
        == row.count_after_near_dup_collapse
    )
    assert row.sentiment_mean == pytest.approx((0.8 + 0.0 - 0.2) / 3)
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


def test_near_duplicates_do_not_count_in_classes_or_mean():
    day = date(2015, 2, 19)
    articles = [
        _article(gkg_record_id="stem", sentiment_label="negative", sentiment=-0.6, url_normalized="https://e.com/s"),
        _article(gkg_record_id="d1", sentiment_label="negative", sentiment=-0.6, is_near_duplicate=True, near_duplicate_of="stem", url_normalized="https://e.com/d1"),
        _article(gkg_record_id="d2", sentiment_label="negative", sentiment=-0.6, is_near_duplicate=True, near_duplicate_of="stem", url_normalized="https://e.com/d2"),
        _article(gkg_record_id="pos", sentiment_label="positive", sentiment=0.4, url_normalized="https://e.com/p"),
        _article(gkg_record_id="dx", sentiment=None, sentiment_label=None, is_near_duplicate=True, near_duplicate_of="pos", url_normalized="https://e.com/dx"),
    ]
    row = aggregate_daily(articles, day, set(expected_batch_ids_for_berlin_day(day)))
    assert row.count_unique_url == 5
    assert row.count_after_near_dup_collapse == 2
    assert (row.count_positive, row.count_neutral, row.count_negative, row.count_without_sentiment) == (1, 0, 1, 0)
    assert row.count_positive + row.count_neutral + row.count_negative + row.count_without_sentiment == 2
    assert row.sentiment_mean == pytest.approx(-0.1)


def test_row_carries_both_counting_modes_with_and_without_near_duplicates():
    day = date(2015, 2, 19)
    articles = [
        _article(gkg_record_id="stem", sentiment_label="negative", sentiment=-0.6, url_normalized="https://e.com/s"),
        _article(gkg_record_id="d1", sentiment_label="negative", sentiment=-0.6, is_near_duplicate=True, near_duplicate_of="stem", url_normalized="https://e.com/d1"),
        _article(gkg_record_id="d2", sentiment_label="neutral", sentiment=0.0, is_near_duplicate=True, near_duplicate_of="stem", url_normalized="https://e.com/d2"),
        _article(gkg_record_id="pos", sentiment_label="positive", sentiment=0.4, url_normalized="https://e.com/p"),
        _article(gkg_record_id="dx", sentiment=None, sentiment_label=None, is_near_duplicate=True, near_duplicate_of="pos", url_normalized="https://e.com/dx"),
    ]
    row = aggregate_daily(articles, day, set(expected_batch_ids_for_berlin_day(day)))
    # Modus "ohne Nahduplikate" (Standard): unverändert.
    assert (row.count_positive, row.count_neutral, row.count_negative, row.count_without_sentiment) == (1, 0, 1, 0)
    assert row.sentiment_mean == pytest.approx(-0.1)
    # Modus "alle Nachrichten": jede URL-eindeutige Meldung zählt.
    assert (row.count_positive_all, row.count_neutral_all, row.count_negative_all, row.count_without_sentiment_all) == (1, 1, 2, 1)
    assert (
        row.count_positive_all + row.count_neutral_all + row.count_negative_all + row.count_without_sentiment_all
        == row.count_unique_url
    )
    assert row.sentiment_mean_all == pytest.approx((-0.6 - 0.6 + 0.0 + 0.4) / 4)


def test_empty_day_has_no_mean_in_either_mode():
    day = date(2015, 2, 19)
    row = aggregate_daily([], day, set(expected_batch_ids_for_berlin_day(day)))
    assert row.sentiment_mean is None and row.sentiment_mean_all is None
    assert (row.count_positive_all, row.count_neutral_all, row.count_negative_all, row.count_without_sentiment_all) == (0, 0, 0, 0)


def test_candle_from_batch_means_in_chronological_order_for_both_modes():
    day = date(2015, 2, 19)
    ids = expected_batch_ids_for_berlin_day(day)
    b0, b1, b2 = ids[3], ids[10], ids[40]
    articles = [
        # Reihenfolge absichtlich nicht chronologisch.
        _article(gkg_record_id="c1", batch_id=b2, sentiment=-0.2, sentiment_label="negative", url_normalized="https://e.com/c1"),
        _article(gkg_record_id="a1", batch_id=b0, sentiment=0.4, url_normalized="https://e.com/a1"),
        _article(gkg_record_id="a2", batch_id=b0, sentiment=0.0, sentiment_label="neutral", url_normalized="https://e.com/a2"),
        _article(gkg_record_id="b1", batch_id=b1, sentiment=0.6, url_normalized="https://e.com/b1"),
        _article(gkg_record_id="b2", batch_id=b1, sentiment=-0.8, sentiment_label="negative", is_near_duplicate=True,
                 near_duplicate_of="c1", url_normalized="https://e.com/b2"),
        _article(gkg_record_id="x", batch_id=b2, sentiment=None, sentiment_label=None, url_normalized="https://e.com/x"),
    ]
    row = aggregate_daily(articles, day, set(ids))
    # ohne Nahduplikate: Satzmittel b0=0,2  b1=0,6  b2=-0,2 → O 0,2 H 0,6 L -0,2 C -0,2; 3 Sätze
    assert row.ohlc == pytest.approx((0.2, 0.6, -0.2, -0.2, 3))
    # alle: b0=0,2  b1=(0,6-0,8)/2=-0,1  b2=-0,2 → O 0,2 H 0,2 L -0,2 C -0,2
    assert row.ohlc_all == pytest.approx((0.2, 0.2, -0.2, -0.2, 3))


def test_candle_single_batch_is_flat_and_empty_day_has_none():
    day = date(2015, 2, 19)
    ids = expected_batch_ids_for_berlin_day(day)
    one = aggregate_daily([_article(batch_id=ids[5], sentiment=0.3)], day, set(ids))
    assert one.ohlc == pytest.approx((0.3, 0.3, 0.3, 0.3, 1))
    assert one.ohlc_all == pytest.approx((0.3, 0.3, 0.3, 0.3, 1))
    empty = aggregate_daily([], day, set(ids))
    assert empty.ohlc is None and empty.ohlc_all is None
    only_missing = aggregate_daily([_article(batch_id=ids[5], sentiment=None, sentiment_label=None)], day, set(ids))
    assert only_missing.ohlc is None


def test_candle_values_are_rounded_compactly():
    day = date(2015, 2, 19)
    ids = expected_batch_ids_for_berlin_day(day)
    row = aggregate_daily([_article(batch_id=ids[0], sentiment=0.123456789)], day, set(ids))
    assert row.ohlc == (0.1235, 0.1235, 0.1235, 0.1235, 1)
