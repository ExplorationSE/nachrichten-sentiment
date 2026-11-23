from __future__ import annotations

import json
from dataclasses import asdict

from nachrichten_sentiment.models import Article, DailyRow
from nachrichten_sentiment.paths import ProjectPaths


def article_to_dict(article: Article) -> dict:
    return asdict(article)


def article_from_dict(raw: dict) -> Article:
    return Article(**raw)


def daily_row_to_dict(row: DailyRow) -> dict:
    return asdict(row)


def append_articles(paths: ProjectPaths, ticker: str, articles: list[Article]) -> None:
    by_month: dict[str, list[Article]] = {}
    for article in articles:
        month = article.day_berlin[:7]
        by_month.setdefault(month, []).append(article)
    directory = paths.articles_dir(ticker)
    directory.mkdir(parents=True, exist_ok=True)
    for month, rows in by_month.items():
        target = directory / f"{month}.jsonl"
        with target.open("a", encoding="utf-8") as handle:
            for article in rows:
                handle.write(json.dumps(article_to_dict(article), ensure_ascii=False) + "\n")


def load_articles(paths: ProjectPaths, ticker: str) -> list[Article]:
    directory = paths.articles_dir(ticker)
    if not directory.exists():
        return []
    articles: list[Article] = []
    for file in sorted(directory.glob("*.jsonl")):
        for line in file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                articles.append(article_from_dict(json.loads(line)))
    return articles


def write_daily(paths: ProjectPaths, ticker: str, rows: list[DailyRow], display_name: str) -> None:
    paths.site_data_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "ticker": ticker.upper(),
        "display_name": display_name,
        "timezone": "Europe/Berlin",
        "days": [daily_row_to_dict(row) for row in rows],
    }
    target = paths.site_data_dir / f"{ticker.lower()}-daily.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_headlines(paths: ProjectPaths, ticker: str, articles: list[Article]) -> None:
    grouped: dict[str, dict[str, list[dict]]] = {}
    for article in articles:
        month = article.day_berlin[:7]
        day_map = grouped.setdefault(month, {})
        day_map.setdefault(article.day_berlin, []).append(
            {
                "gkg_record_id": article.gkg_record_id,
                "title": article.title,
                "url": article.url,
                "sentiment": article.sentiment,
                "sentiment_label": article.sentiment_label,
                "title_source": article.title_source,
                "is_near_duplicate": article.is_near_duplicate,
                "near_duplicate_of": article.near_duplicate_of,
            }
        )
    root = paths.site_data_dir / ticker.lower()
    root.mkdir(parents=True, exist_ok=True)
    for month, days in grouped.items():
        (root / f"{month}.json").write_text(json.dumps(days, ensure_ascii=False, indent=2), encoding="utf-8")
