from nachrichten_sentiment.sentiment import score_from_probs, score_title


def test_score_is_positive_minus_negative_and_stays_in_range():
    result = score_from_probs(0.7, 0.2, 0.1)
    assert result.sentiment == 0.6
    assert result.label == "positive"
    assert result.p_positive == 0.7
    low = score_from_probs(0.0, 0.0, 1.0)
    assert low.sentiment == -1.0
    assert low.label == "negative"
    mid = score_from_probs(0.0, 1.0, 0.0)
    assert mid.sentiment == 0.0
    assert mid.label == "neutral"


class _Stub:
    def predict_proba(self, title: str) -> tuple[float, float, float]:
        assert title == "NVIDIA raises forecast"
        return (0.8, 0.15, 0.05)


def test_score_title_uses_model_probabilities():
    result = score_title("NVIDIA raises forecast", _Stub())
    assert result.sentiment == 0.75
    assert result.label == "positive"
