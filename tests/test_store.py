import json
from pathlib import Path

from nachrichten_sentiment.models import Article, DailyRow
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.store import append_articles, load_articles, write_daily, write_headlines


def _article() -> Article:
    return Article(
        gkg_record_id="id-1",
        url="https://example.com/a",
        url_normalized="https://example.com/a",
        source_domain="example.com",
        title="NVIDIA raises forecast",
        title_source="gkg",
        batch_id="20150218230000",
        batch_utc="2015-02-18T23:00:00Z",
        day_berlin="2015-02-19",
        sentiment=0.5,
        sentiment_label="positive",
        p_positive=0.6,
        p_neutral=0.3,
        p_negative=0.1,
        is_near_duplicate=False,
        near_duplicate_of=None,
    )


def test_store_writes_month_daily_and_headline_files(tmp_path: Path):
    paths = ProjectPaths(tmp_path)
    article = _article()
    append_articles(paths, "NVDA", [article])
    month_file = tmp_path / "data" / "articles" / "nvda" / "2015-02.jsonl"
    assert month_file.exists()
    loaded = load_articles(paths, "NVDA")
    assert loaded[0].gkg_record_id == "id-1"
    assert loaded[0].sentiment_label == "positive"
    row = DailyRow("2015-02-19", 1, 1, 1, 0, 0, 0, 0.5, "complete")
    write_daily(paths, "NVDA", [row], "Nvidia")
    daily = json.loads((tmp_path / "site" / "data" / "nvda-daily.json").read_text(encoding="utf-8"))
    assert daily["ticker"] == "NVDA"
    assert daily["display_name"] == "Nvidia"
    assert daily["timezone"] == "Europe/Berlin"
    assert daily["days"][0]["count_positive"] == 1
    assert daily["days"][0]["count_neutral"] == 0
    assert daily["days"][0]["coverage"] == "complete"
    write_headlines(paths, "NVDA", [article])
    headlines = json.loads((tmp_path / "site" / "data" / "nvda" / "2015-02.json").read_text(encoding="utf-8"))
    assert headlines["2015-02-19"][0]["title"] == "NVIDIA raises forecast"
    assert headlines["2015-02-19"][0]["url"] == "https://example.com/a"
    assert headlines["2015-02-19"][0]["is_near_duplicate"] is False
