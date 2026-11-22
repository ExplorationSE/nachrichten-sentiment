# Nachrichten-Sentiment Implementierungsplan

> **Für ausführende Agenten:** PFLICHT-SKILL: superpowers:subagent-driven-development (empfohlen) oder superpowers:executing-plans, Aufgabe für Aufgabe. Schritte mit Checkbox (`- [ ]`).

**Ziel:** Ein eigenständiges Werkzeug sammelt taggenau Nvidia-Nachrichten aus GDELT GKG 2.1 ab dem 19. Februar 2015, bewertet Titel mit FinBERT und zeigt positive und negative Anzahlen sowie die Stimmung auf einer statischen Webseite.

**Architektur:** Ein Python-Datensammler lädt 15-Minuten-GKG-Dateien, filtert, dedupliziert, lädt fehlende Titel nach, bewertet und schreibt Monats- und Tagesdateien; der Stand in `data/state/progress.json` macht Erstlauf und Tageslauf fortsetzbar. Eine GitHub Action startet den Tageslauf um 06:00 Europe/Berlin und veröffentlicht nur bei Erfolg den Ordner `site/` auf GitHub Pages. Die Webseite lädt vorbereitete JSON-Dateien und zeichnet divergierende Balken sowie die Stimmungslinie mit lokal eingebundenem Lightweight Charts.

**Technik:** Python 3.11+, pytest, requests, transformers und torch (nur Extra `ml` für FinBERT), TradingView Lightweight Charts (lokal als `site/lwc.js`), GitHub Actions und GitHub Pages. Keine Datenbank, kein eigener Server.

## Globale Vorgaben

- Eigenständiges Werkzeug, nicht Teil der App SE Aktien; Lieferumfang nur Nvidia (NVDA); Konfiguration so vorbereiten, dass später weitere Aktien ergänzt werden können.
- Quelle ausschließlich der englische GDELT-2.0-Strom, Datei `https://data.gdeltproject.org/gdeltv2/YYYYMMDDHHMMSS.gkg.csv.zip` (GKG 2.1, tabgetrennt); Manifest-URLs mit `http://` werden per HTTPS geladen; Events/Mentions und der Übersetzungsstrom werden nicht verwendet.
- Erste GKG-Datei: `20150218230000.gkg.csv.zip` (18. Februar 2015, 23:00 UTC); erster dargestellter Kalendertag: 19. Februar 2015 in der Zeitzone Europe/Berlin.
- Ein Tag ist der Kalendertag Europe/Berlin aus dem UTC-Dateinamen der 15-Minuten-Datei; `PAGE_PRECISEPUBTIMESTAMP` wird nicht verwendet.
- Stimmungswert = \(P(\text{positiv}) - P(\text{negativ})\), Intervall \([-1, +1]\); Modell ProsusAI/finbert, lokal, nur auf verfügbaren Titeln; Klasse nach argmax (`positive` / `neutral` / `negative`).
- GDELT-eigener Tonwert (`V1.5TONE` / GCAM) und große KI-Sprachmodelle werden nicht verwendet.
- Nahduplikat-Schwelle: `difflib.SequenceMatcher.ratio` mindestens 0,90 auf normalisierten Titeln desselben Berlin-Tages; Artikel ohne Titel werden nicht gruppiert.
- Alle Diagramm- und Tooltip-Anzahlen beziehen sich auf URL-eindeutige Artikel; Balken zeigen nur `count_positive` (grün nach oben, `--up` `#26a69a`) und `count_negative` (rot nach unten, `--down` `#ef5350`); Gesamtzahl und Neutralzahl stehen im Tooltip, nicht als Balken.
- CSS-Farben wörtlich: `--bg` `#0d1117`, `--card` `#161b22`, `--line` `#30363d`, `--txt` `#e6edf3`, `--mut` `#8b949e`, `--up` `#26a69a`, `--down` `#ef5350`, `--acc` `#58a6ff`, aktiver Chip-Hintergrund `#1f2937`, Fußzeile `#6e7681`.
- Arbeitstitel der Seite: „Nachrichten-Sentiment“, Untertitel „Nvidia (NVDA)“; Schrift `system-ui, -apple-system, Segoe UI, Roboto, sans-serif`; Zeitraum-Chips: 1 Monat, 3 Monate, 1 Jahr, 5 Jahre, Maximum.
- Täglicher Lauf um 06:00 Europe/Berlin per GitHub Action, zusätzlich `workflow_dispatch`; bei Fehlschlag keine neue Pages-Veröffentlichung; E-Mail über die GitHub-Actions-Benachrichtigung an ExplorationSE.
- Erstlauf lokal oder in mehreren fortsetzbaren Läufen; nach jeder erfolgreich verarbeiteten 15-Minuten-Datei Fortschritt schreiben.
- Nicht im Umfang: weitere Aktien im Lieferumfang, Kursdaten, Handelssignale, LLM-Bewertung, übersetzter GDELT-Strom, eigener Server oder Datenbank.

---

## Dateistruktur

Jede Datei hat eine Verantwortung; der ausführende Agent legt Dateien erst in der Aufgabe an, die sie braucht.

| Pfad | Verantwortung |
| --- | --- |
| `pyproject.toml` | Paketmetadaten, Abhängigkeiten, pytest-Marker |
| `.gitignore` | Virtuelle Umgebungen, Caches, rohe GDELT-Downloads |
| `config/companies.json` | Ticker, Anzeigename und Suchbegriffe (nur `NVDA` im Lieferumfang) |
| `README.md` | Zweck, CLI, Erstlauf, Action, Hinweise zu Lücken |
| `src/nachrichten_sentiment/__init__.py` | Paketmarkierung |
| `src/nachrichten_sentiment/models.py` | Dataclasses `CompanyConfig`, `Article`, `DailyRow`, `SentimentResult`, `ProgressState` |
| `src/nachrichten_sentiment/paths.py` | Projektpfade (`data/`, `site/`, `progress.json`, `gaps.log`) |
| `src/nachrichten_sentiment/companies.py` | `load_company(ticker, path) -> CompanyConfig` |
| `src/nachrichten_sentiment/timeutil.py` | Batch-IDs, Berlin-Tag, erwartete 15-Minuten-Sätze inkl. Sommerzeit |
| `src/nachrichten_sentiment/urls.py` | `normalize_url(url) -> str` |
| `src/nachrichten_sentiment/gkg.py` | GKG-2.1-Spalten, `parse_gkg_line`, `extract_page_title` |
| `src/nachrichten_sentiment/filter_company.py` | `matches_company(...)` (Nvidia-Filter ohne Titelnachladen) |
| `src/nachrichten_sentiment/titles.py` | Titel normalisieren, HTML-Titel parsen, `fetch_title` |
| `src/nachrichten_sentiment/dedup.py` | `UrlIndex`, `mark_near_duplicates` |
| `src/nachrichten_sentiment/sentiment.py` | `score_from_probs`, Protokoll `SentimentModel`, `FinBertModel` |
| `src/nachrichten_sentiment/daily.py` | `aggregate_daily` |
| `src/nachrichten_sentiment/progress.py` | `progress.json` und `gaps.log` laden, speichern, Fortsetzen |
| `src/nachrichten_sentiment/download.py` | GKG-ZIP per HTTPS mit Wiederholversuchen |
| `src/nachrichten_sentiment/store.py` | Monats-JSONL, Tages-JSON, Schlagzeilen-JSON |
| `src/nachrichten_sentiment/pipeline.py` | Einen Satz / den Tageslauf / den Erstlauf verarbeiten |
| `src/nachrichten_sentiment/schedule.py` | `should_run_scheduled` für 06:00 Europe/Berlin |
| `src/nachrichten_sentiment/cli.py` | `python -m nachrichten_sentiment` mit `erstlauf`, `tageslauf`, `probelauf` |
| `src/nachrichten_sentiment/__main__.py` | Einstieg `python -m nachrichten_sentiment` |
| `tests/` | Eine Testdatei je Komponente, Fixture-GKG für den Probelauf |
| `site/index.html` | Seite, CSS-Variablen, Zeitraum-Chips, Listenbereich |
| `site/app.js` | Tooltip, Chart-Daten, Zoom, Nachladen der Schlagzeilen |
| `site/chart_data.js` | Testbare reine Funktionen für Tooltip, Serien und Zeitraum |
| `site/lwc.js` | Lokal eingebundenes Lightweight Charts (Vendor-Datei) |
| `site/data/` | Erzeugte `nvda-daily.json` und `nvda/YYYY-MM.json` |
| `data/articles/nvda/` | `YYYY-MM.jsonl` (Bestand) |
| `data/state/progress.json` | Fortschritt, Lücken, fehlgeschlagene Titelnachladeversuche |
| `data/state/gaps.log` | Nur Anhangprotokoll |
| `data/tmp/` | Kurzlebige Downloads, nicht ins Git |
| `.github/workflows/daily.yml` | Zeitplan, Tageslauf, bedingtes Pages-Deploy |

---

### Aufgabe 1: Projektgerüst, Pfade, Firmenkonfiguration und Datenmodell

**Dateien:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `config/companies.json`
- Create: `src/nachrichten_sentiment/__init__.py`
- Create: `src/nachrichten_sentiment/models.py`
- Create: `src/nachrichten_sentiment/paths.py`
- Create: `src/nachrichten_sentiment/companies.py`
- Test: `tests/test_companies.py`

**Schnittstellen:**
- Nutzt: nichts.
- Liefert: `CompanyConfig(ticker: str, display_name: str, name_substrings: tuple[str, ...], ticker_word: str)`; `Article` und `DailyRow` wie unten; `ProjectPaths(root: Path)` mit Eigenschaften `data_dir`, `articles_dir(ticker: str) -> Path`, `state_dir`, `progress_path`, `gaps_log_path`, `site_dir`, `site_data_dir`, `company_config_path`, `tmp_dir`; `load_company(ticker: str, path: Path | None = None) -> CompanyConfig`; `default_root() -> Path`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_companies.py
from pathlib import Path

import pytest

from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.models import Article, CompanyConfig, DailyRow
from nachrichten_sentiment.paths import ProjectPaths, default_root


def test_load_company_nvda_from_default_config():
    company = load_company("NVDA")
    assert company == CompanyConfig(
        ticker="NVDA",
        display_name="Nvidia",
        name_substrings=("nvidia",),
        ticker_word="nvda",
    )


def test_load_company_unknown_ticker_raises():
    with pytest.raises(KeyError):
        load_company("MSFT")


def test_project_paths_layout():
    root = Path("/workspace/nachrichten-sentiment")
    paths = ProjectPaths(root)
    assert paths.company_config_path == root / "config" / "companies.json"
    assert paths.progress_path == root / "data" / "state" / "progress.json"
    assert paths.gaps_log_path == root / "data" / "state" / "gaps.log"
    assert paths.articles_dir("NVDA") == root / "data" / "articles" / "nvda"
    assert paths.site_dir == root / "site"
    assert paths.site_data_dir == root / "site" / "data"
    assert paths.tmp_dir == root / "data" / "tmp"
    assert default_root() == root


def test_article_and_daily_row_fields():
    article = Article(
        gkg_record_id="id-1",
        url="https://example.com/a",
        url_normalized="https://example.com/a",
        source_domain="example.com",
        title="NVIDIA raises forecast",
        title_source="gkg",
        batch_id="20150218230000",
        batch_utc="2015-02-18T23:00:00Z",
        day_berlin="2015-02-19",
        sentiment=0.8,
        sentiment_label="positive",
        p_positive=0.8,
        p_neutral=0.1,
        p_negative=0.1,
        is_near_duplicate=False,
        near_duplicate_of=None,
    )
    assert article.title_source == "gkg"
    row = DailyRow(
        date="2015-02-19",
        count_unique_url=0,
        count_after_near_dup_collapse=0,
        count_positive=0,
        count_neutral=0,
        count_negative=0,
        count_without_sentiment=0,
        sentiment_mean=None,
        coverage="complete",
    )
    assert row.coverage == "complete"
    assert row.sentiment_mean is None
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `python3 -m pip install -e ".[dev]" && pytest tests/test_companies.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment'` oder fehlendem `pyproject.toml`.

- [ ] **Schritt 3: Minimale Implementierung**

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "nachrichten-sentiment"
version = "0.1.0"
description = "Nachrichten-Sentiment für Aktien (Nvidia)"
requires-python = ">=3.11"
dependencies = ["requests>=2.31"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]
ml = ["transformers>=4.40", "torch"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
  "finbert: needs the local ProsusAI/finbert model and the ml extra",
]
```

`.gitignore`:

```
.venv/
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
dist/
data/tmp/
.hf-cache/
```

`config/companies.json`:

```json
{
  "NVDA": {
    "ticker": "NVDA",
    "display_name": "Nvidia",
    "name_substrings": ["nvidia"],
    "ticker_word": "nvda"
  }
}
```

`src/nachrichten_sentiment/__init__.py` bleibt leer.

`src/nachrichten_sentiment/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
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
```

`src/nachrichten_sentiment/paths.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def default_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def company_config_path(self) -> Path:
        return self.root / "config" / "companies.json"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def state_dir(self) -> Path:
        return self.data_dir / "state"

    @property
    def progress_path(self) -> Path:
        return self.state_dir / "progress.json"

    @property
    def gaps_log_path(self) -> Path:
        return self.state_dir / "gaps.log"

    def articles_dir(self, ticker: str) -> Path:
        return self.data_dir / "articles" / ticker.lower()

    @property
    def site_dir(self) -> Path:
        return self.root / "site"

    @property
    def site_data_dir(self) -> Path:
        return self.site_dir / "data"

    @property
    def tmp_dir(self) -> Path:
        return self.data_dir / "tmp"
```

`src/nachrichten_sentiment/companies.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from nachrichten_sentiment.models import CompanyConfig
from nachrichten_sentiment.paths import default_root


def load_company(ticker: str, path: Path | None = None) -> CompanyConfig:
    config_path = path or (default_root() / "config" / "companies.json")
    data = json.loads(config_path.read_text(encoding="utf-8"))
    key = ticker.upper()
    if key not in data:
        raise KeyError(ticker)
    raw = data[key]
    return CompanyConfig(
        ticker=raw["ticker"],
        display_name=raw["display_name"],
        name_substrings=tuple(s.lower() for s in raw["name_substrings"]),
        ticker_word=str(raw["ticker_word"]).lower(),
    )
```

Leere Verzeichnisse mit `.gitkeep` anlegen: `data/state/.gitkeep`, `data/articles/nvda/.gitkeep`, `data/tmp/.gitkeep`, `site/data/nvda/.gitkeep`.

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `python3 -m pip install -e ".[dev]" && pytest tests/test_companies.py -v`

Expected: PASS, vier Tests.

- [ ] **Schritt 5: Commit**

```bash
git add pyproject.toml .gitignore config/companies.json src/nachrichten_sentiment/__init__.py src/nachrichten_sentiment/models.py src/nachrichten_sentiment/paths.py src/nachrichten_sentiment/companies.py tests/test_companies.py data/state/.gitkeep data/articles/nvda/.gitkeep data/tmp/.gitkeep site/data/nvda/.gitkeep
git commit -m "feat: Projektgerüst, Pfade, NVDA-Konfiguration und Datenmodell"
```

### Aufgabe 2: Berlin-Kalendertag und 15-Minuten-Sätze

**Dateien:**
- Create: `src/nachrichten_sentiment/timeutil.py`
- Test: `tests/test_timeutil.py`

**Schnittstellen:**
- Nutzt: nichts aus Aufgabe 1 außer dem installierten Paket.
- Liefert: Konstanten `FIRST_BATCH_ID: str = "20150218230000"` und `FIRST_BERLIN_DAY` als `datetime.date(2015, 2, 19)`; `datetime_from_batch_id(batch_id: str) -> datetime` (UTC); `batch_id_from_datetime(dt: datetime) -> str`; `berlin_day_from_batch_id(batch_id: str) -> date`; `expected_batch_ids_for_berlin_day(day: date) -> list[str]`; `next_batch_id(batch_id: str) -> str`; `iter_batch_ids(start_id: str, end_id: str) -> list[str]` (beide Grenzen inklusive); `previous_berlin_day(now: datetime | None = None) -> date`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_timeutil.py
from datetime import date, datetime, timezone

from nachrichten_sentiment.timeutil import (
    FIRST_BATCH_ID,
    FIRST_BERLIN_DAY,
    batch_id_from_datetime,
    berlin_day_from_batch_id,
    datetime_from_batch_id,
    expected_batch_ids_for_berlin_day,
    iter_batch_ids,
    next_batch_id,
    previous_berlin_day,
)


def test_first_batch_is_berlin_19_february_2015():
    assert FIRST_BATCH_ID == "20150218230000"
    assert FIRST_BERLIN_DAY == date(2015, 2, 19)
    assert berlin_day_from_batch_id(FIRST_BATCH_ID) == date(2015, 2, 19)
    assert datetime_from_batch_id(FIRST_BATCH_ID) == datetime(2015, 2, 18, 23, 0, 0, tzinfo=timezone.utc)


def test_expected_batches_regular_winter_day_has_96():
    ids = expected_batch_ids_for_berlin_day(date(2015, 2, 19))
    assert len(ids) == 96
    assert ids[0] == "20150218230000"
    assert ids[-1] == "20150219224500"
    assert berlin_day_from_batch_id(ids[-1]) == date(2015, 2, 19)
    assert berlin_day_from_batch_id(next_batch_id(ids[-1])) == date(2015, 2, 20)


def test_expected_batches_follow_european_dst():
    spring = expected_batch_ids_for_berlin_day(date(2026, 3, 29))  # 23-Stunden-Tag
    autumn = expected_batch_ids_for_berlin_day(date(2026, 10, 25))  # 25-Stunden-Tag
    assert len(spring) == 92
    assert len(autumn) == 100
    assert all(berlin_day_from_batch_id(i) == date(2026, 3, 29) for i in spring)
    assert all(berlin_day_from_batch_id(i) == date(2026, 10, 25) for i in autumn)


def test_iter_and_previous_day():
    ids = iter_batch_ids("20150218230000", "20150218233000")
    assert ids == ["20150218230000", "20150218231500", "20150218233000"]
    now = datetime(2026, 11, 22, 8, 0, tzinfo=timezone.utc)  # 09:00 Europe/Berlin
    assert previous_berlin_day(now) == date(2026, 11, 21)
    assert batch_id_from_datetime(datetime(2015, 2, 18, 23, 0, tzinfo=timezone.utc)) == "20150218230000"
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_timeutil.py -v`

Expected: FAIL mit `ImportError` oder `ModuleNotFoundError: cannot import name 'FIRST_BATCH_ID'`.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/timeutil.py
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
FIRST_BATCH_ID = "20150218230000"
FIRST_BERLIN_DAY = date(2015, 2, 19)


def datetime_from_batch_id(batch_id: str) -> datetime:
    return datetime.strptime(batch_id, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def batch_id_from_datetime(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")


def berlin_day_from_batch_id(batch_id: str) -> date:
    return datetime_from_batch_id(batch_id).astimezone(BERLIN).date()


def next_batch_id(batch_id: str) -> str:
    return batch_id_from_datetime(datetime_from_batch_id(batch_id) + timedelta(minutes=15))


def iter_batch_ids(start_id: str, end_id: str) -> list[str]:
    ids: list[str] = []
    current = start_id
    while current <= end_id:
        ids.append(current)
        current = next_batch_id(current)
    return ids


def expected_batch_ids_for_berlin_day(day: date) -> list[str]:
    start_local = datetime(day.year, day.month, day.day, 0, 0, tzinfo=BERLIN)
    end_local = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=BERLIN)
    start = start_local.astimezone(timezone.utc)
    # Round up to the next 15-minute mark if needed, but GDELT marks are :00/:15/:30/:45.
    minute = (start.minute // 15) * 15
    start = start.replace(minute=minute, second=0, microsecond=0)
    if start.astimezone(BERLIN).date() < day:
        start = start + timedelta(minutes=15)
    ids: list[str] = []
    cursor = start
    end = end_local.astimezone(timezone.utc)
    while cursor <= end:
        batch_id = batch_id_from_datetime(cursor)
        if berlin_day_from_batch_id(batch_id) == day:
            ids.append(batch_id)
        cursor += timedelta(minutes=15)
    return ids


def previous_berlin_day(now: datetime | None = None) -> date:
    current = now or datetime.now(timezone.utc)
    return current.astimezone(BERLIN).date() - timedelta(days=1)
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_timeutil.py -v`

Expected: PASS, vier Tests.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/timeutil.py tests/test_timeutil.py
git commit -m "feat: Berlin-Kalendertag und erwartete GDELT-15-Minuten-Sätze"
```

### Aufgabe 3: URL-Normalisierung

**Dateien:**
- Create: `src/nachrichten_sentiment/urls.py`
- Test: `tests/test_urls.py`

**Schnittstellen:**
- Nutzt: nichts.
- Liefert: `normalize_url(url: str) -> str` (Host klein, kein abschließender Schrägstrich, ohne Query-Parameter `utm_*`, `fbclid` und `gclid`).

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_urls.py
from nachrichten_sentiment.urls import normalize_url


def test_normalize_url_lowercases_host_and_strips_slash_and_tracking():
    raw = "HTTPS://Example.COM/Path/?utm_source=x&id=1&fbclid=abc&gclid=zzz"
    assert normalize_url(raw) == "https://example.com/Path?id=1"


def test_normalize_url_strips_only_trailing_slash_on_path():
    assert normalize_url("https://example.com/") == "https://example.com"
    assert normalize_url("https://example.com/a/") == "https://example.com/a"
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_urls.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.urls'`.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/urls.py
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_DROP_PARAMS = {"fbclid", "gclid"}


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _DROP_PARAMS and not key.lower().startswith("utm_")
    ]
    return urlunparse((scheme, netloc, path, "", urlencode(query, doseq=True), ""))
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_urls.py -v`

Expected: PASS, zwei Tests.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/urls.py tests/test_urls.py
git commit -m "feat: URL-Normalisierung ohne Tracking-Parameter"
```

### Aufgabe 4: GKG-2.1-Zeile parsen und PAGE_TITLE extrahieren

**Dateien:**
- Create: `src/nachrichten_sentiment/gkg.py`
- Test: `tests/test_gkg.py`

**Schnittstellen:**
- Nutzt: `normalize_url(url: str) -> str` aus Aufgabe 3 nicht unmittelbar (URL bleibt roh im Record; Normalisierung folgt im Filter/Dedup).
- Liefert: `GkgRecord(gkg_record_id: str, batch_id: str, source_collection_id: int, source_domain: str, url: str, organizations: str, enhanced_organizations: str, extras: str, page_title: str | None)`; `COL_RECORD_ID = 0`, `COL_DATE = 1`, `COL_SOURCE_COLLECTION = 2`, `COL_SOURCE_NAME = 3`, `COL_URL = 4`, `COL_ORGANIZATIONS = 13`, `COL_ENHANCED_ORGANIZATIONS = 14`, `COL_EXTRAS = 26`; `extract_page_title(extras: str) -> str | None`; `unescape_gdelt_title(raw: str) -> str`; `parse_gkg_line(line: str, batch_id: str) -> GkgRecord | None` (None bei nicht-WEB, Kopfzeile oder zu kurzer Zeile).

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_gkg.py
from nachrichten_sentiment.gkg import extract_page_title, parse_gkg_line


def _line(*, collection: str = "1", orgs: str = "NVIDIA", extras: str = "", url: str = "https://example.com/n"):
    cols = [""] * 27
    cols[0] = "20150218230000-GKG-1"
    cols[1] = "20150218230000"
    cols[2] = collection
    cols[3] = "example.com"
    cols[4] = url
    cols[13] = orgs
    cols[14] = "NVIDIA,100"
    cols[26] = extras
    return "\t".join(cols)


def test_extract_page_title_unescapes_entities():
    extras = "<PAGE_TITLE>NVIDIA &#x26; earnings &#8211; rise</PAGE_TITLE>"
    assert extract_page_title(extras) == "NVIDIA & earnings – rise"
    assert extract_page_title("no title here") is None


def test_parse_web_row_and_skip_non_web_and_header():
    record = parse_gkg_line(_line(extras="<PAGE_TITLE>NVIDIA beats</PAGE_TITLE>"), "20150218230000")
    assert record is not None
    assert record.gkg_record_id == "20150218230000-GKG-1"
    assert record.source_collection_id == 1
    assert record.url == "https://example.com/n"
    assert record.organizations == "NVIDIA"
    assert record.page_title == "NVIDIA beats"
    assert parse_gkg_line(_line(collection="2"), "20150218230000") is None
    header = "GKGRECORDID\tDATE\tSourceCollectionIdentifier\t" + "\t".join(["x"] * 24)
    assert parse_gkg_line(header, "20150218230000") is None
    assert parse_gkg_line("too\tshort", "20150218230000") is None
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_gkg.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.gkg'`.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/gkg.py
from __future__ import annotations

import html
import re
from dataclasses import dataclass


COL_RECORD_ID = 0
COL_DATE = 1
COL_SOURCE_COLLECTION = 2
COL_SOURCE_NAME = 3
COL_URL = 4
COL_ORGANIZATIONS = 13
COL_ENHANCED_ORGANIZATIONS = 14
COL_EXTRAS = 26
GKG_MIN_COLUMNS = 27

_PAGE_TITLE = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class GkgRecord:
    gkg_record_id: str
    batch_id: str
    source_collection_id: int
    source_domain: str
    url: str
    organizations: str
    enhanced_organizations: str
    extras: str
    page_title: str | None


def unescape_gdelt_title(raw: str) -> str:
    return html.unescape(raw)


def extract_page_title(extras: str) -> str | None:
    match = _PAGE_TITLE.search(extras or "")
    if not match:
        return None
    title = unescape_gdelt_title(match.group(1)).strip()
    return title or None


def parse_gkg_line(line: str, batch_id: str) -> GkgRecord | None:
    parts = line.rstrip("\n").split("\t")
    if len(parts) < GKG_MIN_COLUMNS:
        return None
    if parts[COL_RECORD_ID] == "GKGRECORDID":
        return None
    try:
        collection = int(parts[COL_SOURCE_COLLECTION])
    except ValueError:
        return None
    if collection != 1:
        return None
    return GkgRecord(
        gkg_record_id=parts[COL_RECORD_ID],
        batch_id=batch_id,
        source_collection_id=collection,
        source_domain=parts[COL_SOURCE_NAME],
        url=parts[COL_URL],
        organizations=parts[COL_ORGANIZATIONS],
        enhanced_organizations=parts[COL_ENHANCED_ORGANIZATIONS],
        extras=parts[COL_EXTRAS],
        page_title=extract_page_title(parts[COL_EXTRAS]),
    )
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_gkg.py -v`

Expected: PASS, zwei Tests.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/gkg.py tests/test_gkg.py
git commit -m "feat: GKG-2.1-Zeilen parsen und PAGE_TITLE entschlüsseln"
```

### Aufgabe 5: Nvidia-Filter ohne Titelnachladen

**Dateien:**
- Create: `src/nachrichten_sentiment/filter_company.py`
- Test: `tests/test_filter_company.py`

**Schnittstellen:**
- Nutzt: `CompanyConfig` aus Aufgabe 1; `normalize_url(url: str) -> str` aus Aufgabe 3.
- Liefert: `matches_company(company: CompanyConfig, organizations: str, enhanced_organizations: str, url: str, gkg_title: str | None) -> bool`. Der Filter verwendet nur Organisationstexte, die URL und einen bereits vorhandenen GKG-Titel, nie einen nachgeladenen Titel.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_filter_company.py
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
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_filter_company.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.filter_company'`.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/filter_company.py
from __future__ import annotations

import re

from nachrichten_sentiment.models import CompanyConfig
from nachrichten_sentiment.urls import normalize_url


def _contains_name(text: str, company: CompanyConfig) -> bool:
    lowered = text.lower()
    return any(part in lowered for part in company.name_substrings)


def _contains_ticker_word(text: str, company: CompanyConfig) -> bool:
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(company.ticker_word)}(?![A-Za-z0-9])", text, re.IGNORECASE) is not None


def matches_company(
    company: CompanyConfig,
    organizations: str,
    enhanced_organizations: str,
    url: str,
    gkg_title: str | None,
) -> bool:
    if _contains_name(organizations, company) or _contains_name(enhanced_organizations, company):
        return True
    normalized = normalize_url(url)
    if _contains_name(normalized, company) or _contains_ticker_word(normalized, company):
        return True
    if gkg_title and (_contains_name(gkg_title, company) or _contains_ticker_word(gkg_title, company)):
        return True
    return False
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_filter_company.py -v`

Expected: PASS, zwei Tests.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/filter_company.py tests/test_filter_company.py
git commit -m "feat: Nvidia-Filter über Organisation, URL und GKG-Titel"
```

### Aufgabe 6: Titel normalisieren und HTML-Titel parsen

**Dateien:**
- Create: `src/nachrichten_sentiment/titles.py`
- Test: `tests/test_titles.py`

**Schnittstellen:**
- Nutzt: nichts.
- Liefert: `normalize_title(title: str) -> str` (NFKC, Kleinbuchstaben, zusammengezogene Leerzeichen, Suffix nach ` | ` oder ` – ` entfernt); `titles_are_near_duplicates(a: str, b: str, threshold: float = 0.90) -> bool`; `parse_html_title(html: str) -> str | None` (zuerst `og:title`, sonst `<title>`).

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_titles.py
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
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_titles.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.titles'`.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/titles.py
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from html.parser import HTMLParser


def normalize_title(title: str) -> str:
    text = unicodedata.normalize("NFKC", title)
    text = re.split(r"\s+[\|\u2013]\s+", text, maxsplit=1)[0]
    text = " ".join(text.lower().split())
    return text


def titles_are_near_duplicates(a: str, b: str, threshold: float = 0.90) -> bool:
    left = normalize_title(a)
    right = normalize_title(b)
    if not left or not right:
        return False
    if left == right:
        return True
    return SequenceMatcher(None, left, right).ratio() >= threshold


class _TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.title_chunks: list[str] = []
        self.og_title: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        mapping = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() == "meta" and mapping.get("property", "").lower() == "og:title":
            self.og_title = mapping.get("content") or None

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_chunks.append(data)


def parse_html_title(html: str) -> str | None:
    parser = _TitleParser()
    parser.feed(html)
    if parser.og_title and parser.og_title.strip():
        return parser.og_title.strip()
    title = "".join(parser.title_chunks).strip()
    return title or None
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_titles.py -v`

Expected: PASS, drei Tests.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/titles.py tests/test_titles.py
git commit -m "feat: Titel normalisieren, Nahduplikat-Vergleich und HTML-Titel"
```

### Aufgabe 7: Titel von der Artikel-URL nachladen

**Dateien:**
- Modify: `src/nachrichten_sentiment/titles.py`
- Test: `tests/test_fetch_title.py`

**Schnittstellen:**
- Nutzt: `parse_html_title(html: str) -> str | None` aus Aufgabe 6.
- Liefert: `FetchResult(title: str | None, source: Literal["fetched", "missing"], error: str | None)`; `fetch_title(url: str, opener, failed_cache: dict[str, str], timeout_seconds: float = 10.0) -> FetchResult`. `opener(url: str, timeout_seconds: float) -> str` liefert HTML oder wirft. Ist die normalisierte URL in `failed_cache`, wird nicht erneut angefragt. Bei Erfolg `source="fetched"`; bei Fehler `source="missing"`, `title=None`, Fehlertext in `error` und Eintrag in `failed_cache`. Kein Stimmungswert 0 bei fehlendem Titel (das entscheidet die Pipeline später).

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_fetch_title.py
from nachrichten_sentiment.titles import fetch_title


def test_fetch_title_reads_html_and_caches_failures():
    calls: list[str] = []

    def opener(url: str, timeout_seconds: float) -> str:
        calls.append(url)
        return "<html><title>NVIDIA results</title></html>"

    failed: dict[str, str] = {}
    result = fetch_title("https://example.com/a/", opener, failed)
    assert result.title == "NVIDIA results"
    assert result.source == "fetched"
    assert result.error is None
    assert failed == {}
    assert calls == ["https://example.com/a/"]


def test_fetch_title_records_failure_and_does_not_retry_from_cache():
    calls = {"n": 0}

    def opener(url: str, timeout_seconds: float) -> str:
        calls["n"] += 1
        raise TimeoutError("timed out")

    failed: dict[str, str] = {}
    first = fetch_title("https://example.com/gone", opener, failed)
    assert first.source == "missing"
    assert first.title is None
    assert first.error is not None
    assert "https://example.com/gone" in failed
    second = fetch_title("https://example.com/gone", opener, failed)
    assert second.source == "missing"
    assert calls["n"] == 1
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_fetch_title.py -v`

Expected: FAIL mit `ImportError: cannot import name 'fetch_title'`.

- [ ] **Schritt 3: Minimale Implementierung**

An `src/nachrichten_sentiment/titles.py` anhängen (bestehende Funktionen unverändert lassen):

```python
from dataclasses import dataclass
from typing import Callable, Literal, Optional

from nachrichten_sentiment.urls import normalize_url


@dataclass(frozen=True)
class FetchResult:
    title: Optional[str]
    source: Literal["fetched", "missing"]
    error: Optional[str]


TitleOpener = Callable[[str, float], str]


def fetch_title(
    url: str,
    opener: TitleOpener,
    failed_cache: dict[str, str],
    timeout_seconds: float = 10.0,
) -> FetchResult:
    key = normalize_url(url)
    if key in failed_cache:
        return FetchResult(title=None, source="missing", error=failed_cache[key])
    try:
        html = opener(url, timeout_seconds)
        title = parse_html_title(html)
        if not title:
            failed_cache[key] = "no title in html"
            return FetchResult(title=None, source="missing", error=failed_cache[key])
        return FetchResult(title=title, source="fetched", error=None)
    except Exception as exc:  # network, timeout, HTTP errors from the opener
        failed_cache[key] = str(exc)
        return FetchResult(title=None, source="missing", error=str(exc))
```

Zusätzlich in derselben Datei eine konkrete opener-Funktion für die Pipeline:

```python
import time
import urllib.request


def http_title_opener(url: str, timeout_seconds: float, pause_seconds: float = 0.3) -> str:
    if pause_seconds:
        time.sleep(pause_seconds)
    request = urllib.request.Request(url, headers={"User-Agent": "NachrichtenSentiment/0.1"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="replace")
```

Die Importe (`dataclass`, `Callable`, `urllib.request`, `time`, `normalize_url`) an den Dateianfang von `src/nachrichten_sentiment/titles.py` setzen, nicht doppelt in der Datei.

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_titles.py tests/test_fetch_title.py -v`

Expected: PASS, fünf Tests.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/titles.py tests/test_fetch_title.py
git commit -m "feat: Titel einmalig nachladen und Fehlversuche merken"
```

### Aufgabe 8: Globale URL-Deduplizierung

**Dateien:**
- Create: `src/nachrichten_sentiment/dedup.py`
- Test: `tests/test_url_dedup.py`

**Schnittstellen:**
- Nutzt: `normalize_url(url: str) -> str` aus Aufgabe 3; `Article` aus Aufgabe 1.
- Liefert: Klasse `UrlIndex` mit `load_from_articles(articles: Iterable[Article]) -> None` und `keep(url: str, gkg_record_id: str) -> bool`. `keep` gibt genau dann `True` zurück, wenn die normalisierte URL noch nicht vorkam; das erste `gkg_record_id` bleibt gespeichert. Spätere gleiche Adressen werden verworfen.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_url_dedup.py
from nachrichten_sentiment.dedup import UrlIndex
from nachrichten_sentiment.models import Article


def _article(uid: str, url: str) -> Article:
    return Article(
        gkg_record_id=uid,
        url=url,
        url_normalized="",
        source_domain="example.com",
        title="t",
        title_source="gkg",
        batch_id="20150218230000",
        batch_utc="2015-02-18T23:00:00Z",
        day_berlin="2015-02-19",
        sentiment=None,
        sentiment_label=None,
        p_positive=None,
        p_neutral=None,
        p_negative=None,
        is_near_duplicate=False,
        near_duplicate_of=None,
    )


def test_url_index_keeps_first_occurrence_globally():
    index = UrlIndex()
    first = "https://example.com/a?utm_source=x"
    later = "HTTPS://Example.com/a/"
    assert index.keep(first, "id-1") is True
    assert index.keep(later, "id-2") is False
    loaded = UrlIndex()
    kept = _article("old", "https://example.com/a")
    kept.url_normalized = "https://example.com/a"
    loaded.load_from_articles([kept])
    assert loaded.keep("https://example.com/a/", "new") is False
    assert loaded.keep("https://example.com/b", "new-b") is True
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_url_dedup.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.dedup'`.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/dedup.py
from __future__ import annotations

from collections.abc import Iterable

from nachrichten_sentiment.models import Article
from nachrichten_sentiment.urls import normalize_url


class UrlIndex:
    def __init__(self) -> None:
        self._first_id: dict[str, str] = {}

    def load_from_articles(self, articles: Iterable[Article]) -> None:
        for article in articles:
            key = article.url_normalized or normalize_url(article.url)
            self._first_id.setdefault(key, article.gkg_record_id)

    def keep(self, url: str, gkg_record_id: str) -> bool:
        key = normalize_url(url)
        if key in self._first_id:
            return False
        self._first_id[key] = gkg_record_id
        return True
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_url_dedup.py -v`

Expected: PASS, ein Test.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/dedup.py tests/test_url_dedup.py
git commit -m "feat: globale URL-Deduplizierung behält das erste Vorkommen"
```

### Aufgabe 9: Nahduplikate am selben Berlin-Tag markieren

**Dateien:**
- Modify: `src/nachrichten_sentiment/dedup.py`
- Test: `tests/test_near_duplicates.py`

**Schnittstellen:**
- Nutzt: `Article` aus Aufgabe 1; `titles_are_near_duplicates(a: str, b: str, threshold: float = 0.90) -> bool` aus Aufgabe 6.
- Liefert: `mark_near_duplicates(articles: list[Article], threshold: float = 0.90) -> list[Article]`. Sortierung nach `batch_utc`, dann `gkg_record_id`. Vergleich nur innerhalb desselben `day_berlin`. Artikel mit `title_source == "missing"` oder leerem Titel werden nicht gruppiert (`is_near_duplicate=False`, `near_duplicate_of=None`). Trifft ein späterer Titel auf einen früheren zu, erbt er dessen Stamm-ID (falls der frühere schon ein Nahduplikat ist, dessen `near_duplicate_of`, sonst dessen `gkg_record_id`). Die Funktion ändert die übergebenen Objekte und gibt dieselbe Liste zurück.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_near_duplicates.py
from nachrichten_sentiment.dedup import mark_near_duplicates
from nachrichten_sentiment.models import Article


def _article(uid: str, title: str, day: str, source: str = "gkg", utc: str = "2015-02-19T00:00:00Z") -> Article:
    return Article(
        gkg_record_id=uid,
        url=f"https://example.com/{uid}",
        url_normalized=f"https://example.com/{uid}",
        source_domain="example.com",
        title=title,
        title_source=source,  # type: ignore[arg-type]
        batch_id="20150219000000",
        batch_utc=utc,
        day_berlin=day,
        sentiment=None,
        sentiment_label=None,
        p_positive=None,
        p_neutral=None,
        p_negative=None,
        is_near_duplicate=False,
        near_duplicate_of=None,
    )


def test_near_duplicates_same_day_and_missing_titles_stay_ungrouped():
    stem = _article("a", "NVIDIA raises full-year revenue forecast", "2015-02-19", utc="2015-02-18T23:00:00Z")
    dup = _article("b", "NVIDIA raises full-year revenue forecast!", "2015-02-19", utc="2015-02-18T23:15:00Z")
    other_day = _article("c", "NVIDIA raises full-year revenue forecast", "2015-02-20", utc="2015-02-19T23:00:00Z")
    missing = _article("d", "", "2015-02-19", source="missing", utc="2015-02-18T23:30:00Z")
    mark_near_duplicates([stem, dup, other_day, missing], 0.90)
    assert stem.is_near_duplicate is False
    assert stem.near_duplicate_of is None
    assert dup.is_near_duplicate is True
    assert dup.near_duplicate_of == "a"
    assert other_day.is_near_duplicate is False
    assert missing.is_near_duplicate is False
    assert missing.near_duplicate_of is None
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_near_duplicates.py -v`

Expected: FAIL mit `ImportError: cannot import name 'mark_near_duplicates'`.

- [ ] **Schritt 3: Minimale Implementierung**

An `src/nachrichten_sentiment/dedup.py` anhängen:

```python
from nachrichten_sentiment.titles import titles_are_near_duplicates


def mark_near_duplicates(articles: list[Article], threshold: float = 0.90) -> list[Article]:
    ordered = sorted(articles, key=lambda item: (item.batch_utc, item.gkg_record_id))
    previous: list[Article] = []
    for article in ordered:
        article.is_near_duplicate = False
        article.near_duplicate_of = None
        if article.title_source == "missing" or not article.title.strip():
            previous.append(article)
            continue
        for candidate in previous:
            if candidate.day_berlin != article.day_berlin:
                continue
            if candidate.title_source == "missing" or not candidate.title.strip():
                continue
            if titles_are_near_duplicates(candidate.title, article.title, threshold):
                article.is_near_duplicate = True
                article.near_duplicate_of = candidate.near_duplicate_of or candidate.gkg_record_id
                break
        previous.append(article)
    return articles
```

Den Import von `titles_are_near_duplicates` an den Dateianfang setzen.

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_near_duplicates.py tests/test_url_dedup.py -v`

Expected: PASS, zwei Tests.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/dedup.py tests/test_near_duplicates.py
git commit -m "feat: Nahduplikate am selben Berlin-Tag mit Schwelle 0,90"
```

### Aufgabe 10: Stimmungswert aus Wahrscheinlichkeiten

**Dateien:**
- Create: `src/nachrichten_sentiment/sentiment.py`
- Test: `tests/test_sentiment_score.py`

**Schnittstellen:**
- Nutzt: `SentimentResult` aus `src/nachrichten_sentiment/models.py` (Aufgabe 1).
- Liefert: `score_from_probs(p_positive: float, p_neutral: float, p_negative: float) -> SentimentResult` mit `sentiment = p_positive - p_negative` und `label` gleich der Klasse mit der größten Wahrscheinlichkeit (argmax; bei Gleichstand in der Reihenfolge positive, negative, neutral). `SentimentModel` als Protokoll mit `predict_proba(self, title: str) -> tuple[float, float, float]` (positiv, neutral, negativ). `score_title(title: str, model: SentimentModel) -> SentimentResult`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_sentiment_score.py
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
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_sentiment_score.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.sentiment'`.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/sentiment.py
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
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_sentiment_score.py -v`

Expected: PASS, zwei Tests.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/sentiment.py tests/test_sentiment_score.py
git commit -m "feat: Stimmung als P(positiv) minus P(negativ) und argmax-Klasse"
```

### Aufgabe 11: FinBERT-Adapter und markierter Plausibilitätstest

**Dateien:**
- Modify: `src/nachrichten_sentiment/sentiment.py`
- Test: `tests/test_finbert_adapter.py`
- Test: `tests/test_finbert_plausibility.py`

**Schnittstellen:**
- Nutzt: `score_from_probs` und `SentimentModel` aus Aufgabe 10; `score_title(title: str, model: SentimentModel) -> SentimentResult`.
- Liefert: `class FinBertModel` mit `__init__(self, model_name: str = "ProsusAI/finbert")` und `predict_proba(self, title: str) -> tuple[float, float, float]` in der Reihenfolge positiv, neutral, negativ, unabhängig von der internen Label-Reihenfolge des Modells. Der Plausibilitätstest trägt `@pytest.mark.finbert` und läuft nicht in der Standard-Suite.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_finbert_adapter.py
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
```

```python
# tests/test_finbert_plausibility.py
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
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_finbert_adapter.py -v`

Expected: FAIL mit `ImportError: cannot import name 'FinBertModel'`.

- [ ] **Schritt 3: Minimale Implementierung**

An `src/nachrichten_sentiment/sentiment.py` anhängen und `_transformers_pipeline` so setzen, dass der Test es patchen kann:

```python
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
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_sentiment_score.py tests/test_finbert_adapter.py -v`

Expected: PASS. Den echten Modelltest nicht in diesem Schritt ausführen; er folgt nach `pip install -e ".[ml]"` bewusst mit:

Run: `pytest tests/test_finbert_plausibility.py -v -m finbert`

Expected: PASS, sofern Extra `ml` installiert und das Modell lokal ladbar ist. In der Standard-Suite bleibt er ausgeschlossen: `pytest -m "not finbert"` muss ohne diesen Test grün sein.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/sentiment.py tests/test_finbert_adapter.py tests/test_finbert_plausibility.py
git commit -m "feat: FinBERT-Adapter und markierter Plausibilitätstest"
```

### Aufgabe 12: Tageswerte aggregieren

**Dateien:**
- Create: `src/nachrichten_sentiment/daily.py`
- Test: `tests/test_daily.py`

**Schnittstellen:**
- Nutzt: `Article`, `DailyRow` aus Aufgabe 1; `expected_batch_ids_for_berlin_day(day: date) -> list[str]` aus Aufgabe 2; `mark_near_duplicates` aus Aufgabe 9 (die Tests übergeben bereits markierte Artikel oder rufen die Funktion auf).
- Liefert: `aggregate_daily(articles: list[Article], day: date, processed_batch_ids: set[str]) -> DailyRow`. Es gilt `count_positive + count_neutral + count_negative + count_without_sentiment = count_unique_url`. `count_after_near_dup_collapse` zählt Artikel mit `is_near_duplicate is False`. `sentiment_mean` ist das arithmetische Mittel aller nicht-leeren `sentiment`-Werte (einschließlich Nahduplikate) oder `None`. `coverage` ist `"complete"`, wenn jedes Element von `expected_batch_ids_for_berlin_day(day)` in `processed_batch_ids` liegt, sonst `"gap"`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_daily.py
from datetime import date

from nachrichten_sentiment.daily import aggregate_daily
from nachrichten_sentiment.models import Article
from nachrichten_sentiment.timeutil import expected_batch_ids_for_berlin_day


def _article(**kwargs) -> Article:
    base = dict(
        gkg_record_id="id",
        url="https://example.com/id",
        url_normalized="https://example.com/id",
        source_domain="example.com",
        title="t",
        title_source="gkg",
        batch_id="20150219000000",
        batch_utc="2015-02-19T00:00:00Z",
        day_berlin="2015-02-19",
        sentiment=0.5,
        sentiment_label="positive",
        p_positive=0.6,
        p_neutral=0.3,
        p_negative=0.1,
        is_near_duplicate=False,
        near_duplicate_of=None,
    )
    base.update(kwargs)
    return Article(**base)  # type: ignore[arg-type]


def test_aggregate_counts_invariant_and_mean():
    day = date(2015, 2, 19)
    articles = [
        _article(gkg_record_id="p", sentiment_label="positive", sentiment=0.8, url_normalized="https://e.com/p"),
        _article(gkg_record_id="n", sentiment_label="neutral", sentiment=0.0, url_normalized="https://e.com/n"),
        _article(gkg_record_id="d", sentiment_label="negative", sentiment=-0.2, url_normalized="https://e.com/d"),
        _article(gkg_record_id="x", sentiment=None, sentiment_label=None, title_source="missing", title="", url_normalized="https://e.com/x"),
        _article(gkg_record_id="dup", sentiment_label="positive", sentiment=0.8, is_near_duplicate=True, near_duplicate_of="p", url_normalized="https://e.com/dup"),
    ]
    processed = set(expected_batch_ids_for_berlin_day(day))
    row = aggregate_daily(articles, day, processed)
    assert row.count_unique_url == 5
    assert row.count_positive == 2
    assert row.count_neutral == 1
    assert row.count_negative == 1
    assert row.count_without_sentiment == 1
    assert row.count_positive + row.count_neutral + row.count_negative + row.count_without_sentiment == row.count_unique_url
    assert row.count_after_near_dup_collapse == 4
    assert row.sentiment_mean == 0.35
    assert row.coverage == "complete"
    assert row.date == "2015-02-19"


def test_empty_complete_day_is_zero_and_missing_batches_are_gaps():
    day = date(2015, 2, 19)
    complete = aggregate_daily([], day, set(expected_batch_ids_for_berlin_day(day)))
    assert complete.count_unique_url == 0
    assert complete.sentiment_mean is None
    assert complete.coverage == "complete"
    gap = aggregate_daily([], day, set())
    assert gap.coverage == "gap"
    assert gap.count_unique_url == 0
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_daily.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.daily'`.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/daily.py
from __future__ import annotations

from datetime import date

from nachrichten_sentiment.models import Article, DailyRow
from nachrichten_sentiment.timeutil import expected_batch_ids_for_berlin_day


def aggregate_daily(articles: list[Article], day: date, processed_batch_ids: set[str]) -> DailyRow:
    day_key = day.isoformat()
    of_day = [item for item in articles if item.day_berlin == day_key]
    positives = [item for item in of_day if item.sentiment_label == "positive"]
    neutrals = [item for item in of_day if item.sentiment_label == "neutral"]
    negatives = [item for item in of_day if item.sentiment_label == "negative"]
    missing = [item for item in of_day if item.sentiment is None]
    scores = [item.sentiment for item in of_day if item.sentiment is not None]
    expected = set(expected_batch_ids_for_berlin_day(day))
    coverage = "complete" if expected <= processed_batch_ids else "gap"
    return DailyRow(
        date=day_key,
        count_unique_url=len(of_day),
        count_after_near_dup_collapse=sum(1 for item in of_day if not item.is_near_duplicate),
        count_positive=len(positives),
        count_neutral=len(neutrals),
        count_negative=len(negatives),
        count_without_sentiment=len(missing),
        sentiment_mean=(sum(scores) / len(scores)) if scores else None,
        coverage=coverage,
    )
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_daily.py -v`

Expected: PASS, zwei Tests.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/daily.py tests/test_daily.py
git commit -m "feat: Tageswerte mit Positiv-, Neutral- und Negativzahl sowie Lücken"
```

### Aufgabe 13: Fortschritt, Lückenprotokoll und Fortsetzen

**Dateien:**
- Create: `src/nachrichten_sentiment/progress.py`
- Test: `tests/test_progress.py`

**Schnittstellen:**
- Nutzt: `ProgressState` aus Aufgabe 1; `FIRST_BATCH_ID`, `next_batch_id` aus Aufgabe 2.
- Liefert: `load_progress(path: Path) -> ProgressState`; `save_progress(path: Path, state: ProgressState) -> None`; `append_gap_log(path: Path, message: str) -> None`; `processed_batch_ids(state: ProgressState) -> set[str]` (alle IDs von `FIRST_BATCH_ID` bis `cursor_batch_id` einschließlich, ohne `open_gaps`; leer wenn `cursor_batch_id` fehlt); `batches_to_process(state: ProgressState, until_id: str) -> list[str]` (zuerst offene Lücken in zeitlicher Folge, danach neue Sätze nach dem Cursor bis `until_id` inklusive, ohne Duplikate). Nach Erfolg ruft die Pipeline `mark_success(state, batch_id)` auf, nach endgültigem Fehlschlag `mark_gap(state, batch_id)`. `cursor_batch_id` ist der höchste bereits versuchte Satz; `last_success_batch_id` bleibt der letzte erfolgreiche Satz laut Spec.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_progress.py
from pathlib import Path

from nachrichten_sentiment.models import ProgressState
from nachrichten_sentiment.progress import (
    append_gap_log,
    batches_to_process,
    load_progress,
    mark_gap,
    mark_success,
    processed_batch_ids,
    save_progress,
)


def test_progress_roundtrip_resume_and_gap_log(tmp_path: Path):
    path = tmp_path / "progress.json"
    log = tmp_path / "gaps.log"
    state = ProgressState(last_success_batch_id=None, cursor_batch_id=None, open_gaps=[], failed_title_fetches={})
    mark_success(state, "20150218230000")
    mark_gap(state, "20150218231500")
    mark_success(state, "20150218233000")
    save_progress(path, state)
    append_gap_log(log, "missing 20150218231500")
    loaded = load_progress(path)
    assert loaded.last_success_batch_id == "20150218233000"
    assert loaded.cursor_batch_id == "20150218233000"
    assert loaded.open_gaps == ["20150218231500"]
    processed = processed_batch_ids(loaded)
    assert "20150218230000" in processed
    assert "20150218233000" in processed
    assert "20150218231500" not in processed
    todo = batches_to_process(loaded, "20150218234500")
    assert todo[0] == "20150218231500"
    assert todo[-1] == "20150218234500"
    assert "20150218233000" not in todo
    assert "missing 20150218231500" in log.read_text(encoding="utf-8")
    empty = load_progress(tmp_path / "missing.json")
    assert empty.cursor_batch_id is None
    assert batches_to_process(empty, "20150218231500") == ["20150218230000", "20150218231500"]
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_progress.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.progress'`.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/progress.py
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from nachrichten_sentiment.models import ProgressState
from nachrichten_sentiment.timeutil import FIRST_BATCH_ID, iter_batch_ids, next_batch_id


def load_progress(path: Path) -> ProgressState:
    if not path.exists():
        return ProgressState(None, None, [], {})
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ProgressState(
        last_success_batch_id=raw.get("last_success_batch_id"),
        cursor_batch_id=raw.get("cursor_batch_id"),
        open_gaps=list(raw.get("open_gaps", [])),
        failed_title_fetches=dict(raw.get("failed_title_fetches", {})),
    )


def save_progress(path: Path, state: ProgressState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "last_success_batch_id": state.last_success_batch_id,
                "cursor_batch_id": state.cursor_batch_id,
                "open_gaps": state.open_gaps,
                "failed_title_fetches": state.failed_title_fetches,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def append_gap_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {message}\n")


def mark_success(state: ProgressState, batch_id: str) -> None:
    if batch_id in state.open_gaps:
        state.open_gaps.remove(batch_id)
    state.last_success_batch_id = batch_id
    state.cursor_batch_id = batch_id if state.cursor_batch_id is None or batch_id > state.cursor_batch_id else state.cursor_batch_id


def mark_gap(state: ProgressState, batch_id: str) -> None:
    if batch_id not in state.open_gaps:
        state.open_gaps.append(batch_id)
        state.open_gaps.sort()
    state.cursor_batch_id = batch_id if state.cursor_batch_id is None or batch_id > state.cursor_batch_id else state.cursor_batch_id


def processed_batch_ids(state: ProgressState) -> set[str]:
    if not state.cursor_batch_id:
        return set()
    all_ids = set(iter_batch_ids(FIRST_BATCH_ID, state.cursor_batch_id))
    return all_ids - set(state.open_gaps)


def batches_to_process(state: ProgressState, until_id: str) -> list[str]:
    pending: list[str] = []
    seen: set[str] = set()
    for batch_id in state.open_gaps:
        if batch_id <= until_id and batch_id not in seen:
            pending.append(batch_id)
            seen.add(batch_id)
    start = FIRST_BATCH_ID if state.cursor_batch_id is None else next_batch_id(state.cursor_batch_id)
    if start <= until_id:
        for batch_id in iter_batch_ids(start, until_id):
            if batch_id not in seen:
                pending.append(batch_id)
                seen.add(batch_id)
    return pending
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_progress.py -v`

Expected: PASS, ein Test.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/progress.py tests/test_progress.py
git commit -m "feat: Fortschrittsdatei, Lückenprotokoll und fortsetzbare Satzliste"
```

### Aufgabe 14: GKG-Download mit Wiederholversuchen

**Dateien:**
- Create: `src/nachrichten_sentiment/download.py`
- Test: `tests/test_download.py`

**Schnittstellen:**
- Nutzt: `ProjectPaths.tmp_dir` aus Aufgabe 1 nur in der Pipeline; die Funktion selbst bekommt einen Zielordner.
- Liefert: `gkg_url(batch_id: str) -> str` immer mit `https://data.gdeltproject.org/gdeltv2/{batch_id}.gkg.csv.zip`; Ausnahmen `MissingGkgError(batch_id)` und `DownloadError(batch_id, message)`; `download_gkg_zip(batch_id: str, dest_dir: Path, retries: int = 3, backoff_seconds: float = 0.0, fetcher=None) -> Path`. `fetcher(url: str) -> bytes` kann im Test ersetzt werden. Nach `retries` Versuchen: HTTP 404 wird zu `MissingGkgError`, andere Fehler zu `DownloadError`. Die ZIP wird nach `{dest_dir}/{batch_id}.gkg.csv.zip` geschrieben.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_download.py
from pathlib import Path

import pytest

from nachrichten_sentiment.download import (
    DownloadError,
    MissingGkgError,
    download_gkg_zip,
    gkg_url,
)


def test_gkg_url_uses_https():
    assert gkg_url("20150218230000") == "https://data.gdeltproject.org/gdeltv2/20150218230000.gkg.csv.zip"


def test_download_retries_then_succeeds(tmp_path: Path):
    attempts = {"n": 0}

    def fetcher(url: str) -> bytes:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ConnectionError("drop")
        return b"PK\x03\x04fake-zip"

    path = download_gkg_zip("20150218230000", tmp_path, retries=3, backoff_seconds=0.0, fetcher=fetcher)
    assert path.read_bytes() == b"PK\x03\x04fake-zip"
    assert attempts["n"] == 3


def test_download_404_becomes_missing_after_retries(tmp_path: Path):
    def fetcher(url: str) -> bytes:
        raise MissingGkgError("20150218230000")

    with pytest.raises(MissingGkgError):
        download_gkg_zip("20150218230000", tmp_path, retries=3, backoff_seconds=0.0, fetcher=fetcher)


def test_download_other_errors_become_download_error(tmp_path: Path):
    def fetcher(url: str) -> bytes:
        raise RuntimeError("boom")

    with pytest.raises(DownloadError):
        download_gkg_zip("20150218230000", tmp_path, retries=2, backoff_seconds=0.0, fetcher=fetcher)
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_download.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.download'`.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/download.py
from __future__ import annotations

import time
from pathlib import Path

import requests


class MissingGkgError(Exception):
    def __init__(self, batch_id: str) -> None:
        super().__init__(f"missing GKG file {batch_id}")
        self.batch_id = batch_id


class DownloadError(Exception):
    def __init__(self, batch_id: str, message: str) -> None:
        super().__init__(f"{batch_id}: {message}")
        self.batch_id = batch_id
        self.message = message


def gkg_url(batch_id: str) -> str:
    return f"https://data.gdeltproject.org/gdeltv2/{batch_id}.gkg.csv.zip"


def _default_fetcher(url: str) -> bytes:
    response = requests.get(url, timeout=60)
    if response.status_code == 404:
        batch_id = url.rsplit("/", 1)[-1].split(".")[0]
        raise MissingGkgError(batch_id)
    response.raise_for_status()
    return response.content


def download_gkg_zip(
    batch_id: str,
    dest_dir: Path,
    retries: int = 3,
    backoff_seconds: float = 2.0,
    fetcher=None,
) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / f"{batch_id}.gkg.csv.zip"
    url = gkg_url(batch_id)
    fetch = fetcher or _default_fetcher
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            data = fetch(url)
            target.write_bytes(data)
            return target
        except MissingGkgError:
            last_error = MissingGkgError(batch_id)
        except Exception as exc:  # noqa: BLE001
            last_error = DownloadError(batch_id, str(exc))
        if attempt < retries and backoff_seconds:
            time.sleep(backoff_seconds * attempt)
    if isinstance(last_error, MissingGkgError):
        raise last_error
    raise last_error or DownloadError(batch_id, "unknown error")
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_download.py -v`

Expected: PASS, vier Tests.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/download.py tests/test_download.py
git commit -m "feat: GKG-Download per HTTPS mit Wiederholversuchen"
```

### Aufgabe 15: Monatsdateien, Tagesdatei und Schlagzeilen schreiben

**Dateien:**
- Create: `src/nachrichten_sentiment/store.py`
- Test: `tests/test_store.py`

**Schnittstellen:**
- Nutzt: `Article`, `DailyRow`, `ProjectPaths` aus Aufgabe 1.
- Liefert: `append_articles(paths: ProjectPaths, ticker: str, articles: list[Article]) -> None` schreibt nach `data/articles/{ticker}/YYYY-MM.jsonl` (Monat aus `day_berlin`); `load_articles(paths: ProjectPaths, ticker: str) -> list[Article]`; `write_daily(paths: ProjectPaths, ticker: str, rows: list[DailyRow], display_name: str) -> None` schreibt `site/data/{ticker}-daily.json`; `write_headlines(paths: ProjectPaths, ticker: str, articles: list[Article]) -> None` schreibt `site/data/{ticker}/YYYY-MM.json` gruppiert nach `day_berlin`. `article_from_dict` / `article_to_dict` und `daily_row_to_dict` gehören in dieselbe Datei und werden von den Tests indirekt geprüft.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_store.py
import json
from pathlib import Path

from nachrichten_sentiment.models import Article, DailyRow
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.store import append_articles, load_articles, write_daily, write_headlines


def _article() -> Article:
    return Article(
        gkg_record_id="id-1",
        url="https://example.com/a",
        url_normalized="https://example.com/a",
        source_domain="example.com",
        title="NVIDIA raises forecast",
        title_source="gkg",
        batch_id="20150218230000",
        batch_utc="2015-02-18T23:00:00Z",
        day_berlin="2015-02-19",
        sentiment=0.5,
        sentiment_label="positive",
        p_positive=0.6,
        p_neutral=0.3,
        p_negative=0.1,
        is_near_duplicate=False,
        near_duplicate_of=None,
    )


def test_store_writes_month_daily_and_headline_files(tmp_path: Path):
    paths = ProjectPaths(tmp_path)
    article = _article()
    append_articles(paths, "NVDA", [article])
    month_file = tmp_path / "data" / "articles" / "nvda" / "2015-02.jsonl"
    assert month_file.exists()
    loaded = load_articles(paths, "NVDA")
    assert loaded[0].gkg_record_id == "id-1"
    assert loaded[0].sentiment_label == "positive"
    row = DailyRow("2015-02-19", 1, 1, 1, 0, 0, 0, 0.5, "complete")
    write_daily(paths, "NVDA", [row], "Nvidia")
    daily = json.loads((tmp_path / "site" / "data" / "nvda-daily.json").read_text(encoding="utf-8"))
    assert daily["ticker"] == "NVDA"
    assert daily["display_name"] == "Nvidia"
    assert daily["timezone"] == "Europe/Berlin"
    assert daily["days"][0]["count_positive"] == 1
    assert daily["days"][0]["count_neutral"] == 0
    assert daily["days"][0]["coverage"] == "complete"
    write_headlines(paths, "NVDA", [article])
    headlines = json.loads((tmp_path / "site" / "data" / "nvda" / "2015-02.json").read_text(encoding="utf-8"))
    assert headlines["2015-02-19"][0]["title"] == "NVIDIA raises forecast"
    assert headlines["2015-02-19"][0]["url"] == "https://example.com/a"
    assert headlines["2015-02-19"][0]["is_near_duplicate"] is False
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_store.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.store'`.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/store.py
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from nachrichten_sentiment.models import Article, DailyRow
from nachrichten_sentiment.paths import ProjectPaths


def article_to_dict(article: Article) -> dict:
    return asdict(article)


def article_from_dict(raw: dict) -> Article:
    return Article(**raw)


def append_articles(paths: ProjectPaths, ticker: str, articles: list[Article]) -> None:
    by_month: dict[str, list[Article]] = {}
    for article in articles:
        month = article.day_berlin[:7]
        by_month.setdefault(month, []).append(article)
    directory = paths.articles_dir(ticker)
    directory.mkdir(parents=True, exist_ok=True)
    for month, rows in by_month.items():
        target = directory / f"{month}.jsonl"
        with target.open("a", encoding="utf-8") as handle:
            for article in rows:
                handle.write(json.dumps(article_to_dict(article), ensure_ascii=False) + "\n")


def load_articles(paths: ProjectPaths, ticker: str) -> list[Article]:
    directory = paths.articles_dir(ticker)
    if not directory.exists():
        return []
    articles: list[Article] = []
    for file in sorted(directory.glob("*.jsonl")):
        for line in file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                articles.append(article_from_dict(json.loads(line)))
    return articles


def write_daily(paths: ProjectPaths, ticker: str, rows: list[DailyRow], display_name: str) -> None:
    paths.site_data_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "ticker": ticker.upper(),
        "display_name": display_name,
        "timezone": "Europe/Berlin",
        "days": [asdict(row) for row in rows],
    }
    target = paths.site_data_dir / f"{ticker.lower()}-daily.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_headlines(paths: ProjectPaths, ticker: str, articles: list[Article]) -> None:
    grouped: dict[str, dict[str, list[dict]]] = {}
    for article in articles:
        month = article.day_berlin[:7]
        day_map = grouped.setdefault(month, {})
        day_map.setdefault(article.day_berlin, []).append(
            {
                "gkg_record_id": article.gkg_record_id,
                "title": article.title,
                "url": article.url,
                "sentiment": article.sentiment,
                "sentiment_label": article.sentiment_label,
                "title_source": article.title_source,
                "is_near_duplicate": article.is_near_duplicate,
                "near_duplicate_of": article.near_duplicate_of,
            }
        )
    root = paths.site_data_dir / ticker.lower()
    root.mkdir(parents=True, exist_ok=True)
    for month, days in grouped.items():
        (root / f"{month}.json").write_text(json.dumps(days, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_store.py -v`

Expected: PASS, ein Test.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/store.py tests/test_store.py
git commit -m "feat: Einzelnachrichten, Tageswerte und Schlagzeilen speichern"
```

### Aufgabe 16: Einen 15-Minuten-Satz verarbeiten

**Dateien:**
- Create: `src/nachrichten_sentiment/pipeline.py`
- Test: `tests/test_pipeline_batch.py`

**Schnittstellen:**
- Nutzt: `parse_gkg_line(line: str, batch_id: str) -> GkgRecord | None`; `matches_company(...)`; `UrlIndex.keep`; `fetch_title`; `score_title`; `normalize_url`; `datetime_from_batch_id`, `berlin_day_from_batch_id`; `download_gkg_zip`; `MissingGkgError`, `DownloadError`; `append_articles`; `mark_success`, `mark_gap`, `save_progress`, `append_gap_log`.
- Liefert: `process_batch(batch_id: str, *, company: CompanyConfig, paths: ProjectPaths, url_index: UrlIndex, model: SentimentModel | None, title_opener, progress: ProgressState, fetcher=None, extract_zip=None) -> list[Article]`. Ablauf: ZIP laden und entpacken, Zeilen parsen, nur Treffer von `matches_company` mit vorhandenem GKG-Titel oder Organisation/URL behalten, URL-Dedup, Titel aus `page_title` oder `fetch_title` (kein Nachladen zur Entdeckung), FinBERT nur bei vorhandenem Titel, Artikel anhängen, bei Erfolg `mark_success` und `save_progress`, bei `MissingGkgError`/`DownloadError` nach den Wiederholversuchen im Downloader `mark_gap`, `append_gap_log` und `save_progress`. Rohe ZIP nach dem Verarbeiten aus `tmp_dir` löschen. `extract_zip(zip_path: Path) -> str` liefert den TSV-Text und ist im Test ersetzbar.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_pipeline_batch.py
from pathlib import Path

from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.dedup import UrlIndex
from nachrichten_sentiment.models import ProgressState, SentimentResult
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.pipeline import process_batch
from nachrichten_sentiment.progress import load_progress
from nachrichten_sentiment.store import load_articles


class _Model:
    def predict_proba(self, title: str) -> tuple[float, float, float]:
        return (0.8, 0.1, 0.1)


def _gkg_line(record_id: str, url: str, extras: str, orgs: str = "NVIDIA") -> str:
    cols = [""] * 27
    cols[0] = record_id
    cols[1] = "20150218230000"
    cols[2] = "1"
    cols[3] = "example.com"
    cols[4] = url
    cols[13] = orgs
    cols[14] = orgs
    cols[26] = extras
    return "\t".join(cols)


def test_process_batch_filters_scores_and_records_gaps(tmp_path: Path):
    paths = ProjectPaths(tmp_path)
    company = load_company("NVDA")
    progress = ProgressState(None, None, [], {})
    lines = "\n".join(
        [
            _gkg_line("r1", "https://example.com/a", "<PAGE_TITLE>NVIDIA raises forecast</PAGE_TITLE>"),
            _gkg_line("r2", "https://example.com/b", "", orgs=""),  # no nvidia
            _gkg_line("r1b", "https://example.com/a", "<PAGE_TITLE>dup url</PAGE_TITLE>"),
        ]
    )
    articles = process_batch(
        "20150218230000",
        company=company,
        paths=paths,
        url_index=UrlIndex(),
        model=_Model(),
        title_opener=lambda url, timeout: "<html></html>",
        progress=progress,
        fetcher=lambda url: b"zip",
        extract_zip=lambda path: lines,
    )
    assert [item.gkg_record_id for item in articles] == ["r1"]
    assert articles[0].sentiment == 0.7
    assert articles[0].title_source == "gkg"
    assert progress.last_success_batch_id == "20150218230000"
    stored = load_articles(paths, "NVDA")
    assert len(stored) == 1

    def missing(url: str):
        from nachrichten_sentiment.download import MissingGkgError
        raise MissingGkgError("20150218231500")

    process_batch(
        "20150218231500",
        company=company,
        paths=paths,
        url_index=UrlIndex(),
        model=_Model(),
        title_opener=lambda url, timeout: "",
        progress=progress,
        fetcher=missing,
        extract_zip=lambda path: "",
    )
    assert "20150218231500" in progress.open_gaps
    assert (paths.gaps_log_path).exists()
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_pipeline_batch.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.pipeline'`.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/pipeline.py
from __future__ import annotations

import zipfile
from pathlib import Path

from nachrichten_sentiment.dedup import UrlIndex
from nachrichten_sentiment.download import DownloadError, MissingGkgError, download_gkg_zip
from nachrichten_sentiment.filter_company import matches_company
from nachrichten_sentiment.gkg import parse_gkg_line
from nachrichten_sentiment.models import Article, CompanyConfig, ProgressState
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.progress import append_gap_log, mark_gap, mark_success, save_progress
from nachrichten_sentiment.sentiment import SentimentModel, score_title
from nachrichten_sentiment.store import append_articles
from nachrichten_sentiment.timeutil import berlin_day_from_batch_id, datetime_from_batch_id
from nachrichten_sentiment.titles import fetch_title
from nachrichten_sentiment.urls import normalize_url


def _extract_zip(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as archive:
        name = archive.namelist()[0]
        return archive.read(name).decode("utf-8", errors="replace")


def process_batch(
    batch_id: str,
    *,
    company: CompanyConfig,
    paths: ProjectPaths,
    url_index: UrlIndex,
    model: SentimentModel | None,
    title_opener,
    progress: ProgressState,
    fetcher=None,
    extract_zip=None,
) -> list[Article]:
    try:
        zip_path = download_gkg_zip(batch_id, paths.tmp_dir, fetcher=fetcher, backoff_seconds=0.0 if fetcher else 2.0)
        text = (extract_zip or _extract_zip)(zip_path)
    except (MissingGkgError, DownloadError) as exc:
        mark_gap(progress, batch_id)
        append_gap_log(paths.gaps_log_path, f"{batch_id} {exc}")
        save_progress(paths.progress_path, progress)
        return []
    finally:
        leftover = paths.tmp_dir / f"{batch_id}.gkg.csv.zip"
        if leftover.exists():
            leftover.unlink()

    articles: list[Article] = []
    batch_utc = datetime_from_batch_id(batch_id).strftime("%Y-%m-%dT%H:%M:%SZ")
    day = berlin_day_from_batch_id(batch_id).isoformat()
    for line in text.splitlines():
        record = parse_gkg_line(line, batch_id)
        if record is None:
            continue
        if not matches_company(
            company,
            record.organizations,
            record.enhanced_organizations,
            record.url,
            record.page_title,
        ):
            continue
        if not url_index.keep(record.url, record.gkg_record_id):
            continue
        if record.page_title:
            title, title_source = record.page_title, "gkg"
        else:
            fetched = fetch_title(record.url, title_opener, progress.failed_title_fetches)
            title, title_source = (fetched.title or ""), fetched.source
        sentiment = label = p_pos = p_neu = p_neg = None
        if title and model is not None and title_source != "missing":
            scored = score_title(title, model)
            sentiment, label = scored.sentiment, scored.label
            p_pos, p_neu, p_neg = scored.p_positive, scored.p_neutral, scored.p_negative
        articles.append(
            Article(
                gkg_record_id=record.gkg_record_id,
                url=record.url,
                url_normalized=normalize_url(record.url),
                source_domain=record.source_domain,
                title=title,
                title_source=title_source,
                batch_id=batch_id,
                batch_utc=batch_utc,
                day_berlin=day,
                sentiment=sentiment,
                sentiment_label=label,
                p_positive=p_pos,
                p_neutral=p_neu,
                p_negative=p_neg,
                is_near_duplicate=False,
                near_duplicate_of=None,
            )
        )
    if articles:
        append_articles(paths, company.ticker, articles)
    mark_success(progress, batch_id)
    save_progress(paths.progress_path, progress)
    return articles
```

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_pipeline_batch.py -v`

Expected: PASS, ein Test.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/pipeline.py tests/test_pipeline_batch.py
git commit -m "feat: einen GKG-15-Minuten-Satz filternd und fortsetzbar verarbeiten"
```

### Aufgabe 17: Erstlauf, Tageslauf, Probelauf-CLI

**Dateien:**
- Modify: `src/nachrichten_sentiment/pipeline.py`
- Create: `src/nachrichten_sentiment/cli.py`
- Create: `src/nachrichten_sentiment/__main__.py`
- Create: `README.md`
- Test: `tests/test_cli_pipeline.py`

**Schnittstellen:**
- Nutzt: `process_batch`, `batches_to_process`, `load_progress`, `load_articles`, `UrlIndex`, `mark_near_duplicates`, `aggregate_daily`, `processed_batch_ids`, `write_daily`, `write_headlines`, `expected_batch_ids_for_berlin_day`, `previous_berlin_day`, `FIRST_BATCH_ID`, `load_company`, `ProjectPaths`, `default_root`.
- Liefert: `rebuild_outputs(paths: ProjectPaths, company: CompanyConfig, progress: ProgressState) -> list[DailyRow]` (lädt alle Artikel, setzt Nahduplikate neu, schreibt Tages- und Schlagzeilendateien für alle Berlin-Tage von `FIRST_BERLIN_DAY` bis zum Tag des Cursors, `coverage` über `processed_batch_ids`); `run_batches(batch_ids: list[str], **kwargs) -> None`; `run_initial(paths, company, model, title_opener, until_id: str | None) -> None`; `run_daily(paths, company, model, title_opener, day: date | None = None) -> None` (Vortag in Europe/Berlin plus offene Lücken, `until_id` = letzter Satz des Zieltags); `run_trial(paths, company, model, title_opener, start_day: date, days: int = 7, fetcher=None, extract_zip=None) -> None`. CLI: `python -m nachrichten_sentiment erstlauf [--until YYYYMMDDHHMMSS]`, `python -m nachrichten_sentiment tageslauf [--day YYYY-MM-DD]`, `python -m nachrichten_sentiment probelauf --start YYYY-MM-DD [--days 7] [--fixture-dir PATH]`.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_cli_pipeline.py
from datetime import date
from pathlib import Path

from nachrichten_sentiment.cli import build_parser
from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.models import ProgressState
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.pipeline import rebuild_outputs, run_daily, run_trial
from nachrichten_sentiment.store import load_articles


class _Model:
    def predict_proba(self, title: str) -> tuple[float, float, float]:
        return (0.6, 0.3, 0.1)


def _line(batch_id: str, record_id: str) -> str:
    cols = [""] * 27
    cols[0] = record_id
    cols[1] = batch_id
    cols[2] = "1"
    cols[3] = "example.com"
    cols[4] = f"https://example.com/{record_id}"
    cols[13] = "NVIDIA"
    cols[26] = f"<PAGE_TITLE>NVIDIA news {record_id}</PAGE_TITLE>"
    return "\t".join(cols)


def test_run_trial_rebuilds_daily_and_cli_parses():
    parser = build_parser()
    args = parser.parse_args(["tageslauf", "--day", "2015-02-19"])
    assert args.command == "tageslauf"
    assert args.day == "2015-02-19"
    args2 = parser.parse_args(["probelauf", "--start", "2019-09-23", "--days", "7"])
    assert args2.command == "probelauf"
    assert args2.start == "2019-09-23"
    args3 = parser.parse_args(["erstlauf", "--until", "20150218234500"])
    assert args3.until == "20150218234500"
```

Ergänze denselben Test oder einen zweiten Test `test_run_trial_week_writes_coverage`, der `run_trial` über einen Berlin-Tag mit vollständig erzeugten Fixture-Sätzen aufruft. Dafür in `tests/helpers.py` eine Funktion `make_gkg_text(batch_id: str, records: list[str]) -> str` ist nicht nötig: der Test übergibt `extract_zip` und `fetcher`, und für alle `expected_batch_ids_for_berlin_day(date(2019, 9, 23))` liefert `extract_zip` eine Leerdatei, außer für den ersten Satz mit einer Nvidia-Zeile. Nach `run_trial(..., start_day=date(2019, 9, 23), days=1)` muss `site/data/nvda-daily.json` einen Tag `2019-09-23` mit `coverage == "complete"` und `count_unique_url == 1` enthalten.

Vollständiger zweiter Test:

```python
# additional test in tests/test_cli_pipeline.py
import json

from nachrichten_sentiment.timeutil import expected_batch_ids_for_berlin_day


def test_run_trial_one_complete_day(tmp_path: Path, monkeypatch):
    from nachrichten_sentiment.companies import load_company

    # Point default_root at tmp only for written outputs, but load_company still reads repo config.
    paths = ProjectPaths(tmp_path)
    company = load_company("NVDA")
    day = date(2019, 9, 23)
    ids = expected_batch_ids_for_berlin_day(day)
    first = ids[0]

    def extract_zip(path: Path) -> str:
        batch_id = path.name.split(".")[0]
        if batch_id == first:
            return _line(batch_id, "hit-1")
        return ""

    run_trial(
        paths,
        company,
        _Model(),
        title_opener=lambda url, timeout: "",
        start_day=day,
        days=1,
        fetcher=lambda url: b"zip",
        extract_zip=extract_zip,
    )
    daily = json.loads((tmp_path / "site" / "data" / "nvda-daily.json").read_text(encoding="utf-8"))
    assert daily["days"][0]["date"] == "2019-09-23"
    assert daily["days"][0]["coverage"] == "complete"
    assert daily["days"][0]["count_unique_url"] == 1
    assert load_articles(paths, "NVDA")[0].title.startswith("NVIDIA news")
```

Beide Tests gehören in `tests/test_cli_pipeline.py`.

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_cli_pipeline.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.cli'` oder fehlendem `rebuild_outputs`.

- [ ] **Schritt 3: Minimale Implementierung**


An `src/nachrichten_sentiment/pipeline.py` anhängen:

```python
from datetime import date, datetime, timezone, timedelta

from nachrichten_sentiment.daily import aggregate_daily
from nachrichten_sentiment.dedup import mark_near_duplicates
from nachrichten_sentiment.progress import batches_to_process, load_progress, processed_batch_ids
from nachrichten_sentiment.store import load_articles, write_daily, write_headlines
from nachrichten_sentiment.timeutil import (
    FIRST_BERLIN_DAY,
    FIRST_BATCH_ID,
    expected_batch_ids_for_berlin_day,
    previous_berlin_day,
)


def rebuild_outputs(paths: ProjectPaths, company: CompanyConfig, progress: ProgressState) -> list:
    articles = mark_near_duplicates(load_articles(paths, company.ticker))
    processed = processed_batch_ids(progress)
    if progress.cursor_batch_id:
        from nachrichten_sentiment.timeutil import berlin_day_from_batch_id
        end_day = berlin_day_from_batch_id(progress.cursor_batch_id)
    else:
        end_day = FIRST_BERLIN_DAY
    rows = []
    day = FIRST_BERLIN_DAY
    while day <= end_day:
        rows.append(aggregate_daily(articles, day, processed))
        day += timedelta(days=1)
    write_daily(paths, company.ticker, rows, company.display_name)
    write_headlines(paths, company.ticker, articles)
    return rows


def run_batches(batch_ids: list[str], *, company, paths, model, title_opener, fetcher=None, extract_zip=None) -> None:
    progress = load_progress(paths.progress_path)
    url_index = UrlIndex()
    url_index.load_from_articles(load_articles(paths, company.ticker))
    already = processed_batch_ids(progress)
    for batch_id in batch_ids:
        if batch_id in already:
            continue
        process_batch(
            batch_id,
            company=company,
            paths=paths,
            url_index=url_index,
            model=model,
            title_opener=title_opener,
            progress=progress,
            fetcher=fetcher,
            extract_zip=extract_zip,
        )
    rebuild_outputs(paths, company, progress)


def run_initial(paths, company, model, title_opener, until_id: str | None = None, fetcher=None, extract_zip=None) -> None:
    progress = load_progress(paths.progress_path)
    if until_id is None:
        until_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        until_id = until_id[:12] + "00"
        minute = int(until_id[12:14])
        until_id = until_id[:12] + f"{(minute // 15) * 15:02d}00"
    run_batches(batches_to_process(progress, until_id), company=company, paths=paths, model=model, title_opener=title_opener, fetcher=fetcher, extract_zip=extract_zip)


def run_daily(paths, company, model, title_opener, day: date | None = None, fetcher=None, extract_zip=None) -> None:
    target = day or previous_berlin_day()
    wanted = expected_batch_ids_for_berlin_day(target)
    progress = load_progress(paths.progress_path)
    processed = processed_batch_ids(progress)
    todo = [batch_id for batch_id in progress.open_gaps]
    for batch_id in wanted:
        if batch_id not in processed and batch_id not in todo:
            todo.append(batch_id)
    run_batches(todo, company=company, paths=paths, model=model, title_opener=title_opener, fetcher=fetcher, extract_zip=extract_zip)


def run_trial(paths, company, model, title_opener, start_day: date, days: int = 7, fetcher=None, extract_zip=None) -> None:
    from datetime import timedelta
    last = start_day + timedelta(days=days - 1)
    until_id = expected_batch_ids_for_berlin_day(last)[-1]
    progress = load_progress(paths.progress_path)
    wanted: list[str] = []
    cursor = start_day
    while cursor <= last:
        wanted.extend(expected_batch_ids_for_berlin_day(cursor))
        cursor += timedelta(days=1)
    wanted_set = set(wanted)
    processed = processed_batch_ids(progress)
    todo = [batch_id for batch_id in progress.open_gaps if batch_id in wanted_set]
    for batch_id in wanted:
        if batch_id not in processed and batch_id not in todo:
            todo.append(batch_id)
    run_batches(todo, company=company, paths=paths, model=model, title_opener=title_opener, fetcher=fetcher, extract_zip=extract_zip)
```

`src/nachrichten_sentiment/cli.py`:

```python
from __future__ import annotations

import argparse
from datetime import date

from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.paths import ProjectPaths, default_root
from nachrichten_sentiment.pipeline import run_daily, run_initial, run_trial
from nachrichten_sentiment.titles import http_title_opener


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nachrichten-sentiment")
    sub = parser.add_subparsers(dest="command", required=True)
    erstlauf = sub.add_parser("erstlauf")
    erstlauf.add_argument("--until", default=None)
    tageslauf = sub.add_parser("tageslauf")
    tageslauf.add_argument("--day", default=None)
    probelauf = sub.add_parser("probelauf")
    probelauf.add_argument("--start", required=True)
    probelauf.add_argument("--days", type=int, default=7)
    probelauf.add_argument("--fixture-dir", default=None)
    return parser


def _model():
    from nachrichten_sentiment.sentiment import FinBertModel

    return FinBertModel()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = ProjectPaths(default_root())
    company = load_company("NVDA")
    model = _model()
    if args.command == "erstlauf":
        run_initial(paths, company, model, http_title_opener, until_id=args.until)
    elif args.command == "tageslauf":
        day = date.fromisoformat(args.day) if args.day else None
        run_daily(paths, company, model, http_title_opener, day=day)
    elif args.command == "probelauf":
        fetcher = extract_zip = None
        if args.fixture_dir:
            from pathlib import Path
            fixture = Path(args.fixture_dir)

            def fetcher(url: str) -> bytes:
                batch_id = url.rsplit("/", 1)[-1].split(".")[0]
                return (fixture / f"{batch_id}.gkg.csv.zip").read_bytes()

        run_trial(paths, company, model, http_title_opener, date.fromisoformat(args.start), days=args.days, fetcher=fetcher)
    return 0
```

`src/nachrichten_sentiment/__main__.py`:

```python
from nachrichten_sentiment.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

`README.md`:

~~~~markdown
# Nachrichten-Sentiment

Eigenständiges Werkzeug zur taggenauen Auswertung der Nachrichtenlage von Nvidia (NVDA). Es ist nicht Teil der App SE Aktien, liefert keine Kursdaten und keine Handelssignale.

## Installation

    python3 -m pip install -e ".[dev,ml]"

## Befehle

    python -m nachrichten_sentiment erstlauf
    python -m nachrichten_sentiment erstlauf --until 20150218234500
    python -m nachrichten_sentiment tageslauf
    python -m nachrichten_sentiment tageslauf --day 2019-09-23
    python -m nachrichten_sentiment probelauf --start 2019-09-23 --days 7
    python -m nachrichten_sentiment probelauf --start 2019-09-23 --days 7 --fixture-dir tests/tmp-fixtures

Der Erstlauf startet bei der GKG-Datei `20150218230000` (erster Berlin-Tag: 19. Februar 2015) und ist über `data/state/progress.json` fortsetzbar. Er sollte lokal laufen. Der tägliche Lauf verarbeitet den Vortag in Europe/Berlin und holt offene Lücken nach. Eine GitHub Action startet ihn um 06:00 Europe/Berlin und veröffentlicht `site/` nur bei Erfolg auf GitHub Pages.

Tage ohne vollständige Quellabdeckung erscheinen im Diagramm als Lücke, nicht als Anzahl 0. Tests: `pytest -m "not finbert"`. Der echte Modelltest: `pytest -m finbert`.
~~~~

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_cli_pipeline.py tests/test_pipeline_batch.py -v`

Expected: PASS.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/pipeline.py src/nachrichten_sentiment/cli.py src/nachrichten_sentiment/__main__.py README.md tests/test_cli_pipeline.py
git commit -m "feat: CLI für Erstlauf, Tageslauf und Probelauf"
```

### Aufgabe 18: Webseite mit divergierenden Balken und Stimmungslinie

**Dateien:**
- Create: `site/chart_data.js`
- Create: `site/index.html`
- Create: `site/app.js`
- Create: `site/lwc.js` (Vendor, per Befehl)
- Test: `tests/test_chart_data.js`
- Test: `tests/test_site_assets.py`

**Schnittstellen:**
- Nutzt: das JSON-Format aus Aufgabe 15 (`days[]` mit `date`, `count_unique_url`, `count_after_near_dup_collapse`, `count_positive`, `count_neutral`, `count_negative`, `count_without_sentiment`, `sentiment_mean`, `coverage`).
- Liefert: in `site/chart_data.js` (ohne DOM, in Node testbar) `formatTooltip(row) -> string`, `toBarSeries(days) -> { up: Array<{time: string, value: number|null}>, down: Array<{time: string, value: number|null}> }`, `toLineSeries(days) -> Array<{time: string, value: number|null, color: string}>`, `rangeStart(endDate: string, rangeKey: string) -> string | null`. Lückentage (`coverage === "gap"`) haben `value: null` in beiden Balken- und der Linienserie, niemals 0. Zeitraum-Schlüssel: `1M`, `3M`, `1J`, `5J`, `max`. Farben `#26a69a` und `#ef5350` wörtlich.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```javascript
// tests/test_chart_data.js
const assert = require("node:assert/strict");
const test = require("node:test");
const {
  formatTooltip,
  toBarSeries,
  toLineSeries,
  rangeStart,
} = require("../site/chart_data.js");

test("tooltip lists counts and German sentiment", () => {
  const text = formatTooltip({
    count_unique_url: 120,
    count_positive: 45,
    count_neutral: 50,
    count_negative: 25,
    count_without_sentiment: 0,
    count_after_near_dup_collapse: 110,
    sentiment_mean: 0.18,
    coverage: "complete",
  });
  assert.equal(
    text,
    "120 Nachrichten: 45 positiv, 50 neutral, 25 negativ, Stimmung +0,18 (110 ohne Nahduplikate)"
  );
});

test("tooltip mentions missing scores and dashes sentiment", () => {
  const text = formatTooltip({
    count_unique_url: 5,
    count_positive: 0,
    count_neutral: 0,
    count_negative: 0,
    count_without_sentiment: 5,
    count_after_near_dup_collapse: 5,
    sentiment_mean: null,
    coverage: "complete",
  });
  assert.match(text, /5 ohne Wert/);
  assert.match(text, /Stimmung —/);
});

test("bars go up green and down red, gaps are null not zero", () => {
  const days = [
    {
      date: "2019-09-23",
      count_positive: 2,
      count_negative: 3,
      sentiment_mean: -0.1,
      coverage: "complete",
    },
    {
      date: "2019-09-24",
      count_positive: 0,
      count_negative: 0,
      sentiment_mean: null,
      coverage: "gap",
    },
  ];
  const bars = toBarSeries(days);
  assert.equal(bars.up[0].value, 2);
  assert.equal(bars.down[0].value, -3);
  assert.equal(bars.up[1].value, null);
  assert.equal(bars.down[1].value, null);
  const line = toLineSeries(days);
  assert.equal(line[0].value, -0.1);
  assert.equal(line[0].color, "#ef5350");
  assert.equal(line[1].value, null);
});

test("range chips use Berlin calendar days", () => {
  assert.equal(rangeStart("2026-11-22", "1M"), "2026-10-22");
  assert.equal(rangeStart("2026-11-22", "3M"), "2026-08-22");
  assert.equal(rangeStart("2026-11-22", "1J"), "2025-11-22");
  assert.equal(rangeStart("2026-11-22", "5J"), "2021-11-22");
  assert.equal(rangeStart("2026-11-22", "max"), null);
});
```

```python
# tests/test_site_assets.py
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
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `node --test tests/test_chart_data.js`

Expected: FAIL mit `Cannot find module '../site/chart_data.js'`.

Run: `pytest tests/test_site_assets.py -v`

Expected: FAIL, Datei `site/index.html` fehlt.

- [ ] **Schritt 3: Minimale Implementierung**

`site/chart_data.js`:

```javascript
"use strict";

function formatNumber(value) {
  const sign = value > 0 ? "+" : value < 0 ? "\u2212" : "";
  const abs = Math.abs(value);
  return sign + abs.toFixed(2).replace(".", ",");
}

function formatTooltip(row) {
  let text =
    row.count_unique_url +
    " Nachrichten: " +
    row.count_positive +
    " positiv, " +
    row.count_neutral +
    " neutral, " +
    row.count_negative +
    " negativ";
  if (row.sentiment_mean === null || row.sentiment_mean === undefined) {
    text += ", Stimmung —";
  } else {
    const formatted =
      row.sentiment_mean > 0
        ? "+" + row.sentiment_mean.toFixed(2).replace(".", ",")
        : formatNumber(row.sentiment_mean);
    text += ", Stimmung " + formatted;
  }
  if (row.count_without_sentiment > 0) {
    text += ", " + row.count_without_sentiment + " ohne Wert";
  }
  if (row.count_after_near_dup_collapse !== undefined) {
    text += " (" + row.count_after_near_dup_collapse + " ohne Nahduplikate)";
  }
  return text;
}

function toBarSeries(days) {
  const up = [];
  const down = [];
  for (const day of days) {
    const gap = day.coverage === "gap";
    up.push({ time: day.date, value: gap ? null : day.count_positive });
    down.push({ time: day.date, value: gap ? null : -day.count_negative });
  }
  return { up, down };
}

function toLineSeries(days) {
  return days.map((day) => {
    if (day.coverage === "gap" || day.sentiment_mean === null || day.sentiment_mean === undefined) {
      return { time: day.date, value: null, color: "#8b949e" };
    }
    return {
      time: day.date,
      value: day.sentiment_mean,
      color: day.sentiment_mean >= 0 ? "#26a69a" : "#ef5350",
    };
  });
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function shiftDate(iso, months, years) {
  const [year, month, day] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCFullYear(date.getUTCFullYear() + years);
  date.setUTCMonth(date.getUTCMonth() + months);
  return (
    date.getUTCFullYear() +
    "-" +
    pad(date.getUTCMonth() + 1) +
    "-" +
    pad(date.getUTCDate())
  );
}

function rangeStart(endDate, rangeKey) {
  if (rangeKey === "1M") return shiftDate(endDate, -1, 0);
  if (rangeKey === "3M") return shiftDate(endDate, -3, 0);
  if (rangeKey === "1J") return shiftDate(endDate, 0, -1);
  if (rangeKey === "5J") return shiftDate(endDate, 0, -5);
  return null;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { formatTooltip, toBarSeries, toLineSeries, rangeStart };
}
```

`site/index.html`:

```html
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0d1117">
  <title>Nachrichten-Sentiment</title>
  <style>
    :root{--bg:#0d1117;--card:#161b22;--line:#30363d;--txt:#e6edf3;--mut:#8b949e;--up:#26a69a;--down:#ef5350;--acc:#58a6ff}
    *{box-sizing:border-box}
    html,body{margin:0;min-height:100%;background:var(--bg);color:var(--txt);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
    header,main,footer{max-width:960px;margin:0 auto;padding:12px 16px}
    h1{font-size:22px;margin:0}
    .sub{color:var(--mut);margin-top:4px}
    .ranges{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
    .ranges button{background:transparent;border:1px solid var(--line);color:var(--mut);border-radius:999px;padding:5px 11px;font-size:13px}
    .ranges button.on{background:#1f2937;color:var(--txt);border-color:var(--acc)}
    #bars,#line{height:220px;background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:12px}
    #tooltip{font-size:13px;color:var(--mut);min-height:20px}
    #headlines{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}
    #headlines h2{font-size:16px;margin:0 0 8px}
    #headlines a{color:var(--acc)}
    .dup{color:var(--mut);margin-left:16px}
    footer{font-size:10px;color:#6e7681;text-align:center}
  </style>
</head>
<body>
  <header>
    <h1>Nachrichten-Sentiment</h1>
    <div class="sub">Nvidia (NVDA)</div>
    <p class="sub">Die Balken zählen positive und negative Nachrichten nach der FinBERT-Klasse (argmax). Die Linie zeigt den abgestuften Tagesmittelwert von P(positiv) minus P(negativ) und kann deshalb von den Balken abweichen. Neutrale Nachrichten und die Gesamtzahl stehen im Tooltip.</p>
    <div class="ranges" id="ranges">
      <button data-range="1M">1 Monat</button>
      <button data-range="3M">3 Monate</button>
      <button data-range="1J">1 Jahr</button>
      <button data-range="5J">5 Jahre</button>
      <button data-range="max" class="on">Maximum</button>
    </div>
    <div id="tooltip"></div>
  </header>
  <main>
    <div id="bars"></div>
    <div id="line"></div>
    <section id="headlines"><h2>Schlagzeilen</h2><p class="sub">Klicken Sie auf einen Tag.</p></section>
  </main>
  <footer>Nachrichtenlage zur Aktiengesellschaft, keine Anlageberatung.</footer>
  <script src="lwc.js"></script>
  <script src="chart_data.js"></script>
  <script src="app.js"></script>
</body>
</html>
```

`site/app.js` (vollständig): lädt `data/nvda-daily.json`, erzeugt zwei Chart-Bereiche mit Lightweight Charts, obere Histogram-Serien in `#26a69a` (positiv) und `#ef5350` (negativ, Werte negativ), untere Linie mit Punktfarbe aus `toLineSeries`, Nulllinien, Crosshair-Tooltip über `formatTooltip`, Zeitraum-Chips mit `rangeStart`, Klick lädt `data/nvda/YYYY-MM.json` und rendert URL-eindeutige Schlagzeilen, Nahduplikate eingerückt unter der Stammzeile, fehlender Titel als „Titel nicht verfügbar“, Lückentage mit Hinweis „unvollständig“.

```javascript
"use strict";

async function loadDaily() {
  const response = await fetch("data/nvda-daily.json");
  return response.json();
}

function lastCompleteDate(days) {
  for (let i = days.length - 1; i >= 0; i -= 1) {
    if (days[i].coverage === "complete") return days[i].date;
  }
  return days.length ? days[days.length - 1].date : null;
}

function attachCharts(days) {
  const barHost = document.getElementById("bars");
  const lineHost = document.getElementById("line");
  const tooltip = document.getElementById("tooltip");
  const barChart = LightweightCharts.createChart(barHost, {
    layout: { background: { color: "#161b22" }, textColor: "#e6edf3" },
    grid: { vertLines: { color: "#30363d" }, horzLines: { color: "#30363d" } },
    rightPriceScale: { borderColor: "#30363d" },
    timeScale: { borderColor: "#30363d" },
  });
  const lineChart = LightweightCharts.createChart(lineHost, {
    layout: { background: { color: "#161b22" }, textColor: "#e6edf3" },
    grid: { vertLines: { color: "#30363d" }, horzLines: { color: "#30363d" } },
    rightPriceScale: { borderColor: "#30363d" },
    timeScale: { borderColor: "#30363d" },
  });
  const up = barChart.addHistogramSeries({ color: "#26a69a", priceFormat: { type: "volume" } });
  const down = barChart.addHistogramSeries({ color: "#ef5350", priceFormat: { type: "volume" } });
  const line = lineChart.addLineSeries({ color: "#e6edf3", priceLineVisible: true });
  const bars = toBarSeries(days);
  const linePoints = toLineSeries(days);
  up.setData(bars.up);
  down.setData(bars.down);
  line.setData(linePoints.map((p) => ({ time: p.time, value: p.value })));
  const byDate = Object.fromEntries(days.map((d) => [d.date, d]));

  function showTip(date) {
    const row = byDate[date];
    tooltip.textContent = row ? formatTooltip(row) : "";
  }

  barChart.subscribeCrosshairMove((param) => {
    if (param && param.time) showTip(param.time);
  });
  barChart.subscribeClick((param) => {
    if (param && param.time) openDay(param.time, byDate[param.time]);
  });
  document.getElementById("ranges").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    document.querySelectorAll("#ranges button").forEach((el) => el.classList.remove("on"));
    button.classList.add("on");
    const end = lastCompleteDate(days);
    const start = rangeStart(end, button.getAttribute("data-range"));
    if (!start) {
      barChart.timeScale().fitContent();
      lineChart.timeScale().fitContent();
      return;
    }
    barChart.timeScale().setVisibleRange({ from: start, to: end });
    lineChart.timeScale().setVisibleRange({ from: start, to: end });
  });
  barChart.timeScale().fitContent();
  lineChart.timeScale().fitContent();
}

async function openDay(date, row) {
  const root = document.getElementById("headlines");
  const month = date.slice(0, 7);
  const payload = await fetch("data/nvda/" + month + ".json").then((r) => r.json());
  const items = payload[date] || [];
  const stems = items.filter((item) => !item.is_near_duplicate);
  const dups = items.filter((item) => item.is_near_duplicate);
  const grouped = stems.map((stem) => {
    const children = dups.filter((item) => item.near_duplicate_of === stem.gkg_record_id);
    return { stem, children };
  });
  const note = row && row.coverage === "gap" ? " (unvollständig)" : "";
  root.innerHTML = "<h2>Schlagzeilen " + date + note + "</h2>" + grouped.map((group) => {
    const title = group.stem.title || "Titel nicht verfügbar";
    const value = group.stem.sentiment === null || group.stem.sentiment === undefined
      ? "—"
      : String(group.stem.sentiment);
    const main = '<div><a href="' + group.stem.url + '" target="_blank" rel="noopener">' + title + "</a> " + value + "</div>";
    const extra = group.children.map((child) => {
      const ct = child.title || "Titel nicht verfügbar";
      return '<div class="dup"><a href="' + child.url + '" target="_blank" rel="noopener">' + ct + "</a></div>";
    }).join("");
    return main + extra;
  }).join("");
}

loadDaily().then((payload) => attachCharts(payload.days || []));
```

Vendor-Datei holen (Version fest, lokal einbinden, kein CDN zur Laufzeit):

```bash
python3 - << 'PY'
import urllib.request, pathlib
url = "https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"
path = pathlib.Path("site/lwc.js")
path.write_bytes(urllib.request.urlopen(url).read())
print("wrote", path, path.stat().st_size)
PY
```

Falls der Download fehlschlägt, `site/lwc.js` aus dem lokalen SE-Aktien-Stand `/workspace/aktien-pages/site/lwc.js` kopieren: `cp /workspace/aktien-pages/site/lwc.js site/lwc.js`.

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `node --test tests/test_chart_data.js && pytest tests/test_site_assets.py -v`

Expected: PASS.

- [ ] **Schritt 5: Commit**

```bash
git add site/chart_data.js site/index.html site/app.js site/lwc.js tests/test_chart_data.js tests/test_site_assets.py
git commit -m "feat: Webseite mit divergierenden Balken, Stimmungslinie und SE-Aktien-Farben"
```

### Aufgabe 19: GitHub Action um 06:00 Europe/Berlin und Pages-Deploy

**Dateien:**
- Create: `src/nachrichten_sentiment/schedule.py`
- Create: `.github/workflows/daily.yml`
- Test: `tests/test_schedule.py`

**Schnittstellen:**
- Nutzt: Zeitzone Europe/Berlin.
- Liefert: `should_run_scheduled(now_utc: datetime, event_name: str) -> bool` ist `True` bei `event_name == "workflow_dispatch"` oder wenn `now_utc` in Europe/Berlin die Stunde 6 hat. Die Workflow-Datei enthält zwei Cron-Einträge `0 4 * * *` (06:00 während CEST, UTC+2) und `0 5 * * *` (06:00 während CET, UTC+1), dazu `workflow_dispatch`. Der Job bricht mit Exit 0 ab, wenn `should_run_scheduled` falsch ist. Der Tageslauf läuft danach; das Pages-Deploy (`actions/upload-pages-artifact` von `site/`, `actions/deploy-pages`) hängt an `if: success()` und entfällt bei Fehlschlag des Sammlers. GitHub sendet dann die Standard-Fehlermail an den Inhaber.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/test_schedule.py
from datetime import datetime, timezone
from pathlib import Path

from nachrichten_sentiment.schedule import should_run_scheduled

ROOT = Path(__file__).resolve().parents[1]


def test_should_run_only_at_06_berlin_or_manual():
    # 05:00 UTC = 06:00 CET (Winter 2026-01-15)
    winter = datetime(2026, 1, 15, 5, 0, tzinfo=timezone.utc)
    assert should_run_scheduled(winter, "schedule") is True
    # 04:00 UTC = 05:00 CET, nicht ausführen
    assert should_run_scheduled(datetime(2026, 1, 15, 4, 0, tzinfo=timezone.utc), "schedule") is False
    # 04:00 UTC = 06:00 CEST (Sommer 2026-07-15)
    summer = datetime(2026, 7, 15, 4, 0, tzinfo=timezone.utc)
    assert should_run_scheduled(summer, "schedule") is True
    assert should_run_scheduled(datetime(2026, 7, 15, 5, 0, tzinfo=timezone.utc), "schedule") is False
    assert should_run_scheduled(datetime(2026, 1, 15, 4, 0, tzinfo=timezone.utc), "workflow_dispatch") is True


def test_workflow_has_both_cron_entries_and_conditional_deploy():
    text = (ROOT / ".github" / "workflows" / "daily.yml").read_text(encoding="utf-8")
    assert "cron: '0 4 * * *'" in text
    assert "cron: '0 5 * * *'" in text
    assert "workflow_dispatch" in text
    assert "should_run_scheduled" in text
    assert "python -m nachrichten_sentiment tageslauf" in text
    assert "actions/deploy-pages" in text
    assert "if: success()" in text
    assert "site/" in text
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_schedule.py -v`

Expected: FAIL mit `ModuleNotFoundError: No module named 'nachrichten_sentiment.schedule'` oder fehlender Workflow-Datei.

- [ ] **Schritt 3: Minimale Implementierung**

```python
# src/nachrichten_sentiment/schedule.py
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")


def should_run_scheduled(now_utc: datetime, event_name: str) -> bool:
    if event_name == "workflow_dispatch":
        return True
    current = now_utc.astimezone(BERLIN)
    return current.hour == 6
```

`.github/workflows/daily.yml`:

```yaml
name: Tageslauf und GitHub Pages

on:
  schedule:
    - cron: '0 4 * * *'
    - cron: '0 5 * * *'
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

concurrency:
  group: daily-pages
  cancel-in-progress: false

jobs:
  collect-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Abhängigkeiten
        run: python -m pip install -e ".[ml]"
      - name: Stunde in Europe/Berlin prüfen
        env:
          EVENT_NAME: ${{ github.event_name }}
        run: |
          python - << 'PY'
          import os, sys
          from datetime import datetime, timezone
          from nachrichten_sentiment.schedule import should_run_scheduled
          event = os.environ["EVENT_NAME"]
          if not should_run_scheduled(datetime.now(timezone.utc), event):
              print("skip: not 06:00 Europe/Berlin")
              sys.exit(0)
          open("run.flag", "w").write("yes")
          PY
      - name: Tageslauf
        if: hashFiles('run.flag') != '' || github.event_name == 'workflow_dispatch'
        env:
          HF_HOME: ${{ github.workspace }}/.hf-cache
        run: python -m nachrichten_sentiment tageslauf
      - name: Stand committen
        if: success() && (hashFiles('run.flag') != '' || github.event_name == 'workflow_dispatch')
        run: |
          git config user.name "ExplorationSE"
          git config user.email "ExplorationSE@users.noreply.github.com"
          git add data site
          git diff --cached --quiet || git commit -m "data: Tageslauf $(date -u +%Y-%m-%dT%H:%MZ)"
          git push
      - uses: actions/upload-pages-artifact@v3
        if: success() && (hashFiles('run.flag') != '' || github.event_name == 'workflow_dispatch')
        with:
          path: site/
      - uses: actions/deploy-pages@v4
        if: success() && (hashFiles('run.flag') != '' || github.event_name == 'workflow_dispatch')
```

Die Bedingung `if: success()` verhindert ein neues Pages-Deploy, wenn der Tageslauf fehlschlägt; die bisherige Seite bleibt online. Ein Skip um 04:00 UTC im Winter erzeugt keine `run.flag` und überspringt Sammler sowie Deploy.

Für `workflow_dispatch` muss der Stunden-Schritt ebenfalls `run.flag` schreiben, weil `should_run_scheduled(..., "workflow_dispatch")` wahr ist.

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_schedule.py -v`

Expected: PASS, zwei Tests.

- [ ] **Schritt 5: Commit**

```bash
git add src/nachrichten_sentiment/schedule.py .github/workflows/daily.yml tests/test_schedule.py
git commit -m "feat: GitHub Action um 06:00 Europe/Berlin mit bedingtem Pages-Deploy"
```

### Aufgabe 20: Probelauf über eine Woche als Gesamttest

**Dateien:**
- Create: `tests/test_trial_week.py`
- Create: `tests/fixtures/build_week.py`

**Schnittstellen:**
- Nutzt: `run_trial`, `ProjectPaths`, `load_company`, `load_articles`, `load_progress`, `expected_batch_ids_for_berlin_day`, Fixture-Öffner aus den Tests.
- Liefert: einen automatisierten Gesamttest über sieben Berlin-Tage ab 2019-09-23 (GKG-Titel sind dann enthalten): alle erwarteten 15-Minuten-Sätze als minimale ZIPs, die meisten ohne Treffer, ausgewählte Sätze mit Nvidia-Titeln, ein künstlich fehlender Satz als Lücke, Fortsetzen nach Unterbrechung und Prüfung von `nvda-daily.json` plus einer Schlagzeilen-Datei.

- [ ] **Schritt 1: Fehlschlagenden Test schreiben**

```python
# tests/fixtures/build_week.py
from __future__ import annotations

import io
import zipfile
from datetime import date, timedelta
from pathlib import Path

from nachrichten_sentiment.timeutil import expected_batch_ids_for_berlin_day


def gkg_zip_bytes(batch_id: str, body: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"{batch_id}.gkg.csv", body)
    return buffer.getvalue()


def nvidia_line(batch_id: str, record_id: str, title: str) -> str:
    cols = [""] * 27
    cols[0] = record_id
    cols[1] = batch_id
    cols[2] = "1"
    cols[3] = "example.com"
    cols[4] = f"https://example.com/{record_id}"
    cols[13] = "NVIDIA"
    cols[14] = "NVIDIA,10"
    cols[26] = f"<PAGE_TITLE>{title}</PAGE_TITLE>"
    return "\t".join(cols) + "\n"


def write_week(dest: Path, start: date, days: int = 7, missing_batch_id: str | None = None) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    ids: list[str] = []
    for offset in range(days):
        ids.extend(expected_batch_ids_for_berlin_day(start + timedelta(days=offset)))
    first_per_day = []
    cursor = start
    for _ in range(days):
        first_per_day.append(expected_batch_ids_for_berlin_day(cursor)[0])
        cursor += timedelta(days=1)
    for batch_id in ids:
        if batch_id == missing_batch_id:
            continue
        if batch_id in first_per_day:
            body = nvidia_line(batch_id, f"hit-{batch_id}", "NVIDIA raises forecast")
        else:
            body = ""
        (dest / f"{batch_id}.gkg.csv.zip").write_bytes(gkg_zip_bytes(batch_id, body))
    return ids
```

```python
# tests/test_trial_week.py
import json
from datetime import date
from pathlib import Path

from nachrichten_sentiment.companies import load_company
from nachrichten_sentiment.download import MissingGkgError
from nachrichten_sentiment.paths import ProjectPaths
from nachrichten_sentiment.pipeline import run_trial
from nachrichten_sentiment.progress import load_progress
from nachrichten_sentiment.store import load_articles
from nachrichten_sentiment.timeutil import expected_batch_ids_for_berlin_day
from tests.fixtures.build_week import write_week


class _Model:
    def predict_proba(self, title: str) -> tuple[float, float, float]:
        return (0.7, 0.2, 0.1)


def test_trial_week_gap_resume_and_site_files(tmp_path: Path):
    start = date(2019, 9, 23)
    fixture = tmp_path / "fixtures"
    missing = expected_batch_ids_for_berlin_day(start)[10]
    write_week(fixture, start, days=7, missing_batch_id=missing)
    paths = ProjectPaths(tmp_path)
    company = load_company("NVDA")

    def fetcher(url: str) -> bytes:
        batch_id = url.rsplit("/", 1)[-1].split(".")[0]
        file = fixture / f"{batch_id}.gkg.csv.zip"
        if not file.exists():
            raise MissingGkgError(batch_id)
        return file.read_bytes()

    # Interrupt after the first two batches of the first day by pre-limiting via a wrapper.
    seen = {"n": 0}
    real_fetcher = fetcher

    def fetcher_once(url: str) -> bytes:
        seen["n"] += 1
        if seen["n"] > 3:
            raise RuntimeError("interrupted")
        return real_fetcher(url)

    try:
        run_trial(paths, company, _Model(), lambda url, timeout: "", start, days=7, fetcher=fetcher_once)
    except RuntimeError:
        pass
    mid = load_progress(paths.progress_path)
    assert mid.cursor_batch_id is not None
    # Resume with the full fetcher.
    run_trial(paths, company, _Model(), lambda url, timeout: "", start, days=7, fetcher=fetcher)
    progress = load_progress(paths.progress_path)
    assert missing in progress.open_gaps
    daily = json.loads((tmp_path / "site" / "data" / "nvda-daily.json").read_text(encoding="utf-8"))
    days = {row["date"]: row for row in daily["days"]}
    assert days["2019-09-23"]["coverage"] == "gap"
    assert days["2019-09-23"]["count_unique_url"] == 1
    assert days["2019-09-24"]["coverage"] == "complete"
    assert days["2019-09-24"]["count_unique_url"] == 1
    assert days["2019-09-24"]["count_positive"] == 1
    assert days["2019-09-24"]["sentiment_mean"] == 0.6
    assert "2019-09-29" in days
    headlines = json.loads((tmp_path / "site" / "data" / "nvda" / "2019-09.json").read_text(encoding="utf-8"))
    assert headlines["2019-09-24"][0]["title"] == "NVIDIA raises forecast"
    assert len(load_articles(paths, "NVDA")) == 7
```

Zweiter Test in `tests/test_trial_week.py` für das Titelnachladen:

```python
def test_trial_fetches_title_when_page_title_missing(tmp_path: Path):
    from tests.fixtures.build_week import gkg_zip_bytes

    paths = ProjectPaths(tmp_path)
    company = load_company("NVDA")
    day = date(2019, 9, 24)
    ids = expected_batch_ids_for_berlin_day(day)
    first = ids[0]
    cols = [""] * 27
    cols[0] = "fetch-1"
    cols[1] = first
    cols[2] = "1"
    cols[3] = "example.com"
    cols[4] = "https://example.com/fetch-1"
    cols[13] = "NVIDIA"
    cols[26] = ""
    body = "\t".join(cols) + "\n"

    def fetcher(url: str) -> bytes:
        batch_id = url.rsplit("/", 1)[-1].split(".")[0]
        payload = body if batch_id == first else ""
        return gkg_zip_bytes(batch_id, payload)

    def opener(url: str, timeout: float) -> str:
        return "<html><title>Fetched NVIDIA title</title></html>"

    run_trial(paths, company, _Model(), opener, day, days=1, fetcher=fetcher)
    article = load_articles(paths, "NVDA")[0]
    assert article.title_source == "fetched"
    assert article.title == "Fetched NVIDIA title"
```

- [ ] **Schritt 2: Test ausführen und Fehlschlag prüfen**

Run: `pytest tests/test_trial_week.py -v`

Expected: FAIL, bis `tests/fixtures/build_week.py` und der Testdateipfad existieren, bzw. PASS der Hilfsfunktion erst nach Schritt 3; ohne `write_week` schlägt der Import fehl.

- [ ] **Schritt 3: Minimale Implementierung**

Die Datei `tests/fixtures/build_week.py` aus Schritt 1 unverändert anlegen. Zusätzlich die leere Datei `tests/fixtures/__init__.py` anlegen, damit `from tests.fixtures.build_week import write_week` funktioniert. In dieser Aufgabe entsteht kein neuer Produktionscode: `run_trial` aus Aufgabe 17 lädt vorhandene Artikel in `UrlIndex`, überspringt bereits verarbeitete Sätze und arbeitet offene Lücken sowie die restlichen Sätze der Woche beim zweiten Aufruf ab.

- [ ] **Schritt 4: Test ausführen und Erfolg prüfen**

Run: `pytest tests/test_trial_week.py tests/test_cli_pipeline.py tests/test_pipeline_batch.py tests/test_progress.py tests/test_daily.py -v`

Expected: PASS. Anschließend die bisherige Suite ohne das echte Modell:

Run: `pytest -m "not finbert" -v`

Expected: PASS.

Der manuelle Befehl für einen echten GDELT-Probelauf (nicht Teil der automatischen Suite, nach dem Bestehen der Fixtures) lautet:

```bash
python -m nachrichten_sentiment probelauf --start 2019-09-23 --days 7
```

- [ ] **Schritt 5: Commit**

```bash
git add tests/test_trial_week.py tests/fixtures/build_week.py tests/fixtures/__init__.py
git commit -m "test: Probelauf über sieben Berlin-Tage mit Lücke und Fortsetzen"
```

