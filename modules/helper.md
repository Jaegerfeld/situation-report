# helper

Das Modul `helper` enthält Hilfswerkzeuge für die SituationReport-Toolsuite.
Aktuell verfügbar: **JSON Merger** — fügt mehrere Jira-REST-API-JSON-Dateien zusammen.

**Start:**
```bash
python -m helper
```

Oder über die Startdatei im portablen Paket:
- **Windows:** `Helper.bat`
- **macOS:** `Helper.command`
- **Linux:** `Helper.sh`

---

## JSON Merger

### Problem

Jira-REST-API-Abfragen liefern maximal 1000 Issues pro Request. Bei größeren
Projekten müssen mehrere paginierte Abfragen durchgeführt werden, die jeweils
eine eigene JSON-Datei erzeugen. Vor der Verarbeitung mit `transform_data`
müssen diese Dateien zu einer einzigen zusammengeführt werden.

### GUI-Oberfläche

```
┌──────────────────────────────────────────────────┐
│  helper – JSON Merger  v0.8.x                    │
├──────────────────────────────────────────────────┤
│  Eingabedateien                                  │
│  ┌────────────────────────────────────────────┐  │
│  │ /pfad/zu/projekt_0.json                    │  │
│  │ /pfad/zu/projekt_1000.json                 │  │
│  │ /pfad/zu/projekt_2000.json                 │  │
│  └────────────────────────────────────────────┘  │
│  [Hinzufügen…]  [Entfernen]                      │
│                                                  │
│  Ausgabedatei (JSON)                             │
│  [/pfad/zu/merged.json              ] [Suchen…]  │
│                                                  │
│  ☑ Duplikate entfernen (nach Issue-ID)           │
│                                                  │
│               [Zusammenführen]                   │
│  ┌────────────────────────────────────────────┐  │
│  │ Log                                        │  │
│  │ Reading: projekt_0.json                    │  │
│  │   533 issues found.                        │  │
│  │ Reading: projekt_1000.json                 │  │
│  │   412 issues found.                        │  │
│  │ Merged 2 file(s) → 945 issues → merged.json│  │
│  │ --- Fertig ---                             │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### CLI

```bash
python -m helper file1.json file2.json file3.json --output merged.json
python -m helper file1.json file2.json --output merged.json --no-dedup
```

| Argument | Beschreibung |
|----------|-------------|
| `inputs` (positional) | Eine oder mehrere Eingabe-JSON-Dateien |
| `--output FILE` | Ausgabedatei (Pflicht) |
| `--no-dedup` | Deduplizierung deaktivieren |

### Deduplizierung

Standardmäßig werden Issues mit identischer `id` nur einmal in die Ausgabe
übernommen. Das ist wichtig, wenn sich Jira-Abfragen zeitlich überschneiden
und dieselben Issues mehrfach liefern. Im Log erscheint für jedes Duplikat
eine Warnung.

Mit `--no-dedup` bleiben alle Issues erhalten — nützlich wenn die id-Felder
keine Jira-IDs sondern generierte Werte sind.

### Ausgabeformat

Die erzeugte Datei entspricht dem Jira-REST-API-Format und ist direkt mit
`transform_data` verarbeitbar:

```json
{
  "expand": "schema,names",
  "startAt": 0,
  "maxResults": 945,
  "total": 945,
  "issues": [...]
}
```

### Workflow

```bash
# 1. JSON-Dateien zusammenführen
python -m helper page1.json page2.json --output merged.json

# 2. Mit transform_data verarbeiten
python -m transform_data merged.json --workflow workflow.txt
```

---

## Architektur

```
helper/
├── __init__.py        leer
├── __main__.py        Dispatcher (GUI / CLI)
├── merger.py          Kernlogik: merge_json_files()
├── cli.py             run_merge() + argparse CLI
└── gui.py             tkinter-GUI
```

---

## Tests

```bash
python -m pytest tests/helper/ -v
```

- **Unit-Tests** (`tests/helper/unit/`): Merge-Logik, Deduplizierung, Envelope-Felder, Edge Cases
- **Acceptance-Tests** (`tests/helper/acceptance/`): End-to-End mit `transform_data`
