import json
from datetime import date
from pathlib import Path

from nachrichten_sentiment.cli import build_parser
from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.pipeline import run_trial
from nachrichten_sentiment.store import load_articles
from nachrichten_sentiment.timeutil import expected_batch_ids_for_berlin_day


class _Model:
    def predict_proba(self, title: str) -> tuple[float, float, float]:
        return (0.6, 0.3, 0.1)


def _line(batch_id: str, record_id: str) -> str:
    cols = [""] * 27
    cols[0] = record_id
    cols[1] = batch_id
    cols[2] = "1"
    cols[3] = "example.com"
    cols[4] = f"https://example.com/{record_id}"
    cols[13] = "NVIDIA"
    cols[26] = f"<PAGE_TITLE>NVIDIA news {record_id}</PAGE_TITLE>"
    return "\t".join(cols)


def test_run_trial_rebuilds_daily_and_cli_parses():
    parser = build_parser()
    args = parser.parse_args(["tageslauf", "--day", "2015-02-19"])
    assert args.command == "tageslauf"
    assert args.day == "2015-02-19"
    args2 = parser.parse_args(["probelauf", "--start", "2019-09-23", "--days", "7"])
    assert args2.command == "probelauf"
    assert args2.start == "2019-09-23"
    args3 = parser.parse_args(["erstlauf", "--until", "20150218234500"])
    assert args3.until == "20150218234500"


def test_run_trial_one_complete_day(tmp_path: Path):
    # Ausgaben landen in tmp_path, load_company liest die Repo-Konfiguration.
    paths = ProjectPaths(tmp_path)
    company = load_company("NVDA")
    day = date(2019, 9, 23)
    ids = expected_batch_ids_for_berlin_day(day)
    first = ids[0]

    def extract_zip(path: Path) -> str:
        batch_id = path.name.split(".")[0]
        if batch_id == first:
            return _line(batch_id, "hit-1")
        return ""

    run_trial(
        paths,
        company,
        _Model(),
        title_opener=lambda url, timeout: "",
        start_day=day,
        days=1,
        fetcher=lambda url: b"zip",
        extract_zip=extract_zip,
    )
    daily = json.loads((tmp_path / "site" / "data" / "nvda-daily.json").read_text(encoding="utf-8"))
    days = {row["date"]: row for row in daily["days"]}
    assert daily["days"][0]["date"] == "2015-02-19"
    assert daily["days"][0]["coverage"] == "gap"
    assert daily["days"][0]["count_unique_url"] == 0
    assert days["2019-09-22"]["coverage"] == "gap"
    assert days["2019-09-23"]["coverage"] == "complete"
    assert days["2019-09-23"]["count_unique_url"] == 1
    assert load_articles(paths, "NVDA")[0].title.startswith("NVIDIA news")


def test_run_batches_resumes_preloads_urls_and_rebuilds_headlines(tmp_path: Path):
    from datetime import datetime, timezone

    from nachrichten_sentiment.pipeline import _latest_published_batch_id, run_batches

    paths = ProjectPaths(tmp_path)
    company = load_company("NVDA")
    a, b, c = "20190923000000", "20190923001500", "20190923003000"
    calls: list[str] = []

    def fetcher(url: str) -> bytes:
        calls.append(url.rsplit("/", 1)[-1].split(".")[0])
        return b"zip"

    def extract_zip(path: Path) -> str:
        batch_id = path.name.split(".")[0]
        if batch_id == a:
            return _line(batch_id, "x1")
        if batch_id == b:
            # gleiche URL wie in a (x1) plus ein Nahduplikat-Titel
            return _line(batch_id, "x1") + "\n" + _line(batch_id, "x1b")
        return ""

    kwargs = dict(company=company, paths=paths, model=_Model(), title_opener=lambda u, t: "", fetcher=fetcher, extract_zip=extract_zip)
    run_batches([a], **kwargs)
    run_batches([a, b, c], **kwargs)
    assert calls == [a, b, c]  # a wurde beim zweiten Lauf übersprungen
    stored = load_articles(paths, "NVDA")
    assert sorted(item.gkg_record_id for item in stored) == ["x1", "x1b"]  # URL von x1 nicht doppelt
    headlines = json.loads((tmp_path / "site" / "data" / "nvda" / "2019-09.json").read_text(encoding="utf-8"))
    by_id = {row["gkg_record_id"]: row for row in headlines["2019-09-23"]}
    assert by_id["x1b"]["is_near_duplicate"] is True
    assert by_id["x1b"]["near_duplicate_of"] == "x1"

    now = datetime(2026, 11, 23, 21, 22, 5, tzinfo=timezone.utc)
    assert _latest_published_batch_id(now) == "20261123210000"


def _write_fixture_zip(directory: Path, batch_id: str, text: str) -> None:
    import zipfile

    directory.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(directory / f"{batch_id}.gkg.csv.zip", "w") as archive:
        archive.writestr(f"{batch_id}.gkg.csv", text)


def test_probelauf_uses_separate_root_and_leaves_main_state_untouched(tmp_path: Path, monkeypatch):
    from nachrichten_sentiment import cli

    main_root = tmp_path / "repo"
    monkeypatch.setattr(cli, "default_root", lambda: main_root)
    monkeypatch.setattr(cli, "_model", lambda: _Model())
    first = expected_batch_ids_for_berlin_day(date(2019, 9, 23))[0]
    fixtures = tmp_path / "fixtures"
    _write_fixture_zip(fixtures, first, _line(first, "p1"))

    assert cli.main(["probelauf", "--start", "2019-09-23", "--days", "1", "--fixture-dir", str(fixtures)]) == 0

    assert not (main_root / "data" / "state" / "progress.json").exists()
    assert not (main_root / "site" / "data" / "nvda-daily.json").exists()
    probe = main_root / "probe"
    assert (probe / "data" / "state" / "progress.json").exists()
    assert (probe / "site" / "data" / "nvda-daily.json").exists()
    assert load_articles(ProjectPaths(probe), "NVDA")[0].gkg_record_id == "p1"

    custom = tmp_path / "eigener-probe-root"
    cli.main(["probelauf", "--start", "2019-09-23", "--days", "1", "--fixture-dir", str(fixtures), "--root", str(custom)])
    assert (custom / "data" / "state" / "progress.json").exists()
    assert not (main_root / "data" / "state" / "progress.json").exists()
