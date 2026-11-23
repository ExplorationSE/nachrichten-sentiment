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


def test_workflow_checks_hour_before_ml_install_and_deploys_via_environment():
    import pytest

    yaml = pytest.importorskip("yaml")
    text = (ROOT / ".github" / "workflows" / "daily.yml").read_text(encoding="utf-8")
    flow = yaml.safe_load(text)
    collect = flow["jobs"]["collect"]
    steps = collect["steps"]
    runs = [step.get("run", "") for step in steps]
    hour_index = next(i for i, run in enumerate(runs) if "should_run_scheduled" in run)
    install_index = next(i for i, run in enumerate(runs) if "pip install" in run)
    assert hour_index < install_index
    assert "pip install" not in "".join(runs[: hour_index + 1])
    assert "--extra-index-url https://download.pytorch.org/whl/cpu" in runs[install_index]
    cache_steps = [s for s in steps if str(s.get("uses", "")).startswith("actions/cache@")]
    assert cache_steps and ".hf-cache" in cache_steps[0]["with"]["path"]
    commit = next(run for run in runs if "git push" in run)
    assert "git pull --rebase" in commit
    assert commit.index("git pull --rebase") < commit.index("git push")
    deploy = flow["jobs"]["deploy"]
    assert deploy["needs"] == "collect"
    assert deploy["environment"]["name"] == "github-pages"
    assert deploy["environment"]["url"] == "${{ steps.deployment.outputs.page_url }}"
    deploy_step = next(s for s in deploy["steps"] if str(s.get("uses", "")).startswith("actions/deploy-pages@"))
    assert deploy_step["id"] == "deployment"
