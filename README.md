# SituationReport

Toolsuite zur Abfrage von Jira-Issuedaten sowie zur Aufbereitung für Metriken und Reports.

**Dokumentation:** https://jaegerfeld.github.io/situation-report/

## Module

| Modul | Beschreibung | Status |
|-------|-------------|--------|
| [`transform_data`](https://jaegerfeld.github.io/situation-report/modules/transform_data/) | Transformation von Jira-Rohdaten in Stage-Time-Metriken | verfügbar |
| `get_data` | Datenabruf aus Jira via REST API | geplant |
| `build_reports` | Erzeugung von Metriken und Reports | geplant |
| `testdata_generator` | Generierung synthetischer Testdaten | geplant |
| `simulate` | Simulationen und Vorhersagemodelle | geplant |

## Setup

```bash
git clone https://github.com/Jaegerfeld/situation-report.git
cd situation-report
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Lizenz

BSD-3-Clause — siehe [LICENSE](LICENSE)
