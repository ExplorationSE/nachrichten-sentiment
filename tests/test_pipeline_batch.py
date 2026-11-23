import io
import zipfile
from pathlib import Path

import pytest

from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.dedup import UrlIndex
from nachrichten_sentiment.models import ProgressState
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.pipeline import process_batch
from nachrichten_sentiment.store import load_articles


class _Model:
    def predict_proba(self, title: str) -> tuple[float, float, float]:
        return (0.8, 0.1, 0.1)


def _gkg_line(record_id: str, url: str, extras: str, orgs: str = "NVIDIA") -> str:
    cols = [""] * 27
    cols[0] = record_id
    cols[1] = "20150218230000"
    cols[2] = "1"
    cols[3] = "example.com"
    cols[4] = url
    cols[13] = orgs
    cols[14] = orgs
    cols[26] = extras
    return "\t".join(cols)


def test_process_batch_filters_scores_and_records_gaps(tmp_path: Path):
    paths = ProjectPaths(tmp_path)
    company = load_company("NVDA")
    progress = ProgressState(None, None, [], {})
    lines = "\n".join(
        [
            _gkg_line("r1", "https://example.com/a", "<PAGE_TITLE>NVIDIA raises forecast</PAGE_TITLE>"),
            _gkg_line("r2", "https://example.com/b", "", orgs=""),  # no nvidia
            _gkg_line("r1b", "https://example.com/a", "<PAGE_TITLE>dup url</PAGE_TITLE>"),
        ]
    )
    articles = process_batch(
        "20150218230000",
        company=company,
        paths=paths,
        url_index=UrlIndex(),
        model=_Model(),
        title_opener=lambda url, timeout: "<html></html>",
        progress=progress,
        fetcher=lambda url: b"zip",
        extract_zip=lambda path: lines,
    )
    assert [item.gkg_record_id for item in articles] == ["r1"]
    # 0.8 - 0.1 ergibt in Gleitkomma 0.7000000000000001
    assert articles[0].sentiment == pytest.approx(0.7)
    assert articles[0].title_source == "gkg"
    assert progress.last_success_batch_id == "20150218230000"
    stored = load_articles(paths, "NVDA")
    assert len(stored) == 1
    assert not (paths.tmp_dir / "20150218230000.gkg.csv.zip").exists()

    def missing(url: str):
        from nachrichten_sentiment.download import MissingGkgError
        raise MissingGkgError("20150218231500")

    process_batch(
        "20150218231500",
        company=company,
        paths=paths,
        url_index=UrlIndex(),
        model=_Model(),
        title_opener=lambda url, timeout: "",
        progress=progress,
        fetcher=missing,
        extract_zip=lambda path: "",
    )
    assert "20150218231500" in progress.open_gaps
    assert (paths.gaps_log_path).exists()
    assert "20150218231500" in paths.gaps_log_path.read_text(encoding="utf-8")


def test_process_batch_download_error_becomes_gap(tmp_path: Path):
    paths = ProjectPaths(tmp_path)
    progress = ProgressState(None, None, [], {})

    def broken(url: str):
        raise ConnectionError("boom")

    result = process_batch(
        "20150218230000",
        company=load_company("NVDA"),
        paths=paths,
        url_index=UrlIndex(),
        model=_Model(),
        title_opener=lambda url, timeout: "",
        progress=progress,
        fetcher=broken,
    )
    assert result == []
    assert progress.open_gaps == ["20150218230000"]
    assert progress.successful_spans == []
    assert paths.progress_path.exists()


def test_process_batch_reads_real_zip_with_crlf_and_fetches_missing_title(tmp_path: Path):
    paths = ProjectPaths(tmp_path)
    progress = ProgressState(None, None, [], {})
    tsv = "\r\n".join(
        [
            _gkg_line("r1", "https://example.com/nvidia-news", ""),
            _gkg_line("r2", "https://example.com/x", "<PAGE_TITLE>Nvidia caf\u00e9</PAGE_TITLE>"),
        ]
    ) + "\r\n"
    payload = tsv.encode("utf-8") + b"\xff"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("20150218230000.gkg.csv", payload)

    articles = process_batch(
        "20150218230000",
        company=load_company("NVDA"),
        paths=paths,
        url_index=UrlIndex(),
        model=None,
        title_opener=lambda url, timeout: "<html><title>Nvidia beats</title></html>",
        progress=progress,
        fetcher=lambda url: buffer.getvalue(),
    )
    assert [a.gkg_record_id for a in articles] == ["r1", "r2"]
    assert articles[0].title == "Nvidia beats"
    assert articles[0].title_source == "fetched"
    assert articles[0].sentiment is None
    assert articles[1].title == "Nvidia caf\u00e9"
    assert all("\r" not in a.url for a in articles)
    assert articles[0].day_berlin == "2015-02-19"
    assert not (paths.tmp_dir / "20150218230000.gkg.csv.zip").exists()
