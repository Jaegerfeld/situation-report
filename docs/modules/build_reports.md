# build_reports

Liest die von `transform_data` erzeugten XLSX-Dateien und berechnet Flow-Metriken als interaktive Diagramme. Unterstützt SAFe- und Global-Terminologie, optionale Filter, PDF-Export und eine vollständig lokalisierte GUI (Deutsch/Englisch).

!!! tip "Benutzerhandbuch (PDF)"
    Für Nicht-Techniker steht ein ausführliches Benutzerhandbuch bereit:
    **[build_reports_Benutzerhandbuch.pdf](../build_reports_Benutzerhandbuch.pdf)**
    — enthält Setup, GUI-Bedienung, Metriken-Erklärungen, FAQ und Glossar.

## Start

### GUI

```bash
python -m build_reports
```

Öffnet das build_reports-Fenster. Alternativ: Doppelklick auf `build_reports_gui.pyw` im Projektverzeichnis — öffnet die GUI ohne Konsolenfenster.

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
| `--exclude-status STATUS …` | Issues mit diesen Jira-Status vollständig ausschließen |
| `--exclude-resolution RES …` | Issues mit diesen Resolutions vollständig ausschließen |
| `--exclude-zero-day` | Zero-Day-Issues ausschließen (CT < Schwellwert) |
| `--zero-day-threshold MINUTEN` | Schwellwert in Minuten für Zero-Day-Erkennung (Standard: 5) |
| `--terminology` | Terminologie: `SAFe` (Standard) oder `Global` |
| `--ct-method` | CT-Berechnungsmethode: `A` (Kalendertage, Standard) oder `B` (Stage-Minuten) |
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

# Mehrere Metriken, Global-Terminologie, CT-Methode B
python -m build_reports.cli data/ART_A_IssueTimes.xlsx --cfd data/ART_A_CFD.xlsx \
    --metrics flow_time flow_velocity cfd \
    --terminology Global \
    --ct-method B \
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

## GUI

### Optionsmenü

Das Menüband enthält zwei Menüs:

**Optionen**

- **Sprache** — Umschalten zwischen Deutsch und Englisch; alle Labels, Tooltips und Menüpunkte werden sofort aktualisiert.
- **Terminologie** — Umschalten zwischen SAFe und Global; betrifft Diagrammtitel, Achsenbeschriftungen und Metrik-Checkboxen.

**Templates**

- **Speichern…** — Speichert die gesamte aktuelle Konfiguration (Dateipfade, Datumsfilter, Projekte, Issuetypen, Terminologie, CT-Methode, Metrikauswahl, Sprache) als JSON-Datei.
- **Laden…** — Lädt eine gespeicherte Konfiguration und befüllt alle Felder. Pfade, die nicht mehr existieren, werden im Log angezeigt.

### Dateien

- **IssueTimes** — Pflichtfeld. Nach der Auswahl werden Projekte und Issuetypen automatisch aus der Datei geladen (Hintergrund-Thread). Falls eine CFD-Datei bereits gesetzt ist, wird gleichzeitig ein Stage-Konsistenz-Check durchgeführt.
- **CFD (optional)** — Wird nur für die CFD-Metrik benötigt. Beim Setzen wird der Stage-Konsistenz-Check ausgeführt.

### Filter

| Feld | Beschreibung |
|------|-------------|
| Von / Bis | Datumsfilter auf `Closed Date`. Standard: letzte 365 Tage. Direkteingabe (YYYY-MM-DD) oder Kalender-Picker (📅-Button). |
| Letzte 365 Tage | Setzt Von und Bis auf heute − 365 Tage bis heute. |
| Projekte | Kommagetrennte Projektschlüssel, z. B. `ARTA, ARTB`. Leer = alle. ▾-Button öffnet eine Auswahlliste aus der geladenen Datei. |
| Issuetypen | Kommagetrennte Issuetypen, z. B. `Feature, Bug`. Leer = alle. ▾-Button öffnet eine Auswahlliste. |

### Ausschlüsse

Bestimmte Issues können vollständig aus allen Metriken entfernt werden — auch wenn sie ein Closed Date besitzen.

| Feld | Beschreibung |
|------|-------------|
| Status | Kommagetrennte Jira-Status, z. B. `Canceled`. ▾-Button öffnet Auswahlliste. |
| Resolution | Kommagetrennte Resolutions, z. B. `Won't Do, Duplicate`. ▾-Button öffnet Auswahlliste. |
| Zero-Day-Issues ausschließen | Checkbox + Spinbox (1–60 min). Issues, deren Cycle Time (First → Closed Date) kleiner als der Schwellwert ist, werden entfernt. Standard: 5 Minuten. |

Ausschluss-Defaults können über **Templates → Ausschlüsse als Standard speichern** dauerhaft gespeichert und mit **Standard-Ausschlüsse laden** wiederhergestellt werden.

!!! info "Zero-Day-Issues"
    Typisches Beispiel: Ein Issue wurde manuell innerhalb von Sekunden durch alle Workflow-Stages geklickt, ohne dass tatsächlich Entwicklungsarbeit stattfand. Solche Issues verzerren Flow-Time-Statistiken und sollten per Schwellwert ausgeschlossen werden.

### Metriken und CT-Methode

Über Checkboxen können einzelne Metriken aktiviert oder deaktiviert werden. **Alle** und **Keine** setzen alle Checkboxen auf einmal.

Die CT-Methode (nur für Flow Time relevant) wird per Radiobutton gewählt:

| Methode | Berechnung |
|---------|------------|
| A (Standard) | Kalendertage: `Closed Date − First Date` |
| B | Summe der Stage-Minuten von `First Date` bis `Closed Date` (letzte Stage ausgeschlossen) |

### Stage-Konsistenz-Check

Beim Laden von IssueTimes oder CFD werden die Stage-Spalten beider Dateien verglichen. Abweichungen werden im Log angezeigt:

```
Stage nur in IssueTimes: Review
Stage nur in CFD: In Review
```

### Tooltips

Alle interaktiven Elemente (Eingabefelder, Buttons, Radiobuttons, Checkboxen) zeigen beim Hover einen erläuternden Tooltip. Tooltips werden beim Sprachwechsel automatisch aktualisiert.

## Metriken

### Flow Time / Cycle Time

**Metrik-ID:** `flow_time`

Berechnet die Durchlaufzeit (in Tagen) von der ersten Aktivität (`First Date`) bis zum Abschluss (`Closed Date`) für alle abgeschlossenen Issues. Issues ohne beide Daten oder mit einer Durchlaufzeit von 0 Tagen werden ausgeschlossen.

**CT-Berechnungsmethoden:**

- **Methode A** (Standard): Differenz in Kalendertagen zwischen `First Date` und `Closed Date`.
- **Methode B**: Summe der Stage-Minuten aller Stages außer der letzten, dividiert durch 1440.

**Diagramme:**

- **Boxplot** — Verteilung der Durchlaufzeiten mit Statistik-Header (Min, Q1, Mittelwert, Median, Q3, Max, 90. Perzentil, Standardabweichung, Variationskoeffizient, Anzahl Zero-Day Issues).
- **Scatterplot** — Durchlaufzeit je Abschlussdatum mit:
  - **LOESS-Trendlinie** (blau, durchgezogen) — lokal gewichtete Regression ohne externe Abhängigkeit.
  - **Referenzlinien** (gepunktet): Median (rot), 85. Perzentil (hellgrün), 95. Perzentil (cyan).
  - **Farbkodierung der Punkte**: ≥ 95. Perzentil = rot, ≥ 85. Perzentil = orange, darunter = blau.
  - **X-Achse**: monatliche Ticks; ungerade Monate mit Namenskürzel, gerade Monate mit „·".

**Zero-Day Issues:**

Zwei Mechanismen greifen unabhängig voneinander:

1. **Vor der Metrikberechnung (Ausschluss-Filter):** Issues deren Cycle Time (First → Closed Date) kleiner als der konfigurierte Schwellwert ist (Standard: 5 Minuten), werden vollständig aus allen Metriken entfernt — bei aktivierter Checkbox in den Ausschlüssen.
2. **Innerhalb der Metrik:** Issues mit einer Durchlaufzeit ≤ 0 Tage (z. B. selber Kalendertag) werden aus der Berechnung herausgenommen und separat ausgewiesen.

- **PDF-Export**: Automatisch als `<reportname>_zero_day_issues.xlsx` im selben Ordner gespeichert (wenn Issues vorhanden).
- **Browser-Anzeige**: Issue-Keys im Log-Fenster aufgelistet.

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

- **Obere Trendlinie** — verläuft vom Gesamtbestand (Summe aller Stages) am ersten bis zum letzten Tag (Zufluss).
- **Untere Trendlinie** — verläuft vom Wert der letzten Stage (z. B. „Done"/„Closed") am ersten bis zum letzten Tag (Abfluss).
- **X-Achse** — Monatsgrenzen werden groß beschriftet (z. B. „Jan 2025"); ISO-Kalenderwochen-Montage werden klein und in Grau dargestellt (z. B. „W03"), damit sich die Labels nicht überlappen.

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
| Von-Datum | Feld „Von", 📅-Button oder „Letzte 365 Tage" | `--from-date` |
| Bis-Datum | Feld „Bis", 📅-Button oder „Letzte 365 Tage" | `--to-date` |
| Projekte | Feld „Projekte" (kommagetrennt) oder ▾-Auswahl | `--projects` |
| Issuetypen | Feld „Issuetypen" (kommagetrennt) oder ▾-Auswahl | `--issuetypes` |
| Status-Ausschluss | Ausschlüsse → Status (kommagetrennt) oder ▾-Auswahl | `--exclude-status` |
| Resolution-Ausschluss | Ausschlüsse → Resolution (kommagetrennt) oder ▾-Auswahl | `--exclude-resolution` |
| Zero-Day-Ausschluss | Ausschlüsse → Checkbox + Schwellwert (Minuten) | `--exclude-zero-day` / `--zero-day-threshold` |

- Der Datumsfilter bezieht sich auf das `Closed Date` der Issues.
- Issues ohne `Closed Date` werden bei gesetztem Datumsfilter ausgeschlossen.
- Ausgeschlossene Issues (Status, Resolution, Zero-Day) werden **vor** der Metrikberechnung entfernt und erscheinen in keiner Auswertung.
- CFD-Daten werden nur nach Datum gefiltert (keine Projekt- oder Issuetyp-Dimension).
- Standard-Datumsbereich: die letzten 365 Tage bis heute.

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

Alle Diagramme werden als kombiniertes HTML-Dokument in einer temporären Datei erzeugt und im Standard-Browser geöffnet. Die Diagramme sind vollständig interaktiv (Zoom, Pan, Hover-Tooltips, Legende ein-/ausblenden). Jede Metrik erhält eine Überschrift im HTML-Dokument.

### PDF-Export

```bash
python -m build_reports.cli <xlsx> --pdf report.pdf
```

- Einzelne Diagramme werden direkt als PDF erzeugt.
- Mehrere Diagramme werden über `pypdf` zu einem mehrseitigen PDF zusammengefügt.
- Der Export nutzt `kaleido` zur Rasterisierung (einmalig `choreo_get_chrome` ausführen, falls kaleido den Chrome-Binary noch nicht gefunden hat).
- Bei vorhandenen Zero-Day Issues wird automatisch `report_zero_day_issues.xlsx` im selben Ordner erstellt.
- Parallel zur PDF wird stets eine **Report-Excel-Datei** mit dem gleichen Dateinamen (Endung `.xlsx`) erstellt.

### Report Excel

Bei jedem PDF-Export wird automatisch eine XLSX-Datei (`<reportname>.xlsx`) erzeugt. Sie enthält alle gefilterten Issues im IssueTimes-Format, ergänzt um drei zusätzliche Spalten:

| Spalte | Inhalt |
|--------|--------|
| `Status Group` | Statusgruppe des Issues: `To Do`, `In Progress` oder `Done` (abgeleitet aus `First Date` und `Closed Date`) |
| `Cycle Time (First->Closed)` | Durchlaufzeit in Kalendertagen (`Closed Date − First Date`); leer wenn eines der Daten fehlt |
| `Cycle Time B (days in Status)` | Summe der Stage-Minuten (alle Stages außer der letzten) dividiert durch 1440; leer wenn eines der Daten fehlt |

### Zero-Day Issues Excel

Die exportierte Datei enthält dieselben Spalten wie IssueTimes (Project, Key, Issuetype, Status, Dates, Resolution), sortiert nach Projekt und Key. Der Dateiname wird automatisch aus dem PDF-Namen abgeleitet.

## Plugin-System

Neue Metriken können als eigenständiges Modul in `build_reports/metrics/` hinzugefügt werden:

```python
# build_reports/metrics/my_metric.py
from build_reports.metrics.base import MetricPlugin, MetricResult
from build_reports.metrics import register
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
