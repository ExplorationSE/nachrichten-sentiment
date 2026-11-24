from nachrichten_sentiment.titles import normalize_title, parse_html_title, titles_are_near_duplicates


def test_normalize_title_strips_site_suffix_and_case():
    assert normalize_title("NVIDIA Beats  |  Reuters") == "nvidia beats"
    assert normalize_title("NVIDIA Beats – Reuters") == "nvidia beats"


def test_near_duplicate_threshold_is_0_90():
    a = "NVIDIA raises full-year revenue forecast"
    b = "NVIDIA raises full-year revenue forecast!"
    c = "Completely different headline about copper mines"
    assert titles_are_near_duplicates(a, b, 0.90) is True
    assert titles_are_near_duplicates(a, c, 0.90) is False


def test_parse_html_title_prefers_og_title():
    html = """<html><head>
    <meta property="og:title" content="OG NVIDIA title">
    <title>Fallback title</title>
    </head></html>"""
    assert parse_html_title(html) == "OG NVIDIA title"
    assert parse_html_title("<html><title> Only title </title></html>") == "Only title"
    assert parse_html_title("<html><body>none</body></html>") is None
