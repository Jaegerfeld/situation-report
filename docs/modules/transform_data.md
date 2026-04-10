# transform_data

Liest einen Jira-JSON-Export und eine Workflow-Definition und erzeugt drei XLSX-Dateien mit Stage-Time-Metriken.

## Start

### GUI

```bash
python -m transform_data
```

Öffnet ein Fenster mit Datei-Auswahl-Dialogen. Wenn eine JSON-Datei gewählt wird, werden Ausgabeordner und Präfix automatisch vorbelegt.

```bash
python -m transform_data.gui
```

Startet die GUI direkt (ohne Argument-Prüfung).

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

### Übersicht

| Befehl | Ergebnis |
|--------|----------|
| `python -m transform_data` | GUI |
| `python -m transform_data <json> <workflow>` | CLI |
| `python -m transform_data.gui` | GUI (direkt) |
| `python -m transform_data.transform <json> <workflow>` | CLI (direkt) |
| `python -m transform_data --help` | CLI-Hilfe |

Erzeugt:

- `out/ART_A_Transitions.xlsx`
- `out/ART_A_IssueTimes.xlsx`
- `out/ART_A_CFD.xlsx`

## Workflow-Definitionsdatei

Textdatei, eine Stage pro Zeile.

```
Funnel:To Do
Analysis
Implementation
<First>Analysis
<InProgress>Implementation
<Closed>Done
Done
```

| Format | Bedeutung |
|--------|-----------|
| `Stage` | Canonical Stage Name |
| `Stage:Alias1:Alias2` | Stage mit Jira-Statusnamen, die darauf gemappt werden |
| `<First>Stage` | Diese Stage setzt das „First Date" |
| `<InProgress>Stage` | Diese Stage setzt das „Implementation Date" |
| `<Closed>Stage` | Diese Stage setzt das „Closed Date" |

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
| Closed Date | Erster Eintritt in die `<Closed>`-Stage |
| *Stage-Spalten* | Minuten in der jeweiligen Stage |
| Resolution | Jira-Resolution |

### CFD.xlsx

Cumulative Flow Diagram — eine Zeile pro Kalendertag, Stage-Spalten enthalten die Anzahl der Issues in der jeweiligen Stage.

## Stage-Zeit-Berechnung

- Die Zeit von der Issue-Erstellung bis zur ersten expliziten Transition wird der initialen Stage zugerechnet.
- Nicht gemappte Initialstatus werden auf die erste Stage in der Workflow-Definition zurückgefallen.
- Die letzte Stage akkumuliert Zeit bis zum Ausführungszeitpunkt (`reference_dt`).
- Issues ohne Transitionen haben für alle Stages den Wert 0.
