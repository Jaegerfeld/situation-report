# build_reports

Berechnet Flow-Metriken aus den von `transform_data` erzeugten XLSX-Dateien und stellt die Ergebnisse als interaktive Plotly-Diagramme im Browser oder als PDF-Export bereit.

## Überblick

| Eigenschaft | Wert |
|-------------|------|
| Status | verfügbar |
| Einstiegspunkt GUI | `build_reports_gui.pyw` |
| Einstiegspunkt CLI | `python -m build_reports` |
| Benutzerhandbuch (DE) | [build_reports_Benutzerhandbuch.pdf](../build_reports_Benutzerhandbuch.pdf) |
| User Manual (EN) | [build_reports_UserManual.pdf](../build_reports_UserManual.pdf) |

## Metriken

| Metrik (SAFe) | Metrik (Global) | Beschreibung | Pflichtdatei |
|---------------|-----------------|--------------|-------------|
| Flow Time | Cycle Time | Durchlaufzeit von Start bis Abschluss | IssueTimes.xlsx |
| Flow Velocity | Throughput | Abgeschlossene Issues pro Zeitraum | IssueTimes.xlsx |
| Flow Load | WIP | Aktuell in Bearbeitung befindliche Issues nach Stage | IssueTimes.xlsx |
| Cumulative Flow Diagram | Cumulative Flow Diagram | Kumulierte Stage-Eintritte über die Zeit | CFD.xlsx |
| Flow Distribution | Flow Distribution | Verteilung nach Typ, Stage-Dominanz und Ø Durchlaufzeit | IssueTimes.xlsx |
| Process Flow: Transitions | Process Flow: Transitions | Gerichteter Graph aller Statusübergänge (Anzahl) | Transitions.xlsx |
| Process Flow: Time | Process Flow: Time | Gerichteter Graph mit Knotenbreite und Kantenbreite nach medianer Verweildauer | Transitions.xlsx |

## Eingabedateien

| Datei | Pflicht | Beschreibung |
|-------|---------|-------------|
| `IssueTimes.xlsx` | ✅ | Alle Issues mit Zeitangaben je Stage |
| `CFD.xlsx` | optional | Tägliche Stage-Eintritte für das CFD |
| `Workflow.txt` | optional | `<First>` / `<Closed>`-Marker für CFD-Trendlinien |
| `pi_config_example.json` | optional | Eigene PI-Intervalle für Flow Velocity |
| `Transitions.xlsx` | optional | Statusübergänge je Issue für Process Flow |

## Architektur

```
build_reports/
├── metrics/             # Plugin-Registry + einzelne Metrik-Module
│   ├── base.py          # MetricPlugin / MetricResult Basisklassen
│   ├── flow_time.py
│   ├── flow_velocity.py
│   ├── flow_load.py
│   ├── cfd.py
│   ├── flow_distribution.py
│   └── process_flow.py
├── loader.py            # Laden aller XLSX-Dateien → ReportData
├── filters.py           # FilterConfig + apply_filters()
├── cli.py               # run_reports() + argparse CLI
├── gui.py               # tkinter GUI
├── export.py            # PDF- und Excel-Export
└── terminology.py       # SAFe / Global Terminologie-Umschaltung
```

Das Plugin-System registriert Metriken automatisch beim Import:

```python
from build_reports.metrics import get_metric, all_metrics
plugin = get_metric("flow_time")
result = plugin.compute(data, terminology="SAFe")
figs = plugin.render(result, "SAFe")
```

## Schnellstart CLI

```bash
python -m build_reports IssueTimes.xlsx --pdf report.pdf
python -m build_reports IssueTimes.xlsx --cfd CFD.xlsx --transitions Transitions.xlsx --browser
python -m build_reports IssueTimes.xlsx --metrics flow_time process_flow process_flow_time --from-date 2025-01-01
```

## Templates

Die GUI unterstützt das Speichern und Laden aller Einstellungen als JSON-Template (Menü → Templates). Templates sind versioniert (`"version": 4`) und abwärtskompatibel.
