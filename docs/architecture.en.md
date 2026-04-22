# Architecture

SituationReport follows the **C4 model** (Simon Brown): Context → Containers → Components.
The diagrams show three levels of detail — from the bird's-eye view down to individual files.

---

## Level 1 — System Context

Who uses the system and what external systems does it interact with?

```mermaid
C4Context
    title System Context: SituationReport

    Person(user, "Agile Coach / PI Manager", "Analyses Jira data and generates flow metrics")

    System(sr, "SituationReport", "Toolsuite for transforming Jira raw data into flow metrics and reports")

    System_Ext(jira, "Jira", "Issue tracking system (Atlassian)")

    Rel(user, sr, "starts", "GUI / CLI")
    Rel(sr, jira, "reads raw data", "REST API / JSON export")
    Rel(sr, user, "delivers", "HTML report / PDF / XLSX")
```

---

## Level 2 — Containers (Modules)

What modules exist, what technologies do they use, and how does data flow?

```mermaid
C4Container
    title Containers: SituationReport

    Person(user, "Agile Coach / PI Manager")

    System_Ext(jira, "Jira", "Issue tracking system")

    System_Boundary(sr, "SituationReport") {
        Container(get_data, "get_data", "Python", "Fetches Jira issues via REST API and stores JSON export (planned)")
        Container(transform_data, "transform_data", "Python · tkinter", "Reads JSON export + workflow definition, computes stage times, writes XLSX files")
        Container(build_reports, "build_reports", "Python · tkinter · Plotly", "Reads XLSX, filters issues, computes flow metrics, exports HTML/PDF")
        Container(testdata_generator, "testdata_generator", "Python", "Generates synthetic Jira JSON exports for testing (planned)")
        Container(simulate, "simulate", "Python", "Simulations and forecasting models (planned)")
    }

    Rel(user, get_data, "starts", "CLI")
    Rel(user, transform_data, "starts", "GUI / CLI")
    Rel(user, build_reports, "starts", "GUI / CLI")
    Rel(get_data, jira, "reads", "REST API")
    Rel(get_data, transform_data, "delivers", "JSON export (.json)")
    Rel(transform_data, build_reports, "delivers", "IssueTimes.xlsx · CFD.xlsx")
```

### Data flow

```
Jira
  │  JSON export
  ▼
get_data  ──►  transform_data  ──►  build_reports
                 │                        │
                 │  Transitions.xlsx       │  HTML report
                 │  IssueTimes.xlsx        │  PDF export
                 └  CFD.xlsx             ◄─┘
```

---

## Level 3 — Components: transform_data

```mermaid
C4Component
    title Components: transform_data

    Person(user, "User")
    System_Ext(jira_json, "JSON export", "Jira raw data")
    System_Ext(xlsx_out, "XLSX files", "Transitions · IssueTimes · CFD")

    Container_Boundary(td, "transform_data") {
        Component(main, "__main__ / transform", "Python", "Entry point: detects GUI vs. CLI call and delegates")
        Component(gui, "gui", "tkinter", "File dialogs, log area, progress bar; runs processing in background thread")
        Component(workflow, "workflow", "Python", "Reads workflow definition file, validates markers and stage names, builds status_to_stage mapping")
        Component(processor, "processor", "Python", "Processes JSON export: carry-forward, stage times, milestone dates (First / InProgress / Closed)")
        Component(writers, "writers", "openpyxl", "Writes Transitions.xlsx, IssueTimes.xlsx, CFD.xlsx")
    }

    Rel(user, main, "starts")
    Rel(main, gui, "opens (no argument)")
    Rel(main, processor, "calls (CLI)")
    Rel(gui, workflow, "reads workflow file")
    Rel(gui, processor, "starts in thread")
    Rel(processor, workflow, "uses mapping and stage order")
    Rel(processor, jira_json, "reads")
    Rel(processor, writers, "passes IssueRecords")
    Rel(writers, xlsx_out, "writes")
```

| File | Responsibility |
|------|---------------|
| `__main__.py` / `transform.py` | Entry point; detects GUI vs. CLI mode |
| `gui.py` | tkinter UI; background thread; progress bar after 3 s |
| `workflow.py` | Read, validate, and map workflow definition file |
| `processor.py` | Process Jira JSON; stage times, carry-forward, milestone fallbacks |
| `writers.py` | XLSX output (Transitions, IssueTimes, CFD) |

---

## Level 3 — Components: build_reports

```mermaid
C4Component
    title Components: build_reports

    Person(user, "User")
    System_Ext(xlsx_in, "XLSX input", "IssueTimes · CFD (from transform_data)")
    System_Ext(report_out, "Report output", "HTML · PDF")

    Container_Boundary(br, "build_reports") {
        Component(main, "__main__ / cli", "Python · argparse", "Entry point: parse CLI args, call run_reports()")
        Component(gui, "gui", "tkinter", "Filter UI, template management, exclusions, progress bar, browser and PDF export")
        Component(loader, "loader", "openpyxl", "Reads IssueTimes and CFD XLSX into typed data structures (ReportData)")
        Component(filters, "filters", "Python", "FilterConfig: date range, projects, issue type, exclusions by status/resolution")
        Component(metrics, "metrics/", "Plotly", "Plugin system with 5 metrics: Flow Time, CFD, Flow Load, Flow Velocity, Flow Distribution")
        Component(export, "export", "Plotly · WeasyPrint", "Renders HTML report and PDF from MetricResults")
        Component(stage_groups, "stage_groups", "Python", "Stage group definitions for aggregated analyses")
        Component(pi_config, "pi_config", "Python", "PI configuration: time ranges and sprint lengths")
        Component(terminology, "terminology", "Python", "Terminology mapping: custom stage labels")
    }

    Rel(user, main, "starts (CLI)")
    Rel(user, gui, "starts (GUI)")
    Rel(main, loader, "loads data")
    Rel(main, filters, "configures FilterConfig")
    Rel(gui, loader, "loads data")
    Rel(gui, filters, "configures FilterConfig")
    Rel(gui, export, "triggers export")
    Rel(loader, xlsx_in, "reads")
    Rel(filters, metrics, "delivers filtered ReportData")
    Rel(metrics, export, "delivers MetricResults (figures)")
    Rel(export, report_out, "writes")
```

| File / Directory | Responsibility |
|-----------------|---------------|
| `__main__.py` / `cli.py` | Entry point; argparse; `run_reports()` |
| `gui.py` | tkinter UI; templates; exclusions; progress bar; browser/PDF export |
| `loader.py` | Read XLSX → `ReportData` (typed dataclasses) |
| `filters.py` | `FilterConfig`; `apply_filters()`; exclusion logic |
| `metrics/base.py` | Abstract `MetricPlugin` class + `MetricResult` container |
| `metrics/*.py` | Concrete metrics: `flow_time`, `cfd`, `flow_load`, `flow_velocity`, `flow_distribution` |
| `export.py` | HTML rendering; PDF export via WeasyPrint |
| `stage_groups.py` | Stage group definitions |
| `pi_config.py` | PI time ranges, sprint lengths |
| `terminology.py` | Custom terminology |
