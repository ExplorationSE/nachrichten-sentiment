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

Der Erstlauf startet bei der GKG-Datei `20150218230000` (erster Berlin-Tag: 19. Februar 2015) und ist über `data/state/progress.json` fortsetzbar. Er sollte lokal laufen. Der Probelauf speichert getrennt vom Echtbetrieb unter `probe/` (eigene `data/` und `site/data/`, per `.gitignore` ausgeschlossen; anderer Ort mit `--root PFAD`) und verändert den Fortschritt des Erst- und Tageslaufs nicht. Der tägliche Lauf verarbeitet den Vortag in Europe/Berlin und holt offene Lücken nach. Eine GitHub Action startet ihn um 06:00 Europe/Berlin und veröffentlicht `site/` nur bei Erfolg auf GitHub Pages.

Tage ohne vollständige Quellabdeckung erscheinen im Diagramm als Lücke, nicht als Anzahl 0. Tests: `pytest -m "not finbert"`. Der echte Modelltest: `pytest -m finbert`.
