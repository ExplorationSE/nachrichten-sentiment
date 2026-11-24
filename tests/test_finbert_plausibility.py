import pytest

from nachrichten_sentiment.sentiment import FinBertModel, score_title

pytestmark = pytest.mark.finbert


def test_real_finbert_signs_and_labels_on_clear_headlines():
    model = FinBertModel("ProsusAI/finbert")
    positive = score_title("NVIDIA raises full-year revenue forecast", model)
    negative = score_title("NVIDIA faces federal investigation over accounting", model)
    assert positive.sentiment > 0
    assert positive.label == "positive"
    assert negative.sentiment < 0
    assert negative.label == "negative"
