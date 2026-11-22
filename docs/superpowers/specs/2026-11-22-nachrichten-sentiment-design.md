# Nachrichten-Sentiment für Aktien — Design

Datum: 2026-11-22  
Projekt: Nachrichten-Sentiment (eigenständiges Werkzeug, nicht Teil der App SE Aktien)  
Erstes Beispiel: Nvidia (NVDA)  
Status: Mit dem Auftraggeber abgestimmte Entscheidungen; festgehaltene Annahmen sind als solche gekennzeichnet.

## 1. Zweck und Erfolgskriterien

Das Werkzeug grenzt Kauf- und Verkaufsgelegenheiten von Aktien ein, indem es die Nachrichtenlage zu einer Aktiengesellschaft sichtbar macht. Es ersetzt keine Kursanalyse und erzeugt keine Handelssignale.

Erfolg ist erreicht, wenn für Nvidia gilt:

- Die Anzahl der Nachrichten zur Gesellschaft liegt taggenau vor, vom ersten Kalendertag mit GDELT-2.0-Daten in der Zeitzone Europe/Berlin (**19. Februar 2015**) bis zum jeweils letzten vollständig verarbeiteten Kalendertag. Die zugrunde liegende Quelle beginnt mit der Datei vom 18. Februar 2015, 23:00 UTC. Wo einzelne 15-Minuten-Dateien fehlen, bleibt die Lücke sichtbar (Abschnitt 9), statt als Null durchzugehen.
- Jede Nachricht mit verfügbarem Titel trägt einen Stimmungswert im Intervall \([-1, +1]\): \(0\) ist neutral, \(+1\) maximal positiv, \(-1\) maximal negativ.
- Eine statische Webseite zeigt die Entwicklung interaktiv (positive und negative Anzahl als divergierende Balken, Stimmung als Linie) und listet nach Klick auf einen Tag die Schlagzeilen mit Wert.
- Der einmalige Erstlauf ist nach Unterbrechung fortsetzbar. Danach ergänzt ein täglicher Lauf den Vortag, ohne laufende Kosten für Nachrichtenquellen oder das Stimmungsmodell.

## 2. Umfang

### 2.1 Im Umfang

- Eigenständiges Werkzeug mit Python-Datensammler, einmaligem Erstlauf, täglicher Aktualisierung per GitHub Action und statischer Webseite auf GitHub Pages.
- Nur kostenlose Quellen; Zeitraum ab dem Start von GDELT 2.0 (siehe Abschnitt 3).
- Lokale Stimmungsbewertung mit FinBERT auf Nachrichtentiteln.
- Deduplizierung, Tagesaggregation, Fehlerbehandlung und testgetriebene Umsetzung, wie in den folgenden Abschnitten festgelegt.
- Optik der Webseite im Farben- und Erscheinungsbild von SE Aktien.
- Erweiterbarkeit auf weitere Aktien nur als vorbereitete Struktur (Konfiguration aus Ticker und Suchbegriffen), ohne weitere Aktien im Lieferumfang.

### 2.2 Nicht im Umfang (YAGNI)

- Weitere Aktien außer Nvidia im ersten Lieferumfang.
- Kursdaten, Chartvergleiche mit dem Aktienkurs oder Korrelationen.
- Automatische Kauf- oder Verkaufssignale, Schwellen oder Alerts.
- Bewertung durch ein großes KI-Sprachmodell (als spätere Ausbaustufe vorgemerkt, siehe Abschnitt 12).
- Der übersetzte GDELT-2.0-Strom (`masterfilelist-translation.txt`), weil FinBERT auf englische Finanztexte ausgerichtet ist.
- Nutzung des GDELT-eigenen Tonwerts (`V1.5TONE` / GCAM) — die Stimmungsskala dieses Werkzeugs kommt ausschließlich von FinBERT.
- Eigener Server, Datenbank oder laufende Cloud-Kosten über das kostenlose GitHub-Angebot hinaus.

## 3. Datenquelle: GDELT 2.0 Global Knowledge Graph

### 3.1 Welche Datei geliefert wird

Verwendet wird der **GDELT 2.0 Global Knowledge Graph (GKG 2.1)**, nicht die Event-Dateien (`export.CSV.zip`) und nicht die Mentions-Dateien (`mentions.CSV.zip`). Events und Mentions enthalten eine Quell-URL, aber keinen Artikeltitel und datieren Events zudem teilweise auf den Ereigniszeitpunkt zurück, nicht auf das Erscheinungsdatum des Artikels.

Maßgebliche Dateien:

- 15-Minuten-Datei: `https://data.gdeltproject.org/gdeltv2/YYYYMMDDHHMMSS.gkg.csv.zip`  
  Die Manifeste listen oft `http://`; der Download erfolgt per HTTPS.
- Gesamtliste: `https://data.gdeltproject.org/gdeltv2/masterfilelist.txt`
- Zeiger auf den aktuellen Satz: `https://data.gdeltproject.org/gdeltv2/lastupdate.txt`

Die erste GKG-2.0-Datei ist `20150218230000.gkg.csv.zip` (18. Februar 2015, 23:00 UTC, in Europe/Berlin bereits 19. Februar 2015, 00:00). Danach erscheint alle 15 Minuten eine Datei. An einem vollen UTC-Tag sind das 96 Dateien; die für einen Berlin-Kalendertag erwartete Menge sind alle 15-Minuten-Zeitstempel (UTC), die in diesen Berlin-Tag fallen — an den beiden europäischen Sommerzeit-Übergängen also 92 bzw. 100 Dateien, nicht pauschal 96. Die Dateien sind trotz der Endung `.csv` tabgetrennt, ein Datensatz pro Zeile, ein Dokument pro Zeile.

Aus einem GKG-Datensatz werden verwendet (Bezeichnungen laut Codebook; in der Datei selbst stehen die Präfixe `V1` / `V2` / `V2.1` nicht unbedingt in der Kopfzeile):

| Bedarf | Feld |
| --- | --- |
| Eindeutige Satz-ID | `GKGRECORDID` |
| Zeitpunkt der 15-Minuten-Datei | `V2.1DATE` bzw. der Zeitstempel im Dateinamen (`YYYYMMDDHHMMSS`, UTC) |
| URL | `DocumentIdentifier`, nur wenn `V2SOURCECOLLECTIONIDENTIFIER = 1` (WEB) |
| Quelle / Domain | `V2SOURCECOMMONNAME` |
| Organisationen | `V1ORGANIZATIONS` und `V2ENHANCEDORGANIZATIONS` |
| Titel | Feld `Extras` (letzte Spalte), Block `<PAGE_TITLE>…</PAGE_TITLE>` |

Nur Web-Dokumente (Collection Identifier 1) gehen in den Bestand ein, weil nur sie eine aufrufbare Artikel-URL haben.

### 3.2 Titel: was GDELT zuverlässig liefert und was nicht

GDELT schreibt den Seitentitel erst seit dem **22. September 2019, nach 12:00 ostamerikanischer Ortszeit**, in das Feld `Extras` (`<PAGE_TITLE>`, nicht-ASCII-Zeichen als HTML-Entities). Das ist eine dokumentierte Erweiterung des GKG 2.0, nicht rückwirkend für den Bestand ab Februar 2015.

Arbeitsregel: Ist `<PAGE_TITLE>` im Satz vorhanden, wird dieser Titel nach dem Entschlüsseln der HTML-Entities verwendet. Fehlt der Block, gilt der Titel als in GDELT nicht verfügbar — typischerweise für alle Dateien vor diesem Stichtag und für einzelne spätere Sätze ohne den Block.

**Festgelegte Annahme (Titel nachladen):** Für Sätze ohne `PAGE_TITLE` lädt der Sammler den Titel einmalig nach, indem er die Artikel-URL aufruft und `<title>` bzw. `og:title` liest. Das Nachladen gilt nur für bereits auf Nvidia gefilterte Artikel (Abschnitt 4.1), nicht für den gesamten GKG. Es gelten höfliche Pausen, eine Begrenzung der parallelen Anfragen und ein Zwischenspeicher für erfolgreiche und fehlgeschlagene Versuche, damit ein unterbrochener Erstlauf nichts wiederholt. Schlägt das Nachladen fehl (Seite verschwunden, Blockade, Zeitüberschreitung), bleibt der Artikel in der **Anzahl** enthalten, fließt aber **nicht** in die Durchschnittsstimmung ein (`sentiment = null`, Anzeige „Titel nicht verfügbar“). Ein fehlender Titel wird nicht als Stimmung `0` gewertet, weil das den Tagesmittelwert verfälschen würde.

Damit beginnt die Anzahlreihe am 19. Februar 2015 (Europe/Berlin). Die Stimmungsreihe kann vor September 2019 lückenhafter sein, weil viele ältere URLs nicht mehr erreichbar sind. Dieser Nachladeschritt kann den Erstlauf merklich verlängern; er ist wie der übrige Sammler fortsetzbar.

## 4. Filterung und Deduplizierung

### 4.1 Filter auf Nvidia

Ein GKG-Web-Dokument gehört zu Nvidia, wenn ohne Berücksichtigung der Groß- und Kleinschreibung mindestens eine der folgenden Bedingungen zutrifft. Der Filter läuft **vor** dem Titelnachladen und darf das Nachladen nicht voraussetzen:

- In `V1ORGANIZATIONS` oder `V2ENHANCEDORGANIZATIONS` kommt der Name NVIDIA vor (einschließlich Schreibweisen wie „Nvidia“, „nVidia“, „NVIDIA Corporation“).
- Die URL (`DocumentIdentifier`, normalisiert) enthält die Zeichenfolge `nvidia` oder das Tickersymbol `nvda` als eigenes Wort (Wortgrenze).
- Ein bereits in der GKG-Datei vorhandener Titel (`PAGE_TITLE`) enthält „Nvidia“, „nVidia“, „NVIDIA“ oder das Tickersymbol **NVDA** als eigenes Wort.

Ein nachgeladenes Titel-Feld dient der Anzeige und der FinBERT-Bewertung, nicht der Entdeckung weiterer Artikel. Ein bereits über Organisation oder URL aufgenommener Artikel bleibt im Bestand, auch wenn der nachgeladene Titel Nvidia nicht nennt.

Reine Erwähnungen von Grafikprozessoren ohne Namens- oder Tickerbezug in den oben genannten Feldern zählen nicht. Andere Gesellschaften sind nicht im Filter.

### 4.2 Gleiche Adressen (immer entfernen)

URLs werden normalisiert: Host in Kleinbuchstaben, kein abschließender Schrägstrich, keine typischen Tracking-Parameter (`utm_*`, `fbclid`, `gclid`). Dieselbe normalisierte URL wird **global** (über den gesamten Zeitraum, nicht nur am selben Tag) nur einmal behalten: es bleibt das zeitlich erste Vorkommen. Spätere Sätze mit derselben Adresse entfallen vollständig.

### 4.3 Nahezu gleiche Titel am selben Tag

Zusätzlich werden am selben Kalendertag (Europe/Berlin, siehe Abschnitt 6.1) nahezu gleiche Titel erkannt, nachdem der Titel normalisiert wurde: Unicode NFKC, Kleinbuchstaben, zusammengezogene Leerzeichen, typische Seiten-Suffixe nach ` | ` oder ` – ` entfernt.

Zwei Titel desselben Tages gelten als nahezu gleich, wenn die normalisierten Zeichenketten identisch sind **oder** ihre Ähnlichkeit nach `difflib.SequenceMatcher.ratio` mindestens **0,90** beträgt. Das zeitlich erste Vorkommen bleibt die Stammzeile; die weiteren werden als Nahduplikat markiert, aber nicht gelöscht. Artikel ohne Titel (`title_source = missing`) werden nicht als Nahduplikat behandelt und zählen in beiden Anzahlen einzeln.

Beide Anzahlen bleiben sichtbar, aber nicht als Balken:

- **Hauptwert** (`count_unique_url`): Anzahl nach Entfernen gleicher URLs. Er erscheint im Tooltip und im Kopf der Tagesliste, nicht als Balkenserie.
- **Zusatzwert** (`count_after_near_dup_collapse`): dieselbe Menge ohne Nahduplikate (jedes Nahduplikat-Cluster zählt als eins), ebenfalls im Tooltip und im Kopf der Tagesliste.

Die Balken im Hauptdiagramm zeigen nicht diese Gesamtzahlen, sondern die Anzahl positiver und negativer Nachrichten nach FinBERT-argmax (Abschnitt 8.1), bezogen auf die URL-eindeutigen Artikel.

In der Tagesliste erscheinen alle URL-eindeutigen Schlagzeilen; Nahduplikate werden an der Stammzeile gruppiert dargestellt.

## 5. Stimmungsbewertung

Modell: **ProsusAI/finbert**, lokal (Hugging Face), angewendet auf den entschlüsselten Titel. Es entstehen drei Wahrscheinlichkeiten \(P(\text{positiv})\), \(P(\text{neutral})\), \(P(\text{negativ})\). Der gespeicherte Wert ist

\[
\text{sentiment} = P(\text{positiv}) - P(\text{negativ})
\]

und liegt damit automatisch in \([-1, +1]\).

Zusätzlich wird die vom Modell bevorzugte Klasse (argmax über die drei Wahrscheinlichkeiten) gespeichert: `positive`, `neutral` oder `negative`.

- Der **Tagesmittelwert** ist das arithmetische Mittel der `sentiment`-Werte aller URL-eindeutigen Artikel dieses Tages, die einen Wert haben (einschließlich Nahduplikate). Artikel ohne Titel bzw. ohne Wert gehen nicht in den Mittelwert ein; fehlen an einem vollständig verarbeiteten Tag alle Werte, ist der Mittelwert `null` (Lücke in der Stimmungslinie, nicht `0`).
- Die **Anzahlen positiv, neutral und negativ** zählen URL-eindeutige Artikel nach der argmax-Klasse. Alle drei sind Pflichtfelder der Tageszeile. Im Diagramm werden nur positiv (Balken nach oben) und negativ (Balken nach unten) gezeichnet; die neutrale Anzahl und die Gesamtzahl erscheinen im Tooltip (Abschnitt 8.1). Artikel ohne Wert bilden eine gesonderte Zahl `count_without_sentiment` und erscheinen in der Tagesliste ohne numerischen Wert; ist sie größer als null, nennt der Tooltip sie zusätzlich. Es gilt `count_positive + count_neutral + count_negative + count_without_sentiment = count_unique_url`.

Ein großes KI-Sprachmodell ist nicht Bestandteil dieses Umfangs (Abschnitt 12).

## 6. Tageswerte und Speicherung

### 6.1 Tagesschnitt

Ein „Tag“ ist der **Kalendertag in der Zeitzone Europe/Berlin**, gebildet aus dem UTC-Zeitstempel der GDELT-15-Minuten-Datei (Dateiname / `V2.1DATE`). Der präzise Veröffentlichungszeitstempel `PAGE_PRECISEPUBTIMESTAMP` im Feld `Extras` wird nicht verwendet: er ist nur für einen Teil der Artikel vorhanden und würde die Reihe uneinheitlich machen.

### 6.2 Inhalt eines Artikeldatensatzes

Je behaltenem (URL-eindeutigem) Artikel:

- `gkg_record_id`, `url`, `url_normalized`, `source_domain`
- `title`, `title_source` (`gkg` | `fetched` | `missing`)
- `batch_utc` (Zeitstempel der 15-Minuten-Datei), `day_berlin` (`YYYY-MM-DD`)
- `sentiment` (Zahl oder `null`), `sentiment_label` (`positive` | `neutral` | `negative` | `null`)
- `p_positive`, `p_neutral`, `p_negative` (oder `null`)
- `is_near_duplicate` (bool), `near_duplicate_of` (ID der Stammzeile oder `null`)

### 6.3 Inhalt einer Tageszeile

- `date` (Europe/Berlin)
- `count_unique_url` (Gesamtzahl nach URL-Deduplizierung; Tooltip und Tagesliste, nicht als Balken)
- `count_after_near_dup_collapse` (Zusatzwert; Tooltip und Tagesliste)
- `count_positive`, `count_neutral`, `count_negative` (argmax-Anzahlen der URL-eindeutigen Artikel; positiv und negativ sind die Balkenserien, neutral nur im Tooltip)
- `count_without_sentiment`
- `sentiment_mean` (Zahl oder `null`; Stimmungslinie)
- `coverage` (`complete` | `gap`): `complete`, wenn alle für diesen Berlin-Tag erwarteten 15-Minuten-Dateien erfolgreich verarbeitet wurden (auch wenn die Nvidia-Anzahl 0 ist); `gap`, wenn mindestens eine Datei fehlt oder unlesbar blieb.

Ein erfolgreich verarbeiteter Tag ohne Nvidia-Nachricht ist eine echte Null: keine Ausschläge über oder unter der Nulllinie (Balkenhöhe 0), die Nulllinie bleibt stehen, der Tooltip nennt 0 Nachrichten. Ein Tag nur mit neutralen Meldungen sieht in den Balken ebenso ohne Ausschlag aus, unterscheidet sich aber im Tooltip (Gesamtzahl und neutrale Anzahl größer als 0) und gegebenenfalls in der Stimmungslinie. Ein Tag mit `coverage = gap` wird in beiden Diagrammen als **Lücke** gezeigt, nicht als echte Null, damit fehlende oder unvollständige Quelle nicht wie ein ruhiger oder vollständiger Tag aussieht. Bereits gesammelte Artikel dieses Tages bleiben gespeichert; sobald die fehlenden Dateien nachgeholt sind, wird die Tageszeile neu berechnet und erst dann als `complete` angezeigt. Die Tagesliste eines solchen Tages darf geöffnet werden, trägt aber den Hinweis „unvollständig“.

### 6.4 Dateien

- Einzelnachrichten (Bestand des Sammlers): eine Datei je Monat, `data/articles/nvda/YYYY-MM.jsonl`.
- Tageswerte für die Webseite: eine kleine Datei `site/data/nvda-daily.json`.
- Schlagzeilen für den Tagesklick: Monatsdateien `site/data/nvda/YYYY-MM.json`, die die Webseite erst beim Öffnen eines Tages nachlädt.
- Fortschritt des Sammlers (Quelle der Wahrheit): `data/state/progress.json` mit dem Zeitstempel der letzten erfolgreich verarbeiteten 15-Minuten-Datei, der Liste offener Lücken und dem Zwischenspeicher fehlgeschlagener Titel-Nachladeversuche.
- Menschlich lesbares Protokoll derselben Lücken und Nachlade-Fehler: `data/state/gaps.log` (nur Anhang, kein zweiter Führungsstand).

Rohe GDELT-Dateien werden nach dem Filtern nicht aufbewahrt und nicht ins Git-Repository gelegt. In das Repository gehören `data/` (Artikel, Fortschritt) und `site/` (Webseite und die von ihr geladenen JSON-Dateien), damit ein fortgesetzter Lauf und die GitHub Action denselben Stand vorfinden. GitHub Pages veröffentlicht nur `site/`.

## 7. Architektur und Datenfluss

Gewählt ist Weg 1: Datensammler mit täglicher Aktualisierung und statischer Webseite.

```
GDELT GKG 2.0 (15-Minuten-Dateien)
    → nur WEB-Dokumente, Filter Nvidia (Organisation, URL, vorhandener GKG-Titel)
    → gleiche URLs entfernen (global, erstes Vorkommen bleibt)
    → Titel aus PAGE_TITLE oder einmaligem Nachladen
    → FinBERT auf verfügbare Titel
    → Nahduplikate am selben Berlin-Tag markieren
    → Monatsdateien der Einzelnachrichten schreiben
    → Tageswerte berechnen
    → statische Webseite veröffentlichen
```

Bestandteile:

1. **Python-Datensammler** im Repository. Er kennt zwei Betriebsarten: Erstlauf (vom ersten GKG-Satz bis zur Gegenwart) und Ergänzung (Vortag plus nachzuziehende Lücken).
2. **Fortsetzbarer Erstlauf.** Der Sammler schreibt nach jeder erfolgreich verarbeiteten 15-Minuten-Datei den Fortschritt. Wird der Lauf unterbrochen, setzt der nächste Start genau dort wieder an. Der Erstlauf dauert voraussichtlich mehrere Stunden, vor allem wegen der Dateimenge und des Titelnachladens vor September 2019. Weil ein einzelner GitHub-Action-Lauf zeitlich begrenzt ist, wird der Erstlauf **lokal** ausgeführt oder in mehreren fortsetzbaren Action-Läufen; der Stand wird jeweils ins Repository geschrieben. Der tägliche Lauf bleibt in einer Action und muss in deren Zeitbudget passen.
3. **Täglicher Lauf als GitHub Action**, um 06:00 Europe/Berlin und zusätzlich manuell auslösbar (`workflow_dispatch`). Er verarbeitet alle 15-Minuten-Dateien, die zum vorherigen Berlin-Kalendertag gehören, und zieht bekannte Lücken nach. Anschließend werden Tagesdateien und Webseite neu erzeugt.
4. **Statische Webseite auf GitHub Pages** aus dem Ordner `site/`. Die Rechenarbeit liegt vollständig im Sammler; die Seite lädt nur die vorbereiteten JSON-Dateien.

Die Konfiguration der Gesellschaft (Ticker `NVDA`, Anzeigename, Suchbegriffe) liegt in einer eigenen Datei, damit später weitere Aktien ergänzt werden können, ohne den Datenfluss zu ändern. Im ersten Lieferumfang ist nur Nvidia enthalten.

## 8. Webseite

### 8.1 Darstellung

- Oben: Hauptdiagramm als Balken um eine Nulllinie. Die Nulllinie steht für den neutralen Bereich: von ihr aus gehen **grüne Balken** (`--up`, `#26a69a`) nach oben mit der Anzahl positiver Nachrichten des Tages und **rote Balken** (`--down`, `#ef5350`) nach unten mit der Anzahl negativer Nachrichten, jeweils nach FinBERT-argmax (`count_positive` bzw. `count_negative`). Beide Richtungen teilen sich eine gemeinsame Anzahl-Skala. Die neutrale Anzahl und die Gesamtzahl werden **nicht** als Balken gezeichnet.
- Beim Überfahren eines Tages erscheint ein Tooltip, der Gesamtzahl, Klassen und Stimmung nennt, zum Beispiel: „120 Nachrichten: 45 positiv, 50 neutral, 25 negativ, Stimmung +0,18“. Ist `count_without_sentiment` größer als 0, wird das zusätzlich genannt (etwa „5 ohne Wert“). Fehlt der Tagesmittelwert, entfällt die Angabe „Stimmung …“ oder sie erscheint als „Stimmung —“. Der Zusatzwert nach Nahduplikat-Berechnung erscheint in diesem Tooltip und im Kopf der Tagesliste.
- Darunter: Stimmung als Linie (`sentiment_mean`) im Intervall \([-1, +1]\), mit Nulllinie. Abschnitte über 0 werden grün (`--up`) eingefärbt, Abschnitte unter 0 rot (`--down`). Tage ohne Mittelwert unterbrechen die Linie.
- Balken und Linie können voneinander abweichen, weil sie Unterschiedliches messen: Die Balken zählen Kategorien nach argmax (welche Klasse die größte Wahrscheinlichkeit hat), die Linie den abgestuften Tagesmittelwert \(P(\text{positiv}) - P(\text{negativ})\). Viele schwach positive Meldungen und wenige stark negative können deshalb mehr grüne als rote Balken zeigen, während die Linie unter 0 liegt — oder umgekehrt. Neutrale Meldungen erscheinen nicht in den Balken, fließen aber mit Werten nahe 0 in die Linie ein, sofern ein Stimmungswert vorliegt.
- Zoom und Zeitraumwahl, in der Bedienung an SE Aktien angelehnt. Zeitraum-Chips: 1 Monat, 3 Monate, 1 Jahr, 5 Jahre, Maximum.
- Klick auf einen Tag öffnet die Liste der URL-eindeutigen Schlagzeilen dieses Tages mit Stimmungswert (oder Hinweis „Titel nicht verfügbar“). Nahduplikate sind an der Stammzeile gruppiert. Jede Zeile verlinkt auf die Artikel-URL.

Tage mit `coverage = gap` erscheinen in beiden Diagrammen als Lücke, nicht als Balken der Höhe 0.

### 8.2 Farben und Erscheinungsbild (SE Aktien)

Die Vorgabe ist das öffentliche Erscheinungsbild von SE Aktien (Repository `ExplorationSE/aktien-app`, Live-Seite https://explorationse.github.io/aktien-app/). Die konkreten CSS-Variablen aus `site/index.html` dieses Standes werden übernommen:

| Rolle | Variable | Wert |
| --- | --- | --- |
| Seitenhintergrund, `theme-color` | `--bg` | `#0d1117` |
| Karten, Eingabeflächen | `--card` | `#161b22` |
| Linien, Rahmen | `--line` | `#30363d` |
| Fließtext | `--txt` | `#e6edf3` |
| Nebentext | `--mut` | `#8b949e` |
| Positiv / „oben“ | `--up` | `#26a69a` |
| Negativ / „unten“ | `--down` | `#ef5350` |
| Akzent, aktive Elemente | `--acc` | `#58a6ff` |
| Aktiver Zeitraum-Chip | — | Hintergrund `#1f2937`, Text `--txt` |
| Aktiver Schalter, Schrift | — | Hintergrund `--acc`, Text `#0d1117` |
| Fußzeile | — | `#6e7681` |

Schrift: `system-ui, -apple-system, Segoe UI, Roboto, sans-serif`. Karten und Suchfelder mit 12px Rundung, Schalter 8px, Zeitraum-Chips als Kapseln. Die eigene Wortmarken-Schrift von SE Aktien wird nicht übernommen; dieses Werkzeug ist eigenständig und trägt den Arbeitstitel **Nachrichten-Sentiment**, Untertitel „Nvidia (NVDA)“.

Diagrammfarben: positive Balken und der Teil der Stimmungslinie über 0 in `--up` (`#26a69a`), negative Balken und der Teil der Linie unter 0 in `--down` (`#ef5350`), Nulllinien und Raster in `--line`. `--acc` bleibt der Akzent für Bedienungselemente, nicht für die Balkenserie.

Als Chart-Bibliothek wird **TradingView Lightweight Charts** verwendet, wie in SE Aktien (`lwc.js`, lokal eingebunden). Zoom, Zeitraumwahl und zwei übereinanderliegende Bereiche (divergierende Positiv/Negativ-Balken um die Nulllinie oben, Stimmungslinie unten) sind damit vorgesehen. Für den Klick auf einen Tag und den Tooltip darf eine dünne eigene Interaktionsschicht über dem Chart liegen; ein Wechsel der Bibliothek ist nur zulässig, wenn Lightweight Charts diese Darstellung nachweislich nicht tragen kann.

## 9. Fehlerbehandlung und Betrieb

- Fehlende oder abgebrochene GDELT-Downloads werden mehrfach erneut versucht (mit Abstand). Bleibt der Fehler, wird die Lücke in `progress.json` und im Protokoll `gaps.log` vermerkt. Der nächste Lauf (täglich oder manuell) holt offene Lücken automatisch nach, sobald die Datei erreichbar ist.
- Der Sammler merkt sich den letzten erfolgreich verarbeiteten 15-Minuten-Satz. Ein unterbrochener Erstlauf beginnt nicht von vorn.
- Schlägt der tägliche Lauf fehl, wird **keine** neue GitHub-Pages-Version veröffentlicht. Die bisherige Seite bleibt unverändert online. GitHub sendet die übliche Fehlerbenachrichtigung per E-Mail an den Repository-Inhaber; dafür müssen die E-Mail-Benachrichtigungen für Actions beim Konto ExplorationSE eingeschaltet sein.
- Fehlgeschlagenes Titelnachladen wird je URL in `progress.json` festgehalten und nicht endlos wiederholt; eine spätere, bewusst ausgelöste Wiederholung bleibt möglich.
- Die Webseite darf bei `coverage = gap` den Tag nicht als echte Null darstellen (keine Balken der Höhe 0 und kein Tooltip „0 Nachrichten“ so, als wäre der Tag vollständig leer).

## 10. Tests

Die Umsetzung ist testgetrieben: Für jeden Baustein entsteht zuerst ein fehlschlagender Test, danach der Code, bis der Test besteht.

Unit-Tests mit kleinen, festen Beispieldaten, ohne Netz und ohne das volle FinBERT-Modell (Modellausgabe wird nachgebildet, wo der umgebende Code geprüft wird):

- Filter auf Nvidia (Treffer und Gegenbeispiele, einschließlich Wortgrenze bei NVDA, URL-Treffer und Unabhängigkeit vom nachgeladenen Titel).
- URL-Normalisierung und globales Entfernen gleicher Adressen (erstes Vorkommen bleibt).
- Erkennung nahezu gleicher Titel am selben Tag, getrennte Zählung beider Anzahlen und das Nicht-Gruppieren von Artikeln ohne Titel.
- Umrechnung FinBERT-Wahrscheinlichkeiten in den Wert \(P(\text{positiv}) - P(\text{negativ})\) einschließlich der Intervallgrenzen und der argmax-Klasse.
- Bildung der Tageswerte, einschließlich der Pflichtfelder `count_positive`, `count_neutral` und `count_negative`, der Summe `count_positive + count_neutral + count_negative + count_without_sentiment = count_unique_url`, echter Null bei vollständiger Abdeckung (Balkenhöhe 0, nicht verwechseln mit einem Tag nur aus Neutralen), Lücke bei `coverage = gap` (auch wenn bereits Teilartikel vorliegen) sowie Mittelwert ohne Artikel mit `sentiment = null`.

Plausibilitätstest am echten FinBERT-Modell mit einer Handvoll fest hinterlegter, eindeutiger Schlagzeilen: klar positive Titel (etwa eine Prognoseanhebung) müssen `sentiment > 0` und die Klasse `positive` erhalten; klar negative (etwa ein deutlicher Rückgang oder eine Untersuchung) müssen `sentiment < 0` und die Klasse `negative` erhalten.

Bevor der Erstlauf über den vollen Zeitraum startet, läuft ein **Probelauf über eine Kalenderwoche nach dem 22. September 2019** (sieben aufeinanderfolgende Berlin-Tage, in denen GKG-Titel bereits enthalten sind). Geprüft wird: Downloads, Filter, Deduplizierung, Bewertung, Tagesdateien, Anzeige der Webseite, Fortsetzen nach künstlicher Unterbrechung und Darstellung einer künstlichen Lücke. Das Titelnachladen wird zusätzlich an einer kleinen, festen Menge älterer URLs geprüft, nicht als zweite volle Woche.

## 11. Festgelegte Annahmen

Diese Punkte waren in der Abstimmung noch nicht Satz für Satz festgelegt und werden hiermit entschieden, damit die Umsetzung eindeutig ist:

1. Titel ohne `PAGE_TITLE` (insbesondere vor dem 22. September 2019) werden einmalig von der Artikel-URL nachgeladen; ohne Titel keine Stimmung, aber Zählung bleibt (Abschnitt 3.2). Das Nachladen dient nicht dazu, weitere Artikel zu entdecken (Abschnitt 4.1).
2. Nur der englische GDELT-2.0-Strom, nicht der Übersetzungsstrom.
3. Tagesschnitt ist der Kalendertag Europe/Berlin auf Basis des UTC-Dateinamens der GDELT-Datei. Der erste dargestellte Tag ist der 19. Februar 2015.
4. Anzahl positiv, neutral und negativ folgt der FinBERT-Klasse (argmax), nicht einem Schwellenwert auf dem kontinuierlichen Wert. Die Balken verwenden nur positiv und negativ; die Linie verwendet den abgestuften Tagesmittelwert.
5. Ähnlichkeitsschwelle für Nahduplikate ist 0,90 auf normalisierten Titeln desselben Berlin-Tages; Artikel ohne Titel werden nicht gruppiert.
6. Alle Diagramm- und Tooltip-Anzahlen (gesamt, positiv, neutral, negativ) beziehen sich auf URL-eindeutige Artikel. Die Gesamtzahl und der Zusatzwert nach Nahduplikat-Berechnung erscheinen im Tooltip und im Kopf der Tagesliste, nicht als Balken.
7. Arbeitstitel der Seite: „Nachrichten-Sentiment“.
8. Der Erstlauf läuft lokal oder in mehreren fortsetzbaren Action-Läufen; nur der tägliche Lauf ist fest an eine GitHub Action um 06:00 Europe/Berlin gebunden.

## 12. Spätere Ausbaustufen (vorgemerkt, nicht bauen)

- Bewertung ausgewählter Nachrichten oder Stichproben durch ein großes KI-Sprachmodell zur Kontrolle und eventuellen Nachschärfung von FinBERT.
- Weitere Aktien über die vorbereitete Konfiguration.
- Optional der übersetzte GDELT-Strom, sofern es ein geeignetes nicht-englisches Finanzmodell gibt.
- Keine dieser Stufen ist Voraussetzung für den ersten Lieferumfang.
