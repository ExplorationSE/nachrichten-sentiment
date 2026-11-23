import io

import pytest

from nachrichten_sentiment.titles import fetch_title, http_title_opener, parse_html_title


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


class _FakeResponse:
    def __init__(self, body: bytes, charset: str | None) -> None:
        self._body = io.BytesIO(body)
        self.read_sizes: list = []
        charset_value = charset

        class _Headers:
            def get_content_charset(self):
                return charset_value

        self.headers = _Headers()

    def read(self, size=-1):
        self.read_sizes.append(size)
        return self._body.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_http_title_opener_rejects_non_http_schemes_and_caches_as_missing(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    with pytest.raises(ValueError):
        http_title_opener("file:///etc/passwd", 5.0, pause_seconds=0)
    assert called["n"] == 0
    failed: dict[str, str] = {}
    result = fetch_title("file:///etc/passwd", lambda u, t: http_title_opener(u, t, pause_seconds=0), failed)
    assert result.source == "missing"
    assert failed  # als fehlend gecacht


def test_http_title_opener_limits_read_and_uses_declared_charset(monkeypatch):
    responses: list[_FakeResponse] = []

    def fake_urlopen(request, timeout=None):
        response = _FakeResponse("<title>Nvidia Café</title>".encode("latin-1"), "iso-8859-1")
        responses.append(response)
        return response

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    html = http_title_opener("https://example.com/a", 5.0, pause_seconds=0)
    assert "Nvidia Café" in html
    assert responses[0].read_sizes == [512_000]

    def fake_urlopen_no_charset(request, timeout=None):
        return _FakeResponse("<title>Ünïcode</title>".encode("utf-8"), None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen_no_charset)
    assert "Ünïcode" in http_title_opener("http://example.com/b", 5.0, pause_seconds=0)


def test_fetch_title_without_title_is_cached_missing():
    failed: dict[str, str] = {}
    result = fetch_title("https://example.com/none", lambda u, t: "<html><body>x</body></html>", failed)
    assert result.source == "missing"
    assert result.title is None
    assert "https://example.com/none" in failed


def test_parse_html_title_truncates_to_300_characters():
    long_title = "NVIDIA " * 100
    parsed = parse_html_title(f"<html><title>{long_title}</title></html>")
    assert parsed is not None
    assert len(parsed) <= 300
    og = parse_html_title(f'<meta property="og:title" content="{"X" * 1000}">')
    assert og == "X" * 300
