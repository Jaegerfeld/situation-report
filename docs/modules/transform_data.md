# transform_data

Liest einen Jira-JSON-Export und eine Workflow-Definition und erzeugt drei XLSX-Dateien mit Stage-Time-Metriken.

!!! tip "Benutzerhandbuch (PDF)"
    Für Nicht-Techniker steht ein ausführliches Benutzerhandbuch bereit:
    **[transform_data_Benutzerhandbuch.pdf](../transform_data_Benutzerhandbuch.pdf)**

## Start

### GUI

```bash
python -m transform_data
```

Öffnet ein Fenster mit Datei-Auswahl-Dialogen. Wenn eine JSON-Datei gewählt wird, werden Ausgabeordner und Präfix automatisch vorbelegt. Warnungen und Ergebnisse erscheinen im Log-Bereich.

```bash
python -m transform_data.gui
```

Startet die GUI direkt (ohne Argument-Prüfung).

Alternativ: Doppelklick auf `start_gui.pyw` im Projektverzeichnis — öffnet die GUI ohne Konsolenfenster.

### Kommandozeile

```bash
python -m transform_data <json_datei> <workflow_datei> [Optionen]
python -m transform_data.transform <json_datei> <workflow_datei> [Optionen]
```

Beide Varianten sind gleichwertig. Die zweite (`transform_data.transform`) ist immer ein reiner CLI-Aufruf, unabhängig von der Anzahl der Argumente.

**Argumente**

| Argument | Beschreibung |
|----------|-------------|
| `json_datei` | Jira-JSON-Export (Pflichtfeld) |
| `workflow_datei` | Workflow-Definitionsdatei (Pflichtfeld) |
| `--output-dir` | Ausgabeverzeichnis (Standard: Verzeichnis der JSON-Datei) |
| `--prefix` | Präfix für die Ausgabedateien (Standard: Dateiname der JSON-Datei) |

**Beispiel**

```bash
python -m transform_data data/ART_A.json data/workflow_ART_A.txt --output-dir out/ --prefix ART_A
```

Erzeugt:

- `out/ART_A_Transitions.xlsx`
- `out/ART_A_IssueTimes.xlsx`
- `out/ART_A_CFD.xlsx`

### Übersicht

| Befehl | Ergebnis |
|--------|----------|
| `python -m transform_data` | GUI |
| `python -m transform_data <json> <workflow>` | CLI |
| `python -m transform_data.gui` | GUI (direkt) |
| `python -m transform_data.transform <json> <workflow>` | CLI (direkt) |
| `python -m transform_data --help` | CLI-Hilfe |
| Doppelklick auf `start_gui.pyw` | GUI ohne Konsolenfenster |

## Workflow-Definitionsdatei

Textdatei, eine Stage pro Zeile.

```
Funnel:New:Open
Analysis:In Analysis
Implementation:In Progress
Done:Canceled
<First>Analysis
<InProgress>Implementation
<Closed>Done
```

| Format | Bedeutung |
|--------|-----------|
| `Stage` | Kanonischer Stage-Name |
| `Stage:Alias1:Alias2` | Stage mit Jira-Statusnamen, die darauf gemappt werden |
| `<First>Stage` | Diese Stage setzt das „First Date" |
| `<InProgress>Stage` | Diese Stage setzt das „Implementation Date" (Standard: Stage namens „Implementation") |
| `<Closed>Stage` | Diese Stage setzt das „Closed Date" |

### Validierung der Workflow-Datei

Beim Einlesen der Workflow-Datei werden folgende Prüfungen durchgeführt:

| Situation | Verhalten |
|-----------|-----------|
| `<First>` / `<Closed>` nicht definiert | Warnung: Datumsspalte bleibt leer |
| Stage-Name im Marker existiert nicht in der Datei | **Fehler** mit Liste der gültigen Stage-Namen |
| Stage definiert, aber von keinem Issue erreicht | Kein Eingriff — Datumsspalte bleibt leer |

### Nicht gemappte Jira-Status

Enthält der Jira-Export Status, die in der Workflow-Datei nicht als Stage oder Alias definiert sind, gibt das Tool eine Warnung aus:

```
WARNUNG: 2 Status in den Daten nicht in der Workflow-Datei gemappt:
  - To Do
  - Unknown
  > Zeit dieser Status wird der letzten bekannten Stage zugerechnet.
```

Die Zeit in nicht gemappten Status wird der **letzten bekannten Stage** zugerechnet (Carry-forward). Issues bleiben vollständig in allen Ausgaben erhalten.

## Ausgabedateien

### Transitions.xlsx

Eine Zeile pro Statuswechsel pro Issue, chronologisch sortiert.

| Spalte | Inhalt |
|--------|--------|
| Key | Issue-Schlüssel |
| Transition | Stage-Name (oder „Created") |
| Timestamp | Zeitpunkt des Wechsels |

### IssueTimes.xlsx

Eine Zeile pro Issue mit der verbrachten Zeit (in Minuten) je Stage.

| Spalte | Inhalt |
|--------|--------|
| Project, Key, Issuetype, Status, … | Issue-Stammdaten |
| Created Date | Erstellungszeitpunkt |
| First Date | Erster Eintritt in die `<First>`-Stage |
| Implementation Date | Erster Eintritt in die `<InProgress>`-Stage |
| Closed Date | Letzter Eintritt in die `<Closed>`-Stage |
| *Stage-Spalten* | Minuten in der jeweiligen Stage |
| Resolution | Jira-Resolution |

### CFD.xlsx

Cumulative Flow Diagram — eine Zeile pro Kalendertag, Stage-Spalten enthalten die Anzahl der Issues in der jeweiligen Stage.

## Stage-Zeit-Berechnung

- Die Zeit von der Issue-Erstellung bis zur ersten expliziten Transition wird der initialen Stage zugerechnet.
- Nicht gemappte Initialstatus werden der ersten Stage in der Workflow-Definition zugerechnet.
- Bei Transitionen in nicht gemappte Status läuft die Zeit in der **letzten bekannten Stage** weiter (Carry-forward).
- Die letzte bekannte Stage akkumuliert Zeit bis zum Ausführungszeitpunkt.
- Issues ohne Transitionen haben für alle Stages den Wert 0.

!!! info "Closed Date"
    Das Closed Date wird beim **letzten** Eintritt in die `<Closed>`-Stage gesetzt. Bei Issues die wiedereröffnet und erneut geschlossen wurden, zählt der jüngste Schließzeitpunkt.

!!! info "Übersprungene Closed-Stage"
    Hat ein Issue ein First Date, aber die `<Closed>`-Stage wurde übersprungen (z. B. direkter Wechsel von Implementation nach Done), gilt die **erste Stage chronologisch nach der Closed-Stage** im Workflow als Closed Date. Damit werden Issues, bei denen Entwicklung stattgefunden hat und ein Status im Prozess übersprungen wurde, korrekt als geschlossen gezählt. Issues ohne First Date (z. B. direkt nach Canceled) erhalten kein Closed Date.

## Tests

```bash
python -m pytest tests/transform_data/
```

| Testtyp | Verzeichnis | Inhalt |
|---------|-------------|--------|
| Unit | `tests/transform_data/unit/` | Isolierte Tests für `workflow.py` und `processor.py` mit synthetischen Fixtures |
| Acceptance | `tests/transform_data/acceptance/` | Tests gegen den realen ART_A-Datensatz; prüfen fachliche Korrektheit |
