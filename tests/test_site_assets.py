from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_index_contains_se_aktien_colors_and_title():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert "Nachrichten-Sentiment" in html
    assert "Nvidia (NVDA)" in html
    for value in [
        "--bg:#0d1117",
        "--card:#161b22",
        "--line:#30363d",
        "--txt:#e6edf3",
        "--mut:#8b949e",
        "--up:#26a69a",
        "--down:#ef5350",
        "--acc:#58a6ff",
        "#1f2937",
        "#6e7681",
    ]:
        assert value in html
    assert "1 Monat" in html and "3 Monate" in html and "1 Jahr" in html
    assert "5 Jahre" in html and "Maximum" in html
    assert 'src="lwc.js"' in html
    assert 'src="chart_data.js"' in html
    assert 'src="app.js"' in html


def test_app_builds_headlines_safely_and_handles_load_errors():
    js = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js
    assert "createElement" in js
    assert "textContent" in js
    assert "safeHref" in js
    assert "noopener noreferrer" in js
    assert "Daten konnten nicht geladen werden." in js


def test_index_has_counting_mode_switch_with_default_without_near_duplicates():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert 'id="modes"' in html
    assert 'data-mode="alle"' in html and "Alle Nachrichten" in html
    assert 'data-mode="ohne"' in html and "Ohne Nahduplikate" in html
    assert 'role="radiogroup"' in html
    js = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    assert "resolveMode" in js
    assert "localStorage" in js
    assert "zaehlung" in js
    assert "aria-checked" in js


def test_index_has_line_candle_view_switch_with_default_line():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert 'id="views"' in html
    assert 'data-view="linie"' in html and ">Linie<" in html
    assert 'data-view="kerzen"' in html and ">Kerzen<" in html
    js = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    assert "resolveView" in js and "addCandlestickSeries" in js
    assert "toCandleSeries" in js and "formatCandle" in js
    assert "ansicht" in js
