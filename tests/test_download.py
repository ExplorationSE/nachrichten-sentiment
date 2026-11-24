from pathlib import Path

import pytest

from nachrichten_sentiment.download import (
    DownloadError,
    MissingGkgError,
    download_gkg_zip,
    gkg_url,
)


def test_gkg_url_uses_https():
    assert gkg_url("20150218230000") == "https://data.gdeltproject.org/gdeltv2/20150218230000.gkg.csv.zip"


def test_download_retries_then_succeeds(tmp_path: Path):
    attempts = {"n": 0}

    def fetcher(url: str) -> bytes:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ConnectionError("drop")
        return b"PK\x03\x04fake-zip"

    path = download_gkg_zip("20150218230000", tmp_path, retries=3, backoff_seconds=0.0, fetcher=fetcher)
    assert path.read_bytes() == b"PK\x03\x04fake-zip"
    assert attempts["n"] == 3


def test_download_404_aborts_immediately_without_retry_or_pause(tmp_path: Path, monkeypatch):
    calls = {"n": 0}
    sleeps: list[float] = []
    monkeypatch.setattr("nachrichten_sentiment.download.time.sleep", lambda s: sleeps.append(s))

    def fetcher(url: str) -> bytes:
        calls["n"] += 1
        raise MissingGkgError("20150218230000")

    with pytest.raises(MissingGkgError):
        download_gkg_zip("20150218230000", tmp_path, retries=3, backoff_seconds=2.0, fetcher=fetcher)
    assert calls["n"] == 1
    assert sleeps == []


def test_default_fetcher_sends_user_agent_and_maps_404(monkeypatch):
    from nachrichten_sentiment import download

    seen: dict = {}

    class _Response:
        def __init__(self, status: int) -> None:
            self.status_code = status
            self.content = b"zip"

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(str(self.status_code))

    status = {"code": 200}

    def fake_get(url, timeout=None, headers=None):
        seen["url"], seen["timeout"], seen["headers"] = url, timeout, headers
        return _Response(status["code"])

    monkeypatch.setattr(download.requests, "get", fake_get)
    url = gkg_url("20150218230000")
    assert download._default_fetcher(url) == b"zip"
    assert seen["headers"] == {"User-Agent": "NachrichtenSentiment/0.1"}
    assert seen["timeout"] == 60
    status["code"] = 404
    with pytest.raises(MissingGkgError):
        download._default_fetcher(url)


def test_download_other_errors_become_download_error(tmp_path: Path):
    calls = {"n": 0}

    def fetcher(url: str) -> bytes:
        calls["n"] += 1
        raise RuntimeError("boom")

    with pytest.raises(DownloadError):
        download_gkg_zip("20150218230000", tmp_path, retries=2, backoff_seconds=0.0, fetcher=fetcher)
    assert calls["n"] == 2
