from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from html.parser import HTMLParser


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
