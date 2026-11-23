import json
import zipfile
from datetime import date
from pathlib import Path

from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.download import MissingGkgError
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.pipeline import run_trial
from nachrichten_sentiment.progress import load_progress, processed_batch_ids
from nachrichten_sentiment.store import load_articles
from nachrichten_sentiment.timeutil import expected_batch_ids_for_berlin_day
from tests.fixtures.build_week import write_week


class _Model:
    def predict_proba(self, title: str) -> tuple[float, float, float]:
        return (0.7, 0.2, 0.1)


def test_trial_week_gap_resume_and_site_files(tmp_path: Path):
    start = date(2019, 9, 23)
    fixture = tmp_path / "fixtures"
    missing = expected_batch_ids_for_berlin_day(start)[10]
    write_week(fixture, start, days=7, missing_batch_id=missing)
    paths = ProjectPaths(tmp_path)
    company = load_company("NVDA")

    def fetcher(url: str) -> bytes:
        batch_id = url.rsplit("/", 1)[-1].split(".")[0]
        file = fixture / f"{batch_id}.gkg.csv.zip"
        if not file.exists():
            raise MissingGkgError(batch_id)
        return file.read_bytes()

    # Echte Unterbrechung: extract_zip wirft nach drei erfolgreichen Sätzen RuntimeError,
    # den process_batch nicht in eine Lücke umwandelt.
    seen = {"n": 0}
    interrupted_at = {"id": None}

    def extract_or_interrupt(path: Path) -> str:
        batch_id = path.name.split(".")[0]
        seen["n"] += 1
        if seen["n"] > 3:
            interrupted_at["id"] = batch_id
            raise RuntimeError("interrupted")
        with zipfile.ZipFile(path) as archive:
            return archive.read(archive.namelist()[0]).decode("utf-8", errors="replace")

    try:
        run_trial(
            paths,
            company,
            _Model(),
            lambda url, timeout: "",
            start,
            days=7,
            fetcher=fetcher,
            extract_zip=extract_or_interrupt,
        )
    except RuntimeError:
        pass
    mid = load_progress(paths.progress_path)
    assert mid.cursor_batch_id is not None
    assert interrupted_at["id"] is not None
    assert interrupted_at["id"] not in processed_batch_ids(mid)
    assert interrupted_at["id"] not in mid.open_gaps
    # Resume with the full fetcher and normal zip extraction.
    run_trial(paths, company, _Model(), lambda url, timeout: "", start, days=7, fetcher=fetcher)
    progress = load_progress(paths.progress_path)
    assert missing in progress.open_gaps
    daily = json.loads((tmp_path / "site" / "data" / "nvda-daily.json").read_text(encoding="utf-8"))
    days = {row["date"]: row for row in daily["days"]}
    assert daily["days"][0]["date"] == "2015-02-19"
    assert daily["days"][0]["coverage"] == "gap"
    assert daily["days"][0]["count_unique_url"] == 0
    assert days["2019-09-22"]["coverage"] == "gap"
    assert days["2019-09-23"]["coverage"] == "gap"
    assert days["2019-09-23"]["count_unique_url"] == 1
    assert days["2019-09-24"]["coverage"] == "complete"
    assert days["2019-09-24"]["count_unique_url"] == 1
    assert days["2019-09-24"]["count_positive"] == 1
    assert days["2019-09-24"]["sentiment_mean"] == 0.6
    assert "2019-09-29" in days
    headlines = json.loads((tmp_path / "site" / "data" / "nvda" / "2019-09.json").read_text(encoding="utf-8"))
    assert headlines["2019-09-24"][0]["title"] == "NVIDIA raises forecast"
    assert len(load_articles(paths, "NVDA")) == 7


def test_trial_fetches_title_when_page_title_missing(tmp_path: Path):
    from tests.fixtures.build_week import gkg_zip_bytes

    paths = ProjectPaths(tmp_path)
    company = load_company("NVDA")
    day = date(2019, 9, 24)
    ids = expected_batch_ids_for_berlin_day(day)
    first = ids[0]
    cols = [""] * 27
    cols[0] = "fetch-1"
    cols[1] = first
    cols[2] = "1"
    cols[3] = "example.com"
    cols[4] = "https://example.com/fetch-1"
    cols[13] = "NVIDIA"
    cols[26] = ""
    body = "\t".join(cols) + "\n"

    def fetcher(url: str) -> bytes:
        batch_id = url.rsplit("/", 1)[-1].split(".")[0]
        payload = body if batch_id == first else ""
        return gkg_zip_bytes(batch_id, payload)

    def opener(url: str, timeout: float) -> str:
        return "<html><title>Fetched NVIDIA title</title></html>"

    run_trial(paths, company, _Model(), opener, day, days=1, fetcher=fetcher)
    article = load_articles(paths, "NVDA")[0]
    assert article.title_source == "fetched"
    assert article.title == "Fetched NVIDIA title"
