from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
FIRST_BATCH_ID = "20150218230000"
FIRST_BERLIN_DAY = date(2015, 2, 19)


def datetime_from_batch_id(batch_id: str) -> datetime:
    return datetime.strptime(batch_id, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def batch_id_from_datetime(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")


def berlin_day_from_batch_id(batch_id: str) -> date:
    return datetime_from_batch_id(batch_id).astimezone(BERLIN).date()


def next_batch_id(batch_id: str) -> str:
    return batch_id_from_datetime(datetime_from_batch_id(batch_id) + timedelta(minutes=15))


def iter_batch_ids(start_id: str, end_id: str) -> list[str]:
    ids: list[str] = []
    current = start_id
    while current <= end_id:
        ids.append(current)
        current = next_batch_id(current)
    return ids


def expected_batch_ids_for_berlin_day(day: date) -> list[str]:
    start_local = datetime(day.year, day.month, day.day, 0, 0, tzinfo=BERLIN)
    end_local = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=BERLIN)
    start = start_local.astimezone(timezone.utc)
    # Round up to the next 15-minute mark if needed, but GDELT marks are :00/:15/:30/:45.
    minute = (start.minute // 15) * 15
    start = start.replace(minute=minute, second=0, microsecond=0)
    if start.astimezone(BERLIN).date() < day:
        start = start + timedelta(minutes=15)
    ids: list[str] = []
    cursor = start
    end = end_local.astimezone(timezone.utc)
    while cursor <= end:
        batch_id = batch_id_from_datetime(cursor)
        if berlin_day_from_batch_id(batch_id) == day:
            ids.append(batch_id)
        cursor += timedelta(minutes=15)
    return ids


def previous_berlin_day(now: datetime | None = None) -> date:
    current = now or datetime.now(timezone.utc)
    return current.astimezone(BERLIN).date() - timedelta(days=1)
