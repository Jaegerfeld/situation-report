# SituationReport

Toolsuite zur Abfrage von Jira-Issuedaten sowie zur Aufbereitung für Metriken und Reports.

!!! tip "📚 Die Denkschriften-Reihe – das Denken hinter dem Werkzeug"
    Die Software ist das Werkzeug; die **Denkschriften** sind ihr fachliches Fundament: wie große IT-Portfolios geführt werden – mit ehrlichem **Lagebild**, ausgebildeten **Stäben** und **KI als Stabsmitglied**. Sechs Schriften für Entscheider, frei verfügbar auf Deutsch und Englisch, jede mit ihrem wichtigsten Satz vorneweg.

    **→ [Die Denkschriften lesen](denkschriften/index.md)**

    [![Die Denkschriften-Reihe auf einen Blick](denkschriften/Denkschriften-Reihe_Ueberblick.png)](denkschriften/index.md)

## Module

| Modul | Beschreibung | Status |
|-------|-------------|--------|
| [`transform_data`](modules/transform_data.md) | Transformation von Jira-Rohdaten in Stage-Time-Metriken | verfügbar |
| [`get_data`](modules/get_data.md) | Datenabruf aus Jira via REST API | geplant |
| [`build_reports`](modules/build_reports.md) | Erzeugung von Metriken und Reports | verfügbar |
| [`testdata_generator`](modules/testdata_generator.md) | Generierung synthetischer Testdaten | verfügbar (Beta) |
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
