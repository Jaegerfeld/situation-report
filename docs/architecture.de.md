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

    System(sr, "SituationReport", "Toolsuite für das Lagebild auf Portfolio- und Solution-Ebene: Flow-Metriken, Governance-Register, Prognosen und KI-Entwürfe")

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
        Container(get_data, "get_data", "Python", "Ruft Jira-Issues via REST API ab oder prüft einen manuellen Export")
        Container(helper, "helper", "Python · tkinter", "Führt mehrere paginierte Jira-JSON-Dateien zu einer zusammen")
        Container(transform_data, "transform_data", "Python · tkinter", "Liest JSON-Export + Workflow-Definition, berechnet Stage-Zeiten, schreibt XLSX-Dateien")
        Container(build_reports, "build_reports", "Python · tkinter · Plotly", "Liest XLSX, filtert Issues, berechnet Flow-Metriken, exportiert HTML/PDF")
        Container(portfolio, "portfolio", "Python · tkinter · Plotly", "Aggregiert mehrere ARTs zu Pooled-/Comparison-Reports auf Large-Solution- & Portfolio-Ebene (HTML/PDF); optional bis auf ART-Ebene aufgelöst (ART-Tiefe)")
        Container(testdata_generator, "testdata_generator", "Python · tkinter", "Erzeugt synthetische Jira-JSON-Exporte für Tests und Demos")
        Container(simulate, "simulate", "Python · tkinter · Plotly", "Throughput-basierter Monte-Carlo-Forecast: wie viele / wann fertig (mit Scope-Wachstum) + Scope-Konfidenz; HTML-Report")
        Container(sources, "sources", "Python", "Steckbare externe Metrik-Quellen (Prometheus, GitHub, GitLab, SonarQube, CSV) für SLO-, DORA- und Qualitätswerte")
        Container(llm, "llm", "Python", "Steckbare Sprachmodelle (lokal Ollama, Claude-API, mock) hinter Zahlen-Wächter, KI-Kennzeichnung und Betreiber-Nachweis")
    }

    Rel(user, get_data, "startet", "CLI")
    Rel(user, helper, "startet", "GUI / CLI")
    Rel(user, transform_data, "startet", "GUI / CLI")
    Rel(user, build_reports, "startet", "GUI / CLI")
    Rel(user, portfolio, "startet", "GUI / CLI")
    Rel(portfolio, build_reports, "nutzt", "Metriken + Export")
    Rel(user, simulate, "startet", "GUI / CLI")
    Rel(simulate, build_reports, "nutzt", "Loader (ReportData)")
    Rel(user, testdata_generator, "startet", "GUI / CLI")
    Rel(get_data, jira, "liest", "REST API")
    Rel(get_data, transform_data, "liefert", "JSON (.json)")
    Rel(jira, helper, "Seiten-Exporte", "JSON (manuell)")
    Rel(helper, transform_data, "liefert", "merged.json")
    Rel(testdata_generator, transform_data, "liefert", "JSON (.json)")
    Rel(transform_data, build_reports, "liefert", "IssueTimes.xlsx · CFD.xlsx")
    Rel(transform_data, simulate, "liefert", "IssueTimes.xlsx")
    Rel(portfolio, sources, "liest", "SLO- · DORA- · Qualitäts-Register")
    Rel(portfolio, llm, "entwirft über", "Narration · Summary · Red-Team-Fragen")
```

### Datenfluss

```mermaid
flowchart LR
    jira(["☁️ Jira"])
    tdg["testdata_generator"]
    gd["get_data\nREST oder Export-Prüfung"]
    hlp["helper\nJSON Merger"]
    td["transform_data"]
    br["build_reports"]
    sim["simulate\nMonte-Carlo-Forecast"]
    out(["📄 HTML / PDF\n📊 Excel"])

    jira -- "JSON\nmehrere Seiten" --> hlp
    gd -- "JSON" --> td
    gd -- REST --> jira
    hlp -- "merged.json" --> td
    tdg -- "JSON" --> td
    td -- "IssueTimes.xlsx\nCFD.xlsx\nTransitions.xlsx" --> br
    td -- "IssueTimes.xlsx" --> sim
    br --> out
    sim --> out
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

---

## Level 3 — Komponenten: simulate

```mermaid
C4Component
    title Komponenten: simulate

    Person(user, "Nutzer")
    System_Ext(xlsx_in, "IssueTimes.xlsx", "aus transform_data")
    System_Ext(report_out, "Report-Ausgabe", "HTML (Plotly)")

    Container_Boundary(sim, "simulate") {
        Component(main, "__main__ / cli", "Python · argparse", "Entry Point: GUI ohne Argumente, CLI mit Argumenten; run_simulation()")
        Component(gui, "gui", "tkinter", "Dateiauswahl + Parameter (Horizont, Backlog, Läufe, Split-Rate, Seed); 5-Sprachen-Umschaltung; Projekt-Template Speichern/Laden")
        Component(throughput, "throughput", "Python", "ReportData -> Tagesdurchsatz-Reihe inkl. Null-Tage")
        Component(forecast, "forecast", "Python (stdlib)", "Monte-Carlo-Engine: how_many / when_done / probability_at_least")
        Component(charts, "charts", "Plotly", "Exceedance-Kurve, Ziel-Marker, Konfidenz-Gauge, Verteilung")
    }

    Rel(user, main, "startet (CLI)")
    Rel(user, gui, "startet (GUI)")
    Rel(main, throughput, "baut Sample")
    Rel(gui, main, "run_simulation()")
    Rel(throughput, xlsx_in, "liest via build_reports-Loader")
    Rel(throughput, forecast, "ThroughputSample")
    Rel(forecast, charts, "Forecast-Ergebnisse")
    Rel(charts, report_out, "schreibt")
```

| Datei | Verantwortung |
|------|---------------|
| `__main__.py` / `cli.py` | Entry Point; argparse; `run_simulation()` |
| `gui.py` | tkinter-Oberfläche (5 Sprachen per Flaggen-Umschalter); Parameter; Projekt-Template Speichern/Laden (`project_template`, `MODULE_SIMULATE`); HTML-Report + Browser |
| `throughput.py` | `ReportData` → Tagesdurchsatz-Reihe (inkl. Null-Tage) |
| `forecast.py` | Monte-Carlo-Engine: `how_many`, `when_done` (Scope-Wachstum), `probability_at_least` |
| `charts.py` | Plotly: Exceedance-Kurve, Ziel-Marker, Konfidenz-Gauge, Termin-Verteilung |

Reine Standardbibliothek (`random`, `bisect`, `statistics`) — kein numpy/pandas —
für maximale Portabilität; nutzt `build_reports.loader` zum Einlesen der Eingabe.
