from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")


def should_run_scheduled(now_utc: datetime, event_name: str) -> bool:
    if event_name == "workflow_dispatch":
        return True
    current = now_utc.astimezone(BERLIN)
    return current.hour == 6
