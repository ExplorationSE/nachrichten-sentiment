from __future__ import annotations

import re
import time
import unicodedata
import urllib.request
from dataclasses import dataclass
from difflib import SequenceMatcher
from html.parser import HTMLParser
from typing import Callable, Literal, Optional

from nachrichten_sentiment.urls import normalize_url


def normalize_title(title: str) -> str:
    text = unicodedata.normalize("NFKC", title)
    text = re.split(r"\s+[\|\u2013]\s+", text, maxsplit=1)[0]
    text = " ".join(text.lower().split())
    return text


def titles_are_near_duplicates(a: str, b: str, threshold: float = 0.90) -> bool:
    left = normalize_title(a)
    right = normalize_title(b)
    if not left or not right:
        return False
    if left == right:
        return True
    return SequenceMatcher(None, left, right).ratio() >= threshold


class _TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.title_chunks: list[str] = []
        self.og_title: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        mapping = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() == "meta" and mapping.get("property", "").lower() == "og:title":
            self.og_title = mapping.get("content") or None

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_chunks.append(data)


def parse_html_title(html: str) -> str | None:
    parser = _TitleParser()
    parser.feed(html)
    if parser.og_title and parser.og_title.strip():
        return parser.og_title.strip()
    title = "".join(parser.title_chunks).strip()
    return title or None


@dataclass(frozen=True)
class FetchResult:
    title: Optional[str]
    source: Literal["fetched", "missing"]
    error: Optional[str]


TitleOpener = Callable[[str, float], str]


def fetch_title(
    url: str,
    opener: TitleOpener,
    failed_cache: dict[str, str],
    timeout_seconds: float = 10.0,
) -> FetchResult:
    key = normalize_url(url)
    if key in failed_cache:
        return FetchResult(title=None, source="missing", error=failed_cache[key])
    try:
        html = opener(url, timeout_seconds)
        title = parse_html_title(html)
        if not title:
            failed_cache[key] = "no title in html"
            return FetchResult(title=None, source="missing", error=failed_cache[key])
        return FetchResult(title=title, source="fetched", error=None)
    except Exception as exc:  # network, timeout, HTTP errors from the opener
        failed_cache[key] = str(exc)
        return FetchResult(title=None, source="missing", error=str(exc))


def http_title_opener(url: str, timeout_seconds: float, pause_seconds: float = 0.3) -> str:
    if pause_seconds:
        time.sleep(pause_seconds)
    request = urllib.request.Request(url, headers={"User-Agent": "NachrichtenSentiment/0.1"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="replace")
