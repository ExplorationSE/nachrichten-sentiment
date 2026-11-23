from __future__ import annotations

from typing import Protocol

from nachrichten_sentiment.models import SentimentLabel, SentimentResult


class SentimentModel(Protocol):
    def predict_proba(self, title: str) -> tuple[float, float, float]:
        ...


def score_from_probs(p_positive: float, p_neutral: float, p_negative: float) -> SentimentResult:
    scores = {"positive": p_positive, "negative": p_negative, "neutral": p_neutral}
    label: SentimentLabel = max(("positive", "negative", "neutral"), key=lambda name: scores[name])
    return SentimentResult(
        sentiment=p_positive - p_negative,
        label=label,
        p_positive=p_positive,
        p_neutral=p_neutral,
        p_negative=p_negative,
    )


def score_title(title: str, model: SentimentModel) -> SentimentResult:
    p_positive, p_neutral, p_negative = model.predict_proba(title)
    return score_from_probs(p_positive, p_neutral, p_negative)
