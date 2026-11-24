from nachrichten_sentiment.dedup import UrlIndex
from nachrichten_sentiment.models import Article


def _article(uid: str, url: str) -> Article:
    return Article(
        gkg_record_id=uid,
        url=url,
        url_normalized="",
        source_domain="example.com",
        title="t",
        title_source="gkg",
        batch_id="20150218230000",
        batch_utc="2015-02-18T23:00:00Z",
        day_berlin="2015-02-19",
        sentiment=None,
        sentiment_label=None,
        p_positive=None,
        p_neutral=None,
        p_negative=None,
        is_near_duplicate=False,
        near_duplicate_of=None,
    )


def test_url_index_keeps_first_occurrence_globally():
    index = UrlIndex()
    first = "https://example.com/a?utm_source=x"
    later = "HTTPS://Example.com/a/"
    assert index.keep(first, "id-1") is True
    assert index.keep(later, "id-2") is False
    loaded = UrlIndex()
    kept = _article("old", "https://example.com/a")
    kept.url_normalized = "https://example.com/a"
    loaded.load_from_articles([kept])
    assert loaded.keep("https://example.com/a/", "new") is False
    assert loaded.keep("https://example.com/b", "new-b") is True
