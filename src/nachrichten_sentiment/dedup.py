from __future__ import annotations

from collections.abc import Iterable

from nachrichten_sentiment.models import Article
from nachrichten_sentiment.titles import titles_are_near_duplicates
from nachrichten_sentiment.urls import normalize_url


class UrlIndex:
    def __init__(self) -> None:
        self._first_id: dict[str, str] = {}

    def load_from_articles(self, articles: Iterable[Article]) -> None:
        for article in articles:
            key = article.url_normalized or normalize_url(article.url)
            self._first_id.setdefault(key, article.gkg_record_id)

    def keep(self, url: str, gkg_record_id: str) -> bool:
        key = normalize_url(url)
        if key in self._first_id:
            return False
        self._first_id[key] = gkg_record_id
        return True


def mark_near_duplicates(articles: list[Article], threshold: float = 0.90) -> list[Article]:
    ordered = sorted(articles, key=lambda item: (item.batch_utc, item.gkg_record_id))
    previous: list[Article] = []
    for article in ordered:
        article.is_near_duplicate = False
        article.near_duplicate_of = None
        if article.title_source == "missing" or not article.title.strip():
            previous.append(article)
            continue
        for candidate in previous:
            if candidate.day_berlin != article.day_berlin:
                continue
            if candidate.title_source == "missing" or not candidate.title.strip():
                continue
            if titles_are_near_duplicates(candidate.title, article.title, threshold):
                article.is_near_duplicate = True
                article.near_duplicate_of = candidate.near_duplicate_of or candidate.gkg_record_id
                break
        previous.append(article)
    return articles
