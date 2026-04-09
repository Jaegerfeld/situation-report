# SituationReport

Toolsuite zur Abfrage von Jira-Issuedaten sowie zur Aufbereitung für Metriken und Reports.

**Repository:** https://github.com/Jaegerfeld/situation-report

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
│   └── __init__.py
├── transform_data/
│   └── __init__.py
├── build_reports/
│   └── __init__.py
├── testdata_generator/
│   └── __init__.py
├── simulate/
│   └── __init__.py
├── .gitignore
├── pyproject.toml
└── SituationReport.md
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Technologie

- **Sprache:** Python >= 3.11
- **Paketmanagement:** pip / pyproject.toml
- **Versionskontrolle:** Git / GitHub
- **Datenquelle:** Jira REST API
