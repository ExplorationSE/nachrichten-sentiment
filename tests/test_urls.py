from nachrichten_sentiment.urls import normalize_url


def test_normalize_url_lowercases_host_and_strips_slash_and_tracking():
    raw = "HTTPS://Example.COM/Path/?utm_source=x&id=1&fbclid=abc&gclid=zzz"
    assert normalize_url(raw) == "https://example.com/Path?id=1"


def test_normalize_url_strips_only_trailing_slash_on_path():
    assert normalize_url("https://example.com/") == "https://example.com"
    assert normalize_url("https://example.com/a/") == "https://example.com/a"
