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


def test_download_404_becomes_missing_after_retries(tmp_path: Path):
    def fetcher(url: str) -> bytes:
        raise MissingGkgError("20150218230000")

    with pytest.raises(MissingGkgError):
        download_gkg_zip("20150218230000", tmp_path, retries=3, backoff_seconds=0.0, fetcher=fetcher)


def test_download_other_errors_become_download_error(tmp_path: Path):
    def fetcher(url: str) -> bytes:
        raise RuntimeError("boom")

    with pytest.raises(DownloadError):
        download_gkg_zip("20150218230000", tmp_path, retries=2, backoff_seconds=0.0, fetcher=fetcher)
