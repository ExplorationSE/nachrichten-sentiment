from pathlib import Path

import pytest

from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.models import Article, CompanyConfig, DailyRow
from nachrichten_sentiment.paths import ProjectPaths, default_root


def test_load_company_nvda_from_default_config():
    company = load_company("NVDA")
    assert company == CompanyConfig(
        ticker="NVDA",
        display_name="Nvidia",
        name_substrings=("nvidia",),
        ticker_word="nvda",
    )


def test_load_company_unknown_ticker_raises():
    with pytest.raises(KeyError):
        load_company("MSFT")


def test_project_paths_layout():
    root = Path("/tmp/ns-project-root")
    paths = ProjectPaths(root)
    assert paths.company_config_path == root / "config" / "companies.json"
    assert paths.progress_path == root / "data" / "state" / "progress.json"
    assert paths.gaps_log_path == root / "data" / "state" / "gaps.log"
    assert paths.articles_dir("NVDA") == root / "data" / "articles" / "nvda"
    assert paths.site_dir == root / "site"
    assert paths.site_data_dir == root / "site" / "data"
    assert paths.tmp_dir == root / "data" / "tmp"
    assert default_root() == Path(__file__).resolve().parents[1]


def test_article_and_daily_row_fields():
    article = Article(
        gkg_record_id="id-1",
        url="https://example.com/a",
        url_normalized="https://example.com/a",
        source_domain="example.com",
        title="NVIDIA raises forecast",
        title_source="gkg",
        batch_id="20150218230000",
        batch_utc="2015-02-18T23:00:00Z",
        day_berlin="2015-02-19",
        sentiment=0.8,
        sentiment_label="positive",
        p_positive=0.8,
        p_neutral=0.1,
        p_negative=0.1,
        is_near_duplicate=False,
        near_duplicate_of=None,
    )
    assert article.title_source == "gkg"
    row = DailyRow(
        date="2015-02-19",
        count_unique_url=0,
        count_after_near_dup_collapse=0,
        count_positive=0,
        count_neutral=0,
        count_negative=0,
        count_without_sentiment=0,
        sentiment_mean=None,
        coverage="complete",
    )
    assert row.coverage == "complete"
    assert row.sentiment_mean is None
