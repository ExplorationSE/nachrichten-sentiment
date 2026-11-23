from __future__ import annotations

from collections.abc import Iterable
from difflib import SequenceMatcher

from nachrichten_sentiment.models import Article
from nachrichten_sentiment.titles import normalize_title
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


def _has_title(article: Article) -> bool:
    return article.title_source != "missing" and bool(article.title.strip())


def _mark_day(day_articles: list[Article], threshold: float) -> None:
    """Vergleicht nur Artikel desselben Berlin-Tages; günstige Obergrenzen filtern vor ratio()."""
    ordered = sorted(day_articles, key=lambda item: (item.batch_utc, item.gkg_record_id))
    previous: list[tuple[Article, str]] = []
    matcher = SequenceMatcher(None)
    for article in ordered:
        article.is_near_duplicate = False
        article.near_duplicate_of = None
        if not _has_title(article):
            continue
        current = normalize_title(article.title)
        if not current:
            continue
        # seq2 wird von SequenceMatcher zwischengespeichert, daher den aktuellen Titel dort setzen.
        matcher.set_seq2(current)
        for candidate, candidate_title in previous:
            if candidate_title != current:
                matcher.set_seq1(candidate_title)
                if matcher.real_quick_ratio() < threshold or matcher.quick_ratio() < threshold:
                    continue
                if matcher.ratio() < threshold:
                    continue
            article.is_near_duplicate = True
            article.near_duplicate_of = candidate.near_duplicate_of or candidate.gkg_record_id
            break
        previous.append((article, current))


def group_by_day(articles: Iterable[Article]) -> dict[str, list[Article]]:
    grouped: dict[str, list[Article]] = {}
    for article in articles:
        grouped.setdefault(article.day_berlin, []).append(article)
    return grouped


def mark_near_duplicates(
    articles: list[Article],
    threshold: float = 0.90,
    days: Iterable[str] | None = None,
) -> list[Article]:
    """Setzt Nahduplikat-Flags tageweise neu; mit ``days`` nur für diese Berlin-Tage (alle Artikel des Tages)."""
    grouped = group_by_day(articles)
    wanted = grouped.keys() if days is None else [day for day in days if day in grouped]
    for day in wanted:
        _mark_day(grouped[day], threshold)
    return articles
