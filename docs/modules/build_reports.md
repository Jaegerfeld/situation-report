# build_reports

Liest die von `transform_data` erzeugten XLSX-Dateien und berechnet Flow-Metriken als interaktive Diagramme. Unterstützt SAFe- und Global-Terminologie, optionale Filter und PDF-Export.

## Start

### GUI

```bash
python -m build_reports
```

Öffnet das build_reports-Fenster mit Datei-Auswahl, Filterfeldern, Metrik-Checkboxen und Terminologie-Umschalter. Diagramme werden im Standard-Browser als interaktives HTML angezeigt. PDF-Export öffnet einen Speicher-Dialog.

Alternativ: Doppelklick auf `build_reports_gui.pyw` im Projektverzeichnis — öffnet die GUI ohne Konsolenfenster.

### Kommandozeile

```bash
python -m build_reports.cli <IssueTimes.xlsx> [Optionen]
```

**Argumente**

| Argument | Beschreibung |
|----------|-------------|
| `IssueTimes.xlsx` | Ausgabedatei von `transform_data` (Pflichtfeld) |
| `--cfd CFD.xlsx` | CFD-Ausgabedatei (für CFD-Metrik erforderlich) |
| `--metrics ID …` | Metriken auswählen (Standard: alle) |
| `--from-date YYYY-MM-DD` | Nur Issues einschließen, die ab diesem Datum geschlossen wurden |
| `--to-date YYYY-MM-DD` | Nur Issues einschließen, die bis zu diesem Datum geschlossen wurden |
| `--projects KEY …` | Auf diese Projektschlüssel einschränken |
| `--issuetypes TYPE …` | Auf diese Issuetypen einschränken |
| `--terminology` | Terminologie: `SAFe` (Standard) oder `Global` |
| `--pdf FILE` | Alle Diagramme als PDF speichern |
| `--browser` | Diagramme im Standard-Browser öffnen |

**Beispiele**

```bash
# Alle Metriken, PDF speichern
python -m build_reports.cli data/ART_A_IssueTimes.xlsx --cfd data/ART_A_CFD.xlsx --pdf report.pdf

# Nur Flow Time, Datumsfilter, Browser-Anzeige
python -m build_reports.cli data/ART_A_IssueTimes.xlsx \
    --metrics flow_time \
    --from-date 2025-01-01 --to-date 2025-12-31 \
    --browser

# Mehrere Metriken, Global-Terminologie
python -m build_reports.cli data/ART_A_IssueTimes.xlsx --cfd data/ART_A_CFD.xlsx \
    --metrics flow_time flow_velocity cfd \
    --terminology Global \
    --pdf quarterly_report.pdf
```

### Übersicht

| Befehl | Ergebnis |
|--------|----------|
| `python -m build_reports` | GUI |
| `python -m build_reports.cli <xlsx> --browser` | CLI, Browser-Anzeige |
| `python -m build_reports.cli <xlsx> --pdf out.pdf` | CLI, PDF-Export |
| `python -m build_reports.cli --help` | CLI-Hilfe |
| Doppelklick auf `build_reports_gui.pyw` | GUI ohne Konsolenfenster |

## Metriken

### Flow Time / Cycle Time

**Metrik-ID:** `flow_time`

Berechnet die Durchlaufzeit (in Tagen) von der ersten Aktivität (`First Date`) bis zum Abschluss (`Closed Date`) für alle abgeschlossenen Issues. Issues ohne beide Daten oder mit einer Durchlaufzeit von 0 Tagen werden ausgeschlossen.

**Diagramme:**

- **Boxplot** — Verteilung der Durchlaufzeiten mit Statistik-Header (Median, Mittelwert, Min, Max, 90. Perzentil, Variationskoeffizient)
- **Scatterplot** — Durchlaufzeit je Abschlussdatum mit Trendlinie und Referenzlinien (Median, 85. und 95. Perzentil)

| SAFe | Global |
|------|--------|
| Flow Time | Cycle Time |

---

### Flow Velocity / Throughput

**Metrik-ID:** `flow_velocity`

Zählt abgeschlossene Issues (mit `Closed Date`) pro Zeitraum.

**Diagramme:**

- **Tagesfrequenz** — Histogramm: wie viele Issues werden üblicherweise an einem Tag abgeschlossen
- **Wochenverlauf** — Linienchart der wöchentlichen Abschlüsse (Format `YYYY.WW`)
- **PI-Verlauf** — Balkendiagramm der Abschlüsse pro PI (ISO-Kalenderwoche) mit Durchschnittslinie

| SAFe | Global |
|------|--------|
| Flow Velocity | Throughput |

---

### Flow Load / WIP

**Metrik-ID:** `flow_load`

Analysiert **offene** Issues (ohne `Closed Date`) nach ihrer aktuellen Stage und ihrem Alter (Tage seit `First Date` oder Erstellungsdatum).

**Diagramm:** Gruppierter Boxplot mit Einzelpunkten, unterteilt nach aktueller Stage. Referenzlinien aus den abgeschlossenen Issues (Mittelwert, Median, 85. und 95. Perzentil der Durchlaufzeit) geben einen Kontext für das Alter der offenen Issues.

| SAFe | Global |
|------|--------|
| Flow Load | WIP |

---

### Cumulative Flow Diagram

**Metrik-ID:** `cfd`

Liest die tagesgenauen Stage-Zählungen aus `CFD.xlsx`. Zeigt den Zustand des Systems über Zeit.

**Diagramm:** Gestapeltes Flächendiagramm (erste Stage oben) mit zwei Trendlinien (Zufluss/Abfluss) und In/Out-Ratio im Titel.

| SAFe | Global |
|------|--------|
| Cumulative Flow Diagram | Cumulative Flow Diagram |

---

### Flow Distribution

**Metrik-ID:** `flow_distribution`

Zeigt die Zusammensetzung des Issue-Bestands nach Issuetyp und aktuellem Status.

**Diagramm:** Zwei Kreisdiagramme (Donut) nebeneinander — links nach Issuetyp, rechts nach Status.

| SAFe | Global |
|------|--------|
| Flow Distribution | Flow Distribution |

---

## Filter

Filter können in der GUI über die Eingabefelder gesetzt oder per CLI als Argumente übergeben werden.

| Filter | GUI | CLI |
|--------|-----|-----|
| Von-Datum | Feld „Von (YYYY-MM-DD)" | `--from-date` |
| Bis-Datum | Feld „Bis (YYYY-MM-DD)" | `--to-date` |
| Projekte | Feld „Projekte" (kommagetrennt) | `--projects` |
| Issuetypen | Feld „Issuetypen" (kommagetrennt) | `--issuetypes` |

- Das Datumsfilter bezieht sich auf das `Closed Date` der Issues.
- Issues ohne `Closed Date` werden bei gesetztem Datumsfilter ausgeschlossen.
- CFD-Daten werden nur nach Datum gefiltert (keine Projekt- oder Issuetyp-Dimension).

## Terminologie

Alle Metrik-Bezeichnungen können zwischen SAFe und Global umgeschaltet werden. Die Umschaltung betrifft Diagrammtitel, Achsenbeschriftungen und Labels.

| Metrik-ID | SAFe | Global |
|-----------|------|--------|
| `flow_time` | Flow Time | Cycle Time |
| `flow_velocity` | Flow Velocity | Throughput |
| `flow_load` | Flow Load | WIP |
| `cfd` | Cumulative Flow Diagram | Cumulative Flow Diagram |
| `flow_distribution` | Flow Distribution | Flow Distribution |

## Export

### Browser-Anzeige

Alle Diagramme werden als kombiniertes HTML-Dokument in einer temporären Datei erzeugt und im Standard-Browser geöffnet. Die Diagramme sind vollständig interaktiv (Zoom, Pan, Hover-Tooltips, Legende ein-/ausblenden).

### PDF-Export

```bash
python -m build_reports.cli <xlsx> --pdf report.pdf
```

- Einzelne Diagramme werden direkt als PDF erzeugt.
- Mehrere Diagramme werden über `pypdf` zu einem mehrseitigen PDF zusammengefügt.
- Der Export nutzt `kaleido` zur Rasterisierung (einmalig `choreo_get_chrome` ausführen, falls kaleido den Chrome-Binary noch nicht gefunden hat).

## Plugin-System

Neue Metriken können als eigenständiges Modul in `build_reports/metrics/` hinzugefügt werden:

```python
# build_reports/metrics/my_metric.py
from build_reports.metrics.base import MetricPlugin, MetricResult, register
import plotly.graph_objects as go

class MyMetric(MetricPlugin):
    metric_id = "my_metric"

    def compute(self, data, terminology):
        # Berechnung ...
        return MetricResult(metric_id=self.metric_id, stats={}, chart_data={})

    def render(self, result, terminology):
        fig = go.Figure(...)
        return [fig]

register(MyMetric())
```

Anschließend den Import in `build_reports/metrics/__init__.py` ergänzen — die neue Metrik erscheint automatisch in GUI und CLI.

## Tests

```bash
python -m pytest tests/build_reports/
```

| Testtyp | Verzeichnis | Inhalt |
|---------|-------------|--------|
| Unit | `tests/build_reports/unit/` | Isolierte Tests für jedes Modul mit synthetischen Fixtures; kaleido wird gemockt |
| Acceptance | `tests/build_reports/acceptance/` | Tests gegen den realen ART_A-Datensatz; prüfen fachliche Korrektheit der Metriken, des Exports und der GUI-Eingabeverarbeitung |
