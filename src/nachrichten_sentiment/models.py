from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


TitleSource = Literal["gkg", "fetched", "missing"]
SentimentLabel = Literal["positive", "neutral", "negative"]
Coverage = Literal["complete", "gap"]
GapReason = Literal["source_missing"]


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
    gap_reason: Optional[GapReason] = None
    # Zählweise "alle Nachrichten": dieselben Größen über alle URL-eindeutigen Artikel inkl. Nahduplikate.
    count_positive_all: int = 0
    count_neutral_all: int = 0
    count_negative_all: int = 0
    count_without_sentiment_all: int = 0
    sentiment_mean_all: Optional[float] = None
    # Tageskerze aus den Mittelwerten je 15-Minuten-Satz (chronologisch): [Open, High, Low, Close, Anzahl Sätze mit Stimmungswert];
    # None, wenn kein Satz des Tages einen Stimmungswert hat. ohlc ohne, ohlc_all mit Nahduplikaten.
    ohlc: Optional[tuple[float, float, float, float, int]] = None
    ohlc_all: Optional[tuple[float, float, float, float, int]] = None


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
    # 15-Minuten-Sätze, die GDELT mit 404 beantwortet hat (dauerhaft an der Quelle fehlend).
    missing_at_source: list[str] = field(default_factory=list)
    # Berlin-Tage verarbeiteter Sätze, deren Ausgaben noch nicht neu aufgebaut wurden (übersteht Abbrüche).
    pending_rebuild_days: list[str] = field(default_factory=list)
    # Übersprungene Bereiche [[erster, letzter Satz]] eines späteren Starts (erstlauf --start), zum Nachholen.
    deferred_ranges: list[list[str]] = field(default_factory=list)
    # Schlüssel aus failed_title_fetches, die bereits in failed_titles.jsonl stehen (nur Laufzeit).
    persisted_failed_titles: set[str] = field(default_factory=set, repr=False, compare=False)
