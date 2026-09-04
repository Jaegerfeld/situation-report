# SituationReport

Toolsuite für das Lagebild auf Portfolio- und Solution-Ebene: Flow-Metriken aus Jira, Governance-Register, Vorbereitung der Value-Stream-Conference, Prognosen und KI-Entwürfe — lokal auf dem eigenen Rechner.

!!! tip "📚 Die Denkschriften-Reihe – das Denken hinter dem Werkzeug"
    Die Software ist das Werkzeug; die **Denkschriften** sind ihr fachliches Fundament: wie große IT-Portfolios geführt werden – mit ehrlichem **Lagebild**, ausgebildeten **Stäben** und **KI als Stabsmitglied**. Sechs Schriften für Entscheider, frei verfügbar auf Deutsch und Englisch, jede mit ihrem wichtigsten Satz vorneweg.

    **→ [Die Denkschriften lesen](denkschriften/index.md)**

    [![Die Denkschriften-Reihe auf einen Blick](denkschriften/Denkschriften-Reihe_Ueberblick.png)](denkschriften/index.md)

## Module

| Modul | Beschreibung | Status |
|-------|-------------|--------|
| [`launcher`](modules/launcher.md) | Zentraler Einstiegspunkt – startet alle Module | verfügbar |
| [`transform_data`](modules/transform_data.md) | Transformation von Jira-Rohdaten in Stage-Time-Metriken | verfügbar |
| [`build_reports`](modules/build_reports.md) | Erzeugung von Metriken und Reports | verfügbar |
| [`portfolio`](modules/portfolio.md) | Aggregierte Large-Solution- & Portfolio-Reports über mehrere ARTs | verfügbar (Alpha) |
| [`helper`](modules/helper.md) | JSON-Dateien zusammenführen (Jira-Paginierung) | verfügbar (Alpha) |
| [`testdata_generator`](modules/testdata_generator.md) | Generierung synthetischer Testdaten | verfügbar (Beta) |
| [`get_data`](modules/get_data.md) | Datenabruf aus Jira — REST oder Export-Validierung | verfügbar (Alpha) |
| [`sources`](modules/sources.md) | Steckbare externe Metrik-Quellen (SLO, DORA, Qualität) | verfügbar (Alpha) |
| [`llm`](modules/llm.md) | Steckbare KI-Narration (lokal Ollama, Claude-API, mock) | verfügbar (Alpha) |
| [`simulate`](modules/simulate.md) | Simulationen und Vorhersagemodelle | verfügbar (Alpha) |

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
