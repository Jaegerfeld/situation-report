# Architektur

SituationReport folgt dem **C4-Modell** (Simon Brown): Kontext → Module → Komponenten.
Die Diagramme zeigen drei Detailstufen — von der Vogelperspektive bis auf Dateiebene.

---

## Level 1 — System-Kontext

Wer benutzt das System und mit welchen externen Systemen interagiert es?

```mermaid
C4Context
    title System-Kontext: SituationReport

    Person(user, "Agile Coach / PI Manager", "Analysiert Jira-Daten und erzeugt Flow-Metriken")

    System(sr, "SituationReport", "Toolsuite zur Transformation von Jira-Rohdaten in Flow-Metriken und Reports")

    System_Ext(jira, "Jira", "Issue-Tracking-System (Atlassian)")

    Rel(user, sr, "startet", "GUI / CLI")
    Rel(sr, jira, "liest Rohdaten", "REST API / JSON-Export")
    Rel(sr, user, "liefert", "HTML-Report / PDF / XLSX")
```

---

## Level 2 — Module (Container)

Welche Module gibt es, welche Technologien nutzen sie und wie fließen Daten?

```mermaid
C4Container
    title Module: SituationReport

    Person(user, "Agile Coach / PI Manager")

    System_Ext(jira, "Jira", "Issue-Tracking-System")

    System_Boundary(sr, "SituationReport") {
        Container(get_data, "get_data", "Python", "Ruft Jira-Issues via REST API ab und speichert JSON-Export (geplant)")
        Container(transform_data, "transform_data", "Python · tkinter", "Liest JSON-Export + Workflow-Definition, berechnet Stage-Zeiten, schreibt XLSX-Dateien")
        Container(build_reports, "build_reports", "Python · tkinter · Plotly", "Liest XLSX, filtert Issues, berechnet Flow-Metriken, exportiert HTML/PDF")
        Container(testdata_generator, "testdata_generator", "Python", "Erzeugt synthetische Jira-JSON-Exporte für Tests (geplant)")
        Container(simulate, "simulate", "Python", "Simulationen und Vorhersagemodelle (geplant)")
    }

    Rel(user, get_data, "startet", "CLI")
    Rel(user, transform_data, "startet", "GUI / CLI")
    Rel(user, build_reports, "startet", "GUI / CLI")
    Rel(get_data, jira, "liest", "REST API")
    Rel(get_data, transform_data, "liefert", "JSON-Export (.json)")
    Rel(transform_data, build_reports, "liefert", "IssueTimes.xlsx · CFD.xlsx")
```

### Datenfluss

```
Jira
  │  JSON-Export
  ▼
get_data  ──►  transform_data  ──►  build_reports
                 │                        │
                 │  Transitions.xlsx       │  HTML-Report
                 │  IssueTimes.xlsx        │  PDF-Export
                 └  CFD.xlsx             ◄─┘
```

---

## Level 3 — Komponenten: transform_data

```mermaid
C4Component
    title Komponenten: transform_data

    Person(user, "Benutzer")
    System_Ext(jira_json, "JSON-Export", "Jira-Rohdaten")
    System_Ext(xlsx_out, "XLSX-Dateien", "Transitions · IssueTimes · CFD")

    Container_Boundary(td, "transform_data") {
        Component(main, "__main__ / transform", "Python", "Entry Point: erkennt GUI- vs. CLI-Aufruf und delegiert")
        Component(gui, "gui", "tkinter", "Datei-Dialoge, Log-Bereich, Ladebalken; startet Verarbeitung im Hintergrund-Thread")
        Component(workflow, "workflow", "Python", "Liest Workflow-Definitionsdatei, validiert Marker und Stage-Namen, baut status_to_stage-Mapping")
        Component(processor, "processor", "Python", "Verarbeitet JSON-Export: Carry-forward, Stage-Zeiten, Meilenstein-Daten (First / InProgress / Closed)")
        Component(writers, "writers", "openpyxl", "Schreibt Transitions.xlsx, IssueTimes.xlsx, CFD.xlsx")
    }

    Rel(user, main, "startet")
    Rel(main, gui, "öffnet (kein Argument)")
    Rel(main, processor, "ruft auf (CLI)")
    Rel(gui, workflow, "liest Workflow-Datei")
    Rel(gui, processor, "startet in Thread")
    Rel(processor, workflow, "nutzt Mapping und Stage-Reihenfolge")
    Rel(processor, jira_json, "liest")
    Rel(processor, writers, "übergibt IssueRecords")
    Rel(writers, xlsx_out, "schreibt")
```

| Datei | Verantwortung |
|-------|--------------|
| `__main__.py` / `transform.py` | Entry Point; erkennt GUI- vs. CLI-Modus |
| `gui.py` | tkinter-Oberfläche; Background-Thread; Ladebalken nach 3 s |
| `workflow.py` | Workflow-Definitionsdatei lesen, validieren, Mapping aufbauen |
| `processor.py` | Jira-JSON verarbeiten; Stage-Zeiten, Carry-forward, Meilenstein-Fallbacks |
| `writers.py` | XLSX-Ausgabe (Transitions, IssueTimes, CFD) |

---

## Level 3 — Komponenten: build_reports

```mermaid
C4Component
    title Komponenten: build_reports

    Person(user, "Benutzer")
    System_Ext(xlsx_in, "XLSX-Eingabe", "IssueTimes · CFD (von transform_data)")
    System_Ext(report_out, "Report-Ausgabe", "HTML · PDF")

    Container_Boundary(br, "build_reports") {
        Component(main, "__main__ / cli", "Python · argparse", "Entry Point: CLI-Argumente parsen, run_reports() aufrufen")
        Component(gui, "gui", "tkinter", "Filter-UI, Template-Verwaltung, Ausschlüsse, Ladebalken, Browser- und PDF-Export")
        Component(loader, "loader", "openpyxl", "Liest IssueTimes- und CFD-XLSX in typisierte Datenstrukturen (ReportData)")
        Component(filters, "filters", "Python", "FilterConfig: Zeitraum, Projekte, Issuetype, Ausschlüsse nach Status/Resolution")
        Component(metrics, "metrics/", "Plotly", "Plugin-System mit 5 Metriken: Flow Time, CFD, Flow Load, Flow Velocity, Flow Distribution")
        Component(export, "export", "Plotly · WeasyPrint", "Rendert HTML-Report und PDF aus MetricResults")
        Component(stage_groups, "stage_groups", "Python", "Stage-Gruppen für aggregierte Auswertungen")
        Component(pi_config, "pi_config", "Python", "PI-Konfiguration: Zeiträume und Sprint-Längen")
        Component(terminology, "terminology", "Python", "Terminologie-Mapping: benutzerdefinierte Stage-Labels")
    }

    Rel(user, main, "startet (CLI)")
    Rel(user, gui, "startet (GUI)")
    Rel(main, loader, "lädt Daten")
    Rel(main, filters, "konfiguriert FilterConfig")
    Rel(gui, loader, "lädt Daten")
    Rel(gui, filters, "konfiguriert FilterConfig")
    Rel(gui, export, "startet Export")
    Rel(loader, xlsx_in, "liest")
    Rel(filters, metrics, "liefert gefilterte ReportData")
    Rel(metrics, export, "liefert MetricResults (Figures)")
    Rel(export, report_out, "schreibt")
```

| Datei / Verzeichnis | Verantwortung |
|--------------------|--------------|
| `__main__.py` / `cli.py` | Entry Point; argparse; `run_reports()` |
| `gui.py` | tkinter-Oberfläche; Templates; Ausschlüsse; Ladebalken; Browser-/PDF-Export |
| `loader.py` | XLSX einlesen → `ReportData` (typisierte Dataclasses) |
| `filters.py` | `FilterConfig`; `apply_filters()`; Ausschluss-Logik |
| `metrics/base.py` | Abstrakte `MetricPlugin`-Klasse + `MetricResult`-Container |
| `metrics/*.py` | Konkrete Metriken: `flow_time`, `cfd`, `flow_load`, `flow_velocity`, `flow_distribution` |
| `export.py` | HTML-Rendering; PDF-Export via WeasyPrint |
| `stage_groups.py` | Stage-Gruppen-Definition |
| `pi_config.py` | PI-Zeiträume, Sprint-Längen |
| `terminology.py` | Benutzerdefinierte Terminologie |
