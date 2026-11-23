from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.filter_company import matches_company

NVDA = load_company("NVDA")


def test_match_on_organization_url_or_gkg_title():
    assert matches_company(NVDA, "NVIDIA Corporation", "", "https://reuters.com/a", None)
    assert matches_company(NVDA, "", "", "https://example.com/nvidia-earnings", None)
    assert matches_company(NVDA, "", "", "https://example.com/q?t=NVDA", None)
    assert matches_company(NVDA, "", "", "https://example.com/other", "nVidia raises outlook")
    assert matches_company(NVDA, "", "", "https://example.com/other", "Ticker NVDA jumps")


def test_no_match_on_gpu_only_or_nvda_substring_or_fetched_title_is_irrelevant():
    assert not matches_company(NVDA, "", "", "https://example.com/gpu-prices", None)
    assert not matches_company(NVDA, "", "", "https://example.com/cnvdata", None)
    # A fetched title is not passed in; only gkg_title counts.
    assert not matches_company(NVDA, "", "", "https://example.com/other", None)
