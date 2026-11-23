from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


TitleSource = Literal["gkg", "fetched", "missing"]
SentimentLabel = Literal["positive", "neutral", "negative"]
Coverage = Literal["complete", "gap"]


@dataclass(frozen=True)
class CompanyConfig:
    ticker: str
    display_name: str
    name_substrings: tuple[str, ...]
    ticker_word: str


@dataclass
class Article:
    gkg_record_id: str
    url: str
    url_normalized: str
    source_domain: str
    title: str
    title_source: TitleSource
    batch_id: str
    batch_utc: str
    day_berlin: str
    sentiment: Optional[float]
    sentiment_label: Optional[SentimentLabel]
    p_positive: Optional[float]
    p_neutral: Optional[float]
    p_negative: Optional[float]
    is_near_duplicate: bool
    near_duplicate_of: Optional[str]


@dataclass
class DailyRow:
    date: str
    count_unique_url: int
    count_after_near_dup_collapse: int
    count_positive: int
    count_neutral: int
    count_negative: int
    count_without_sentiment: int
    sentiment_mean: Optional[float]
    coverage: Coverage


@dataclass(frozen=True)
class SentimentResult:
    sentiment: float
    label: SentimentLabel
    p_positive: float
    p_neutral: float
    p_negative: float


@dataclass
class ProgressState:
    last_success_batch_id: Optional[str]
    cursor_batch_id: Optional[str]
    open_gaps: list[str]
    failed_title_fetches: dict[str, str]
    successful_spans: list[list[str]] = field(default_factory=list)
