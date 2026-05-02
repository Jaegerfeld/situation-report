# SituationReport

Toolsuite zur Abfrage von Jira-Issuedaten sowie zur Aufbereitung für Metriken und Reports.

## Module

| Modul | Beschreibung | Status |
|-------|-------------|--------|
| [`transform_data`](modules/transform_data.md) | Transformation von Jira-Rohdaten in Stage-Time-Metriken | verfügbar |
| [`get_data`](modules/get_data.md) | Datenabruf aus Jira via REST API | geplant |
| [`build_reports`](modules/build_reports.md) | Erzeugung von Metriken und Reports | verfügbar |
| [`testdata_generator`](modules/testdata_generator.md) | Generierung synthetischer Testdaten | verfügbar (Alpha) |
| [`simulate`](modules/simulate.md) | Simulationen und Vorhersagemodelle | geplant |
| [`helper`](modules/helper.md) | Hilfswerkzeuge (JSON Merger u.a.) | verfügbar (Alpha) |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Für die Dokumentation lokal vorschauen:

```bash
pip install -e ".[docs]"
mkdocs serve
```
