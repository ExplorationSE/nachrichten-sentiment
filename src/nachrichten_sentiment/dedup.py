from __future__ import annotations

from collections.abc import Iterable

from nachrichten_sentiment.models import Article
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
