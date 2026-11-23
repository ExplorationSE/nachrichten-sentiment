from datetime import datetime, timezone
from pathlib import Path

from nachrichten_sentiment.schedule import should_run_scheduled

ROOT = Path(__file__).resolve().parents[1]


def test_should_run_only_at_06_berlin_or_manual():
    # 05:00 UTC = 06:00 CET (Winter 2026-01-15)
    winter = datetime(2026, 1, 15, 5, 0, tzinfo=timezone.utc)
    assert should_run_scheduled(winter, "schedule") is True
    # 04:00 UTC = 05:00 CET, nicht ausführen
    assert should_run_scheduled(datetime(2026, 1, 15, 4, 0, tzinfo=timezone.utc), "schedule") is False
    # 04:00 UTC = 06:00 CEST (Sommer 2026-07-15)
    summer = datetime(2026, 7, 15, 4, 0, tzinfo=timezone.utc)
    assert should_run_scheduled(summer, "schedule") is True
    assert should_run_scheduled(datetime(2026, 7, 15, 5, 0, tzinfo=timezone.utc), "schedule") is False
    assert should_run_scheduled(datetime(2026, 1, 15, 4, 0, tzinfo=timezone.utc), "workflow_dispatch") is True


def test_workflow_has_both_cron_entries_and_conditional_deploy():
    text = (ROOT / ".github" / "workflows" / "daily.yml").read_text(encoding="utf-8")
    assert "cron: '0 4 * * *'" in text
    assert "cron: '0 5 * * *'" in text
    assert "workflow_dispatch" in text
    assert "should_run_scheduled" in text
    assert "python -m nachrichten_sentiment tageslauf" in text
    assert "actions/deploy-pages" in text
    assert "if: success()" in text
    assert "site/" in text
