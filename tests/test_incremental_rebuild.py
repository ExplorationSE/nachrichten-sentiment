import json
from datetime import date
from pathlib import Path

from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.dedup import mark_near_duplicates
from nachrichten_sentiment.models import Article
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.pipeline import run_batches
from nachrichten_sentiment.timeutil import expected_batch_ids_for_berlin_day
from tests.fixtures.build_week import gkg_zip_bytes, nvidia_line

SEP = expected_batch_ids_for_berlin_day(date(2019, 9, 30))[:2]
OCT = expected_batch_ids_for_berlin_day(date(2019, 10, 1))[:2]

TITLES = {
    SEP[0]: [("s1", "NVIDIA raises full-year revenue forecast"), ("s2", "Copper mines close in Chile")],
    SEP[1]: [("s3", "NVIDIA raises full-year revenue forecast!")],
    OCT[0]: [("o1", "NVIDIA unveils new datacenter GPU"), ("o2", "NVIDIA unveils new datacenter GPU.")],
    OCT[1]: [("o3", "Something unrelated about NVIDIA earnings call")],
}


class _Model:
    def predict_proba(self, title: str) -> tuple[float, float, float]:
        return (0.5, 0.3, 0.2)


def _fetcher(url: str) -> bytes:
    batch_id = url.rsplit("/", 1)[-1].split(".")[0]
    body = "".join(nvidia_line(batch_id, rid, title) for rid, title in TITLES.get(batch_id, []))
    return gkg_zip_bytes(batch_id, body)


def _kwargs(paths: ProjectPaths) -> dict:
    return dict(
        company=load_company("NVDA"),
        paths=paths,
        model=_Model(),
        title_opener=lambda u, t: "",
        fetcher=_fetcher,
    )


def _snapshot(root: Path) -> dict[str, str]:
    files = {}
    for sub in ("site/data", "data/articles"):
        for file in sorted((root / sub).rglob("*")):
            if file.is_file():
                files[str(file.relative_to(root))] = file.read_text(encoding="utf-8")
    return files


def test_incremental_runs_equal_full_rebuild(tmp_path: Path):
    inc = ProjectPaths(tmp_path / "inc")
    run_batches(SEP, **_kwargs(inc))
    run_batches(OCT, **_kwargs(inc))
    full = ProjectPaths(tmp_path / "full")
    run_batches(SEP + OCT, full_rebuild=True, **_kwargs(full))
    assert _snapshot(inc.root) == _snapshot(full.root)
    oct_lines = [json.loads(line) for line in (inc.articles_dir("NVDA") / "2019-10.jsonl").read_text().splitlines()]
    by_id = {row["gkg_record_id"]: row for row in oct_lines}
    # Flags werden dauerhaft in der Monats-JSONL gespeichert.
    assert by_id["o2"]["is_near_duplicate"] is True
    assert by_id["o2"]["near_duplicate_of"] == "o1"
    daily = json.loads((inc.site_data_dir / "nvda-daily.json").read_text(encoding="utf-8"))
    days = {row["date"]: row for row in daily["days"]}
    for key in ("2019-09-30", "2019-10-01"):
        row = days[key]
        classes = row["count_positive"] + row["count_neutral"] + row["count_negative"] + row["count_without_sentiment"]
        assert classes == row["count_after_near_dup_collapse"] < row["count_unique_url"]


def test_incremental_run_leaves_flags_and_files_of_other_days_untouched(tmp_path: Path):
    paths = ProjectPaths(tmp_path)
    run_batches(SEP, **_kwargs(paths))
    sep_file = paths.articles_dir("NVDA") / "2019-09.jsonl"
    rows = [json.loads(line) for line in sep_file.read_text().splitlines()]
    for row in rows:
        if row["gkg_record_id"] == "s2":
            row["is_near_duplicate"] = True  # absichtlich gesetzter, gespeicherter Stand
            row["near_duplicate_of"] = "s1"
    sep_file.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    sep_headlines = (paths.site_data_dir / "nvda" / "2019-09.json").read_text(encoding="utf-8")

    run_batches(OCT, **_kwargs(paths))

    after = {json.loads(line)["gkg_record_id"]: json.loads(line) for line in sep_file.read_text().splitlines()}
    assert after["s2"]["is_near_duplicate"] is True  # Tag 2019-09-30 nicht neu berechnet
    assert (paths.site_data_dir / "nvda" / "2019-09.json").read_text(encoding="utf-8") == sep_headlines
    daily = json.loads((paths.site_data_dir / "nvda-daily.json").read_text(encoding="utf-8"))
    days = {row["date"]: row for row in daily["days"]}
    assert days["2019-09-30"]["count_after_near_dup_collapse"] == 1  # aus gespeicherten Flags
    assert days["2019-10-01"]["count_after_near_dup_collapse"] == 2


def test_mark_near_duplicates_compares_only_within_day_and_matches_reference():
    def art(uid: str, title: str, day: str, utc: str) -> Article:
        return Article(uid, f"https://e.com/{uid}", f"https://e.com/{uid}", "e.com", title, "gkg", "x", utc, day,
                       None, None, None, None, None, False, None)

    items = [
        art("a", "NVIDIA raises forecast for the year", "2019-09-30", "2019-09-29T22:00:00Z"),
        art("b", "NVIDIA raises forecast for the year!", "2019-09-30", "2019-09-29T22:15:00Z"),
        art("c", "NVIDIA raises forecast for the year!", "2019-10-01", "2019-09-30T22:00:00Z"),
        art("d", "Totally different", "2019-09-30", "2019-09-29T22:30:00Z"),
        art("e", "NVIDIA raises forecast for the year?", "2019-09-30", "2019-09-29T22:45:00Z"),
    ]
    mark_near_duplicates(items)
    flags = {a.gkg_record_id: (a.is_near_duplicate, a.near_duplicate_of) for a in items}
    assert flags == {
        "a": (False, None),
        "b": (True, "a"),
        "c": (False, None),
        "d": (False, None),
        "e": (True, "a"),
    }


NOV = expected_batch_ids_for_berlin_day(date(2019, 11, 5))[:1]


def test_interrupted_run_keeps_pending_days_and_resume_equals_full_rebuild(tmp_path: Path):
    import pytest

    from nachrichten_sentiment.progress import load_progress

    paths = ProjectPaths(tmp_path / "inc")
    run_batches(SEP, **_kwargs(paths))

    def extract_or_abort(path: Path) -> str:
        import zipfile

        if path.name.split(".")[0] == NOV[0]:
            raise RuntimeError("abort")
        with zipfile.ZipFile(path) as archive:
            return archive.read(archive.namelist()[0]).decode("utf-8")

    with pytest.raises(RuntimeError):
        run_batches(OCT + NOV, extract_zip=extract_or_abort, **_kwargs(paths))
    assert "2019-10-01" in load_progress(paths.progress_path).pending_rebuild_days

    run_batches(OCT + NOV, **_kwargs(paths))
    assert load_progress(paths.progress_path).pending_rebuild_days == []

    full = ProjectPaths(tmp_path / "full")
    run_batches(SEP + OCT + NOV, full_rebuild=True, **_kwargs(full))
    snap = _snapshot(paths.root)
    assert "site/data/nvda/2019-10.json" in snap
    assert snap == _snapshot(full.root)


def test_pending_rebuild_days_load_backward_compatible(tmp_path: Path):
    from nachrichten_sentiment.progress import load_progress

    path = tmp_path / "progress.json"
    path.write_text(json.dumps({"cursor_batch_id": None}), encoding="utf-8")
    assert load_progress(path).pending_rebuild_days == []
