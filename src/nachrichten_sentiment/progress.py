from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from nachrichten_sentiment.fileutil import atomic_write_text, repair_partial_last_line
from nachrichten_sentiment.models import ProgressState
from nachrichten_sentiment.timeutil import FIRST_BATCH_ID, datetime_from_batch_id, iter_batch_ids, next_batch_id

# Ein 404 auf einen jungen Satz kann an verspäteter Veröffentlichung liegen; ältere gelten als dauerhaft fehlend.
MISSING_RETRY_WINDOW = timedelta(days=7)

logger = logging.getLogger(__name__)


def failed_titles_path(progress_path: Path) -> Path:
    return progress_path.parent / "failed_titles.jsonl"


def _load_failed_titles(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    entries: dict[str, str] = {}
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for number, line in enumerate(lines, start=1):
        try:
            raw = json.loads(line)
            entries[raw["url"]] = raw["error"]
        except (json.JSONDecodeError, KeyError, TypeError):
            if number != len(lines):
                raise
            logger.warning("überspringe unvollständige letzte Zeile in %s", path)
    return entries


def load_progress(path: Path) -> ProgressState:
    from_file = _load_failed_titles(failed_titles_path(path))
    raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    # Altbestand aus progress.json (vor failed_titles.jsonl) wird beim nächsten Speichern übernommen.
    legacy = dict(raw.get("failed_title_fetches", {}))
    return ProgressState(
        last_success_batch_id=raw.get("last_success_batch_id"),
        cursor_batch_id=raw.get("cursor_batch_id"),
        open_gaps=list(raw.get("open_gaps", [])),
        failed_title_fetches={**legacy, **from_file},
        successful_spans=[list(span) for span in raw.get("successful_spans", [])],
        missing_at_source=list(raw.get("missing_at_source", [])),
        persisted_failed_titles=set(from_file),
    )


def _append_failed_titles(path: Path, state: ProgressState) -> None:
    new = [key for key in state.failed_title_fetches if key not in state.persisted_failed_titles]
    if not new:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    repair_partial_last_line(path)
    with path.open("a", encoding="utf-8") as handle:
        for key in new:
            handle.write(json.dumps({"url": key, "error": state.failed_title_fetches[key]}, ensure_ascii=False) + "\n")
    state.persisted_failed_titles.update(new)


def save_progress(path: Path, state: ProgressState) -> None:
    _append_failed_titles(failed_titles_path(path), state)
    atomic_write_text(
        path,
        json.dumps(
            {
                "last_success_batch_id": state.last_success_batch_id,
                "cursor_batch_id": state.cursor_batch_id,
                "open_gaps": state.open_gaps,
                "successful_spans": state.successful_spans,
                "missing_at_source": state.missing_at_source,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
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


def _advance_cursor(state: ProgressState, batch_id: str) -> None:
    if state.cursor_batch_id is None or batch_id > state.cursor_batch_id:
        state.cursor_batch_id = batch_id


def mark_success(state: ProgressState, batch_id: str) -> None:
    if batch_id in state.open_gaps:
        state.open_gaps.remove(batch_id)
    if batch_id in state.missing_at_source:
        state.missing_at_source.remove(batch_id)
    if state.last_success_batch_id is None or batch_id > state.last_success_batch_id:
        state.last_success_batch_id = batch_id
    _advance_cursor(state, batch_id)
    state.successful_spans = _merge_successful_span(state.successful_spans, batch_id)


def mark_gap(state: ProgressState, batch_id: str) -> None:
    if batch_id in state.missing_at_source:
        state.missing_at_source.remove(batch_id)
    if batch_id not in state.open_gaps:
        state.open_gaps.append(batch_id)
        state.open_gaps.sort()
    _advance_cursor(state, batch_id)


def mark_missing_at_source(state: ProgressState, batch_id: str) -> None:
    """GDELT hat 404 geliefert: Satz bleibt Lücke, wird aber nicht bei jedem Lauf erneut versucht."""
    if batch_id in state.open_gaps:
        state.open_gaps.remove(batch_id)
    if batch_id not in state.missing_at_source:
        state.missing_at_source.append(batch_id)
        state.missing_at_source.sort()
    _advance_cursor(state, batch_id)


def processed_batch_ids(state: ProgressState) -> set[str]:
    ids: set[str] = set()
    for start, end in state.successful_spans:
        ids.update(iter_batch_ids(start, end))
    return ids


def batches_to_process(
    state: ProgressState,
    until_id: str,
    now: datetime | None = None,
    retry_missing: bool = False,
) -> list[str]:
    """Offene Lücken, an der Quelle fehlende Sätze (nur jung oder auf Wunsch) und neue Sätze bis until_id."""
    current = now or datetime.now(timezone.utc)
    pending: list[str] = []
    seen: set[str] = set()
    retry = [
        batch_id
        for batch_id in state.missing_at_source
        if retry_missing or current - datetime_from_batch_id(batch_id) < MISSING_RETRY_WINDOW
    ]
    for batch_id in sorted([*state.open_gaps, *retry]):
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
