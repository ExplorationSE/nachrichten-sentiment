from __future__ import annotations

import io
import zipfile
from datetime import date, timedelta
from pathlib import Path

from nachrichten_sentiment.timeutil import expected_batch_ids_for_berlin_day


def gkg_zip_bytes(batch_id: str, body: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"{batch_id}.gkg.csv", body)
    return buffer.getvalue()


def nvidia_line(batch_id: str, record_id: str, title: str) -> str:
    cols = [""] * 27
    cols[0] = record_id
    cols[1] = batch_id
    cols[2] = "1"
    cols[3] = "example.com"
    cols[4] = f"https://example.com/{record_id}"
    cols[13] = "NVIDIA"
    cols[14] = "NVIDIA,10"
    cols[26] = f"<PAGE_TITLE>{title}</PAGE_TITLE>"
    return "\t".join(cols) + "\n"


def write_week(dest: Path, start: date, days: int = 7, missing_batch_id: str | None = None) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    ids: list[str] = []
    for offset in range(days):
        ids.extend(expected_batch_ids_for_berlin_day(start + timedelta(days=offset)))
    first_per_day = []
    cursor = start
    for _ in range(days):
        first_per_day.append(expected_batch_ids_for_berlin_day(cursor)[0])
        cursor += timedelta(days=1)
    for batch_id in ids:
        if batch_id == missing_batch_id:
            continue
        if batch_id in first_per_day:
            body = nvidia_line(batch_id, f"hit-{batch_id}", "NVIDIA raises forecast")
        else:
            body = ""
        (dest / f"{batch_id}.gkg.csv.zip").write_bytes(gkg_zip_bytes(batch_id, body))
    return ids
