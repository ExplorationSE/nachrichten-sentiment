from pathlib import Path

from nachrichten_sentiment.models import ProgressState
from nachrichten_sentiment.progress import (
    append_gap_log,
    batches_to_process,
    load_progress,
    mark_gap,
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
