import json
from pathlib import Path

import pytest

from nachrichten_sentiment.cli import build_parser
from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.pipeline import run_deferred, run_initial
from nachrichten_sentiment.progress import (
    batches_to_process,
    defer_until,
    load_progress,
    processed_batch_ids,
    save_progress,
)
from nachrichten_sentiment.models import ProgressState
from nachrichten_sentiment.timeutil import iter_batch_ids
from tests.fixtures.build_week import gkg_zip_bytes, nvidia_line

FIRST = "20150218230000"


class _Model:
    def predict_proba(self, title: str) -> tuple[float, float, float]:
        return (0.5, 0.3, 0.2)


class _Abort(BaseException):
    pass


def _fetcher(abort_at=None, seen=None):
    def fetcher(url: str) -> bytes:
        batch_id = url.rsplit("/", 1)[-1].split(".")[0]
        if seen is not None:
            seen.append(batch_id)
        if batch_id == abort_at:
            raise _Abort()
        return gkg_zip_bytes(batch_id, nvidia_line(batch_id, f"r{batch_id}", f"NVIDIA headline {batch_id}"))

    return fetcher


def _run(paths, start=None, until=None, fetcher=None, workers=1):
    run_initial(paths, load_company("NVDA"), _Model(), lambda u, t: "", until_id=until,
                start_id=start, fetcher=fetcher or _fetcher(), workers=workers)


def test_defer_until_records_skipped_range_once():
    state = ProgressState(None, "20150410163000", [], {})
    defer_until(state, "20200101000000")
    assert state.deferred_ranges == [["20150410164500", "20191231234500"]]
    defer_until(state, "20200101000000")  # erneuter Start mit gleichem --start: nichts doppelt
    assert state.deferred_ranges == [["20150410164500", "20191231234500"]]
    state.cursor_batch_id = "20200101021500"  # Lauf ab 2020 fortgeschritten
    defer_until(state, "20200101000000")  # Wiederaufnahme: Start liegt vor dem Cursor
    assert state.deferred_ranges == [["20150410164500", "20191231234500"]]


def test_batches_with_start_begin_at_start_and_resume_after_cursor():
    state = ProgressState(None, "20150410163000", [], {})
    todo = batches_to_process(state, "20200101004500", start_id="20200101000000")
    assert todo == ["20200101000000", "20200101001500", "20200101003000", "20200101004500"]
    state.cursor_batch_id = "20200101001500"
    assert batches_to_process(state, "20200101004500", start_id="20200101000000") == [
        "20200101003000", "20200101004500"]


def test_progress_roundtrip_keeps_deferred_ranges(tmp_path: Path):
    state = ProgressState(None, "20200101000000", [], {}, deferred_ranges=[["20150410164500", "20191231234500"]])
    save_progress(tmp_path / "progress.json", state)
    assert load_progress(tmp_path / "progress.json").deferred_ranges == [["20150410164500", "20191231234500"]]
    raw = json.loads((tmp_path / "progress.json").read_text())
    assert raw["deferred_ranges"] == [["20150410164500", "20191231234500"]]


def test_start_later_keeps_old_data_marks_hole_as_gap_and_deferred_run_fills_it(tmp_path: Path):
    paths = ProjectPaths(tmp_path)
    # Alter Stand: die ersten 4 Sätze ab 2015.
    _run(paths, until="20150218234500")
    old_articles = (paths.articles_dir("NVDA") / "2015-02.jsonl").read_text(encoding="utf-8")
    # Später Start (im Test: ab 19.02.2015 12:00 statt 2020), bis 12:45.
    _run(paths, start="20150219120000", until="20150219124500")
    progress = load_progress(paths.progress_path)
    assert progress.deferred_ranges == [["20150219000000", "20150219114500"]]
    assert progress.cursor_batch_id == "20150219124500"
    assert old_articles in (paths.articles_dir("NVDA") / "2015-02.jsonl").read_text(encoding="utf-8")
    hole = set(iter_batch_ids("20150219000000", "20150219114500"))
    assert not hole & processed_batch_ids(progress)
    daily = json.loads((paths.site_data_dir / "nvda-daily.json").read_text(encoding="utf-8"))
    days = {row["date"]: row for row in daily["days"]}
    assert days["2015-02-19"]["coverage"] == "gap"  # Lücke, nicht 0
    # 18.02. 23:00-23:45 UTC gehört zum 19.02. Berlin (4 Artikel), dazu 12:00-12:45 UTC (4 Artikel).
    assert days["2015-02-19"]["count_unique_url"] == 8

    # Nachholen mit Abbruch mitten im Bereich, dann Wiederaufnahme.
    seen: list[str] = []
    with pytest.raises(_Abort):
        run_deferred(paths, load_company("NVDA"), _Model(), lambda u, t: "",
                     fetcher=_fetcher(abort_at="20150219030000", seen=seen))
    mid = load_progress(paths.progress_path)
    assert mid.deferred_ranges == [["20150219000000", "20150219114500"]]  # bleibt vorgemerkt
    assert mid.cursor_batch_id == "20150219124500"  # Cursor springt nicht zurück
    seen.clear()
    run_deferred(paths, load_company("NVDA"), _Model(), lambda u, t: "", fetcher=_fetcher(seen=seen), workers=3)
    assert seen[0] == "20150219030000"  # bereits fertige Sätze werden übersprungen
    done = load_progress(paths.progress_path)
    assert done.deferred_ranges == []
    assert hole <= processed_batch_ids(done)
    daily = json.loads((paths.site_data_dir / "nvda-daily.json").read_text(encoding="utf-8"))
    row = {r["date"]: r for r in daily["days"]}["2015-02-19"]
    assert row["count_unique_url"] == 8 + 48  # 00:00-11:45 UTC nachgeholt


def test_cli_start_and_nachholen_options_validate_batch_ids():
    parser = build_parser()
    args = parser.parse_args(["erstlauf", "--start", "20200101000000"])
    assert args.start == "20200101000000" and args.nachholen is False
    assert parser.parse_args(["erstlauf", "--nachholen"]).nachholen is True
    for bad in ["2020-01-01", "20200101000700", "20200101"]:
        with pytest.raises(SystemExit):
            parser.parse_args(["erstlauf", "--start", bad])
    with pytest.raises(SystemExit):
        parser.parse_args(["erstlauf", "--start", "20200101000000", "--nachholen"])
