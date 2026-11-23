from nachrichten_sentiment.titles import fetch_title


def test_fetch_title_reads_html_and_caches_failures():
    calls: list[str] = []

    def opener(url: str, timeout_seconds: float) -> str:
        calls.append(url)
        return "<html><title>NVIDIA results</title></html>"

    failed: dict[str, str] = {}
    result = fetch_title("https://example.com/a/", opener, failed)
    assert result.title == "NVIDIA results"
    assert result.source == "fetched"
    assert result.error is None
    assert failed == {}
    assert calls == ["https://example.com/a/"]


def test_fetch_title_records_failure_and_does_not_retry_from_cache():
    calls = {"n": 0}

    def opener(url: str, timeout_seconds: float) -> str:
        calls["n"] += 1
        raise TimeoutError("timed out")

    failed: dict[str, str] = {}
    first = fetch_title("https://example.com/gone", opener, failed)
    assert first.source == "missing"
    assert first.title is None
    assert first.error is not None
    assert "https://example.com/gone" in failed
    second = fetch_title("https://example.com/gone", opener, failed)
    assert second.source == "missing"
    assert calls["n"] == 1
