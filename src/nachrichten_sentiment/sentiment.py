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


def _transformers_pipeline(*args, **kwargs):
    from transformers import pipeline

    return pipeline(*args, **kwargs)


class FinBertModel:
    def __init__(self, model_name: str = "ProsusAI/finbert") -> None:
        self._pipe = _transformers_pipeline(
            "text-classification",
            model=model_name,
            top_k=None,
        )

    def predict_proba(self, title: str) -> tuple[float, float, float]:
        rows = self._pipe(title, top_k=None)
        items = rows[0] if rows and isinstance(rows[0], list) else rows
        mapped = {str(item["label"]).lower(): float(item["score"]) for item in items}
        return (
            mapped.get("positive", 0.0),
            mapped.get("neutral", 0.0),
            mapped.get("negative", 0.0),
        )
