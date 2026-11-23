from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from nachrichten_sentiment.models import ProgressState
from nachrichten_sentiment.timeutil import FIRST_BATCH_ID, iter_batch_ids, next_batch_id


def load_progress(path: Path) -> ProgressState:
    if not path.exists():
        return ProgressState(None, None, [], {})
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ProgressState(
        last_success_batch_id=raw.get("last_success_batch_id"),
        cursor_batch_id=raw.get("cursor_batch_id"),
        open_gaps=list(raw.get("open_gaps", [])),
        failed_title_fetches=dict(raw.get("failed_title_fetches", {})),
        successful_spans=[list(span) for span in raw.get("successful_spans", [])],
    )


def save_progress(path: Path, state: ProgressState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "last_success_batch_id": state.last_success_batch_id,
                "cursor_batch_id": state.cursor_batch_id,
                "open_gaps": state.open_gaps,
                "failed_title_fetches": state.failed_title_fetches,
                "successful_spans": state.successful_spans,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def append_gap_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {message}\n")


def _merge_successful_span(spans: list[list[str]], batch_id: str) -> list[list[str]]:
    items = [[start, end] for start, end in spans]
    items.append([batch_id, batch_id])
    items.sort(key=lambda span: span[0])
    merged: list[list[str]] = []
    for start, end in items:
        if not merged:
            merged.append([start, end])
            continue
        _prev_start, prev_end = merged[-1]
        if start <= prev_end or start <= next_batch_id(prev_end):
            if end > prev_end:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged


def mark_success(state: ProgressState, batch_id: str) -> None:
    if batch_id in state.open_gaps:
        state.open_gaps.remove(batch_id)
    if state.last_success_batch_id is None or batch_id > state.last_success_batch_id:
        state.last_success_batch_id = batch_id
    state.cursor_batch_id = batch_id if state.cursor_batch_id is None or batch_id > state.cursor_batch_id else state.cursor_batch_id
    state.successful_spans = _merge_successful_span(state.successful_spans, batch_id)


def mark_gap(state: ProgressState, batch_id: str) -> None:
    if batch_id not in state.open_gaps:
        state.open_gaps.append(batch_id)
        state.open_gaps.sort()
    state.cursor_batch_id = batch_id if state.cursor_batch_id is None or batch_id > state.cursor_batch_id else state.cursor_batch_id


def processed_batch_ids(state: ProgressState) -> set[str]:
    ids: set[str] = set()
    for start, end in state.successful_spans:
        ids.update(iter_batch_ids(start, end))
    return ids


def batches_to_process(state: ProgressState, until_id: str) -> list[str]:
    pending: list[str] = []
    seen: set[str] = set()
    for batch_id in state.open_gaps:
        if batch_id <= until_id and batch_id not in seen:
            pending.append(batch_id)
            seen.add(batch_id)
    start = FIRST_BATCH_ID if state.cursor_batch_id is None else next_batch_id(state.cursor_batch_id)
    if start <= until_id:
        for batch_id in iter_batch_ids(start, until_id):
            if batch_id not in seen:
                pending.append(batch_id)
                seen.add(batch_id)
    return pending
