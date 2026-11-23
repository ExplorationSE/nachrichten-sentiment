from nachrichten_sentiment.dedup import mark_near_duplicates
from nachrichten_sentiment.models import Article


def _article(uid: str, title: str, day: str, source: str = "gkg", utc: str = "2015-02-19T00:00:00Z") -> Article:
    return Article(
        gkg_record_id=uid,
        url=f"https://example.com/{uid}",
        url_normalized=f"https://example.com/{uid}",
        source_domain="example.com",
        title=title,
        title_source=source,  # type: ignore[arg-type]
        batch_id="20150219000000",
        batch_utc=utc,
        day_berlin=day,
        sentiment=None,
        sentiment_label=None,
        p_positive=None,
        p_neutral=None,
        p_negative=None,
        is_near_duplicate=False,
        near_duplicate_of=None,
    )


def test_near_duplicates_same_day_and_missing_titles_stay_ungrouped():
    stem = _article("a", "NVIDIA raises full-year revenue forecast", "2015-02-19", utc="2015-02-18T23:00:00Z")
    dup = _article("b", "NVIDIA raises full-year revenue forecast!", "2015-02-19", utc="2015-02-18T23:15:00Z")
    other_day = _article("c", "NVIDIA raises full-year revenue forecast", "2015-02-20", utc="2015-02-19T23:00:00Z")
    missing = _article("d", "", "2015-02-19", source="missing", utc="2015-02-18T23:30:00Z")
    mark_near_duplicates([stem, dup, other_day, missing], 0.90)
    assert stem.is_near_duplicate is False
    assert stem.near_duplicate_of is None
    assert dup.is_near_duplicate is True
    assert dup.near_duplicate_of == "a"
    assert other_day.is_near_duplicate is False
    assert missing.is_near_duplicate is False
    assert missing.near_duplicate_of is None
