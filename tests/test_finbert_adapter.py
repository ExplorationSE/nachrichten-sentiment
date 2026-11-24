from nachrichten_sentiment.sentiment import FinBertModel, score_title


class _FakePipeline:
    def __init__(self, mapping):
        self.mapping = mapping

    def __call__(self, title, **kwargs):
        assert kwargs.get("top_k") is None or kwargs.get("return_all_scores")
        return [[{"label": name, "score": value} for name, value in self.mapping.items()]]


def test_finbert_model_maps_labels_to_positive_neutral_negative_order(monkeypatch):
    def fake_pipeline(*args, **kwargs):
        return _FakePipeline({"negative": 0.1, "neutral": 0.2, "positive": 0.7})

    monkeypatch.setattr("nachrichten_sentiment.sentiment._transformers_pipeline", fake_pipeline)
    model = FinBertModel()
    result = score_title("NVIDIA raises forecast", model)
    assert result.p_positive == 0.7
    assert result.p_neutral == 0.2
    assert result.p_negative == 0.1
    assert result.sentiment == 0.6
    assert result.label == "positive"


def test_finbert_truncates_long_inputs_to_512_tokens(monkeypatch):
    seen: dict = {}

    class _Recording(_FakePipeline):
        def __call__(self, title, **kwargs):
            seen.update(kwargs)
            return super().__call__(title, **kwargs)

    monkeypatch.setattr(
        "nachrichten_sentiment.sentiment._transformers_pipeline",
        lambda *a, **k: _Recording({"negative": 0.1, "neutral": 0.2, "positive": 0.7}),
    )
    FinBertModel().predict_proba("NVIDIA " * 2000)
    assert seen.get("truncation") is True
    assert seen.get("max_length") == 512
