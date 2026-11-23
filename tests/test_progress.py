import json
from datetime import datetime, timezone
from pathlib import Path

from nachrichten_sentiment.models import ProgressState
from nachrichten_sentiment.progress import (
    append_gap_log,
    batches_to_process,
    load_progress,
    mark_gap,
    mark_missing_at_source,
    mark_success,
    processed_batch_ids,
    save_progress,
)


def test_progress_roundtrip_resume_and_gap_log(tmp_path: Path):
    path = tmp_path / "progress.json"
    log = tmp_path / "gaps.log"
    state = ProgressState(last_success_batch_id=None, cursor_batch_id=None, open_gaps=[], failed_title_fetches={})
    mark_success(state, "20150218230000")
    mark_gap(state, "20150218231500")
    mark_success(state, "20150218233000")
    save_progress(path, state)
    append_gap_log(log, "missing 20150218231500")
    loaded = load_progress(path)
    assert loaded.last_success_batch_id == "20150218233000"
    assert loaded.cursor_batch_id == "20150218233000"
    assert loaded.open_gaps == ["20150218231500"]
    processed = processed_batch_ids(loaded)
    assert "20150218230000" in processed
    assert "20150218233000" in processed
    assert "20150218231500" not in processed
    todo = batches_to_process(loaded, "20150218234500")
    assert todo[0] == "20150218231500"
    assert todo[-1] == "20150218234500"
    assert "20150218233000" not in todo
    assert "missing 20150218231500" in log.read_text(encoding="utf-8")
    empty = load_progress(tmp_path / "missing.json")
    assert empty.cursor_batch_id is None
    assert empty.successful_spans == []
    assert batches_to_process(empty, "20150218231500") == ["20150218230000", "20150218231500"]
    mark_success(loaded, "20150218231500")
    assert loaded.last_success_batch_id == "20150218233000"
    assert "20150218231500" not in loaded.open_gaps
    assert "20150218231500" in processed_batch_ids(loaded)


def test_processed_batch_ids_only_contain_actual_successes():
    state = ProgressState(last_success_batch_id=None, cursor_batch_id=None, open_gaps=[], failed_title_fetches={})
    mark_success(state, "20150219000000")
    processed = processed_batch_ids(state)
    assert processed == {"20150219000000"}
    assert "20150218230000" not in processed
    assert "20150218234500" not in processed
    mark_success(state, "20150218230000")
    assert state.last_success_batch_id == "20150219000000"
    assert processed_batch_ids(state) == {"20150218230000", "20150219000000"}


def test_missing_at_source_roundtrip_and_backward_compatible_load(tmp_path: Path):
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"cursor_batch_id": "20150218230000", "open_gaps": [], "successful_spans": []}), encoding="utf-8")
    assert load_progress(old).missing_at_source == []
    state = ProgressState(None, None, ["20150218231500"], {})
    mark_missing_at_source(state, "20150218231500")
    assert state.missing_at_source == ["20150218231500"]
    assert state.open_gaps == []  # nicht doppelt gefuehrt
    assert state.cursor_batch_id == "20150218231500"
    assert "20150218231500" not in processed_batch_ids(state)
    path = tmp_path / "progress.json"
    save_progress(path, state)
    assert load_progress(path).missing_at_source == ["20150218231500"]


def test_old_missing_at_source_only_retried_when_recent_or_requested():
    now = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
    state = ProgressState(None, "20261123100000", [], {})
    old_missing = "20180101000000"
    recent_missing = "20261120000000"
    mark_missing_at_source(state, old_missing)
    mark_missing_at_source(state, recent_missing)
    todo = batches_to_process(state, "20261123100000", now=now)
    assert old_missing not in todo
    assert recent_missing in todo
    todo_retry = batches_to_process(state, "20261123100000", now=now, retry_missing=True)
    assert old_missing in todo_retry
    assert recent_missing in todo_retry
    assert len(todo_retry) == len(set(todo_retry))


def test_span_closes_after_recovered_missing_batch():
    state = ProgressState(None, None, [], {})
    a, b, c = "20150218230000", "20150218231500", "20150218233000"
    mark_success(state, a)
    mark_missing_at_source(state, b)
    mark_success(state, c)
    assert state.successful_spans == [[a, a], [c, c]]
    mark_success(state, b)
    assert state.successful_spans == [[a, c]]
    assert state.missing_at_source == []
    assert processed_batch_ids(state) == {a, b, c}
