# Nachrichten-Sentiment

Eigenständiges Werkzeug zur taggenauen Auswertung der Nachrichtenlage von Nvidia (NVDA). Es ist nicht Teil der App SE Aktien, liefert keine Kursdaten und keine Handelssignale.

## Installation

    python3 -m pip install -e ".[dev,ml]"

## Befehle

    python -m nachrichten_sentiment erstlauf
    python -m nachrichten_sentiment erstlauf --until 20150218234500
    python -m nachrichten_sentiment erstlauf --luecken-erneut
    python -m nachrichten_sentiment tageslauf
    python -m nachrichten_sentiment tageslauf --day 2019-09-23
    python -m nachrichten_sentiment tageslauf --voll-neuaufbau
    python -m nachrichten_sentiment probelauf --start 2019-09-23 --days 7
    python -m nachrichten_sentiment probelauf --start 2019-09-23 --days 7 --fixture-dir tests/tmp-fixtures

Der Erstlauf startet bei der GKG-Datei `20150218230000` (erster Berlin-Tag: 19. Februar 2015) und ist über `data/state/progress.json` fortsetzbar. Er sollte lokal laufen. Der Probelauf speichert getrennt vom Echtbetrieb unter `probe/` (eigene `data/` und `site/data/`, per `.gitignore` ausgeschlossen; anderer Ort mit `--root PFAD`) und verändert den Fortschritt des Erst- und Tageslaufs nicht. Der tägliche Lauf verarbeitet den Vortag in Europe/Berlin und holt offene Lücken nach. Eine GitHub Action startet ihn um 06:00 Europe/Berlin und veröffentlicht `site/` nur bei Erfolg auf GitHub Pages.

Tage ohne vollständige Quellabdeckung erscheinen im Diagramm als Lücke, nicht als Anzahl 0.

Optionen für `erstlauf` und `tageslauf`:

- `--luecken-erneut`: holt auch an der Quelle fehlende Sätze (GDELT antwortet mit 404) erneut ab, die älter als 7 Tage sind. Ohne diese Option werden sie nur in den ersten 7 Tagen nach ihrem Zeitstempel erneut versucht.
- `--voll-neuaufbau`: berechnet Nahduplikate, Monatsdateien und Schlagzeilen für alle Tage neu. Ohne die Option geschieht das nur für die Berlin-Tage der in diesem Lauf verarbeiteten Sätze.

## Erstlauf: Umfang und Dauer

Der Erstlauf verarbeitet rund 405.000 GKG-Dateien (alle 15 Minuten seit Februar 2015), das sind etwa 3 TB Download. Er dauert mehrere Tage und ist jederzeit fortsetzbar: Nach jeder Datei wird `data/state/progress.json` atomar geschrieben, fehlgeschlagene Titelabrufe landen in `data/state/failed_titles.jsonl`. Vor etwa September 2019 enthält GDELT keine Seitentitel, daher lädt der Erstlauf für diese Jahre den Titel jedes Nvidia-Artikels von der Originalseite nach (mit kurzer Pause pro Abruf), was den Großteil der Laufzeit ausmacht.

Rund 658 Tage enthalten mindestens eine 15-Minuten-Datei, die bei GDELT dauerhaft fehlt (HTTP 404). Diese Tage erscheinen als Lücke mit dem Hinweis „Quelle fehlt (GDELT)“ im Tooltip. Solche Sätze stehen in `missing_at_source` in `progress.json` und werden nach 7 Tagen nicht mehr automatisch erneut abgerufen (siehe `--luecken-erneut`). Andere Fehler (Netzwerk, defekte ZIP-Datei) bleiben offene Lücken und werden bei jedem Lauf erneut versucht.

Den fertigen Erstlauf-Stand (`data/` und `site/data/`) committen, bevor die GitHub Action aktiviert wird, damit der tägliche Lauf darauf aufbaut.

## GitHub einrichten

1. Settings → Pages → Build and deployment → Source: **GitHub Actions**.
2. Settings → Actions → General → Workflow permissions: **Read and write permissions**, damit die Action den Tagesstand committen kann.
3. E-Mail bei Fehlschlag: im Konto ExplorationSE unter Settings → Notifications → Actions die Benachrichtigung „Send notifications for failed workflows only“ per E-Mail einschalten.
4. Die Action `.github/workflows/daily.yml` läuft um 04:00 und 05:00 UTC und arbeitet nur, wenn es in Europe/Berlin 06:00 ist (Sommer- und Winterzeit); manuell über „Run workflow“. Nur bei Erfolg wird `site/` auf GitHub Pages veröffentlicht.

## Tests

    pytest -m "not finbert"
    HF_HOME=.hf-cache pytest -m finbert     # echtes FinBERT-Modell, lädt es beim ersten Mal herunter
    node --test tests/test_chart_data.js    # Diagramm- und Tooltip-Logik der Seite

Testdateien für den Probelauf mit `--fixture-dir tests/tmp-fixtures` erzeugen (sieben Tage ab 23.09.2019, je Tag eine Nvidia-Meldung):

    python -c "from datetime import date; from pathlib import Path; from tests.fixtures.build_week import write_week; write_week(Path('tests/tmp-fixtures'), date(2019, 9, 23), days=7)"
