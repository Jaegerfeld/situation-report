# SituationReport

Toolsuite zur Abfrage von Jira-Issuedaten sowie zur Aufbereitung für Metriken und Reports.

## Module

| Modul | Beschreibung |
|-------|-------------|
| `get_data` | Datenabruf aus Jira via API |
| `transform_data` | Bereinigung und Transformation der Rohdaten |
| `build_reports` | Erzeugung von Metriken und Reports |
| `testdata_generator` | Generierung synthetischer Testdaten |
| `simulate` | Simulationen und Vorhersagemodelle |

## Projektstruktur

```
situation-report/
├── get_data/
├── transform_data/
├── build_reports/
├── testdata_generator/
├── simulate/
├── pyproject.toml
└── SituationReport.md
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```
