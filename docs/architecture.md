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

    System(sr, "SituationReport", "Toolsuite for the situational picture at portfolio and solution level: flow metrics, governance registers, forecasts and AI-drafted narration")

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
        Container(get_data, "get_data", "Python", "Fetches Jira issues via REST API or validates a manual export; minimises person data at the source (R1)")
        Container(helper, "helper", "Python · tkinter", "Merges multiple paginated Jira JSON files into one")
        Container(transform_data, "transform_data", "Python · tkinter", "Reads JSON export + workflow definition, computes stage times, writes XLSX files")
        Container(build_reports, "build_reports", "Python · tkinter · Plotly", "Reads XLSX, filters issues, computes flow metrics, exports HTML/PDF")
        Container(portfolio, "portfolio", "Python · tkinter · Plotly", "Aggregates several ARTs into pooled/comparison Large-Solution & Portfolio reports (HTML/PDF); governance registers, conference pre-read, snapshot/delta briefing, one-pager; optionally resolved down to ART level (ART depth)")
        Container(harmonisation, "harmonisation", "Python · tkinter", "Harmonisation score per end-to-end process: catalogue as data, 0–4 plus unknown, decision matrix, change between two states, AI reading")
        Container(testdata_generator, "testdata_generator", "Python · tkinter", "Generates synthetic Jira JSON exports for testing and demos")
        Container(simulate, "simulate", "Python · tkinter · Plotly", "Throughput-based Monte-Carlo forecast: how many / when done (with scope growth) + scope confidence; HTML report")
        Container(sources, "sources", "Python", "Pluggable external metric sources (Prometheus, GitHub, GitLab, SonarQube, CSV) for SLO, DORA and quality values")
        Container(llm, "llm", "Python", "Pluggable language models (local Ollama, Claude API, prompt export, mock) behind the numbers guard, AI labelling and audit trail")
    }

    Rel(user, get_data, "starts", "CLI")
    Rel(user, helper, "starts", "GUI / CLI")
    Rel(user, transform_data, "starts", "GUI / CLI")
    Rel(user, build_reports, "starts", "GUI / CLI")
    Rel(user, portfolio, "starts", "GUI / CLI")
    Rel(portfolio, build_reports, "reuses", "metrics + export")
    Rel(user, harmonisation, "starts", "GUI / CLI")
    Rel(portfolio, harmonisation, "embeds", "decision matrix as annex")
    Rel(harmonisation, llm, "drafts via", "AI reading")
    Rel(user, simulate, "starts", "GUI / CLI")
    Rel(simulate, build_reports, "reuses", "loader (ReportData)")
    Rel(user, testdata_generator, "starts", "GUI / CLI")
    Rel(get_data, jira, "reads", "REST API")
    Rel(get_data, transform_data, "delivers", "JSON (.json)")
    Rel(jira, helper, "page exports", "JSON (manual)")
    Rel(helper, transform_data, "delivers", "merged.json")
    Rel(testdata_generator, transform_data, "delivers", "JSON (.json)")
    Rel(transform_data, build_reports, "delivers", "IssueTimes.xlsx · CFD.xlsx")
    Rel(transform_data, simulate, "delivers", "IssueTimes.xlsx")
    Rel(portfolio, sources, "reads", "SLO · DORA · quality registers")
    Rel(portfolio, llm, "drafts via", "narration · summary · red-team questions · conference draft · translation")
```

### Data flow

```mermaid
flowchart LR
    jira(["☁️ Jira"])
    tdg["testdata_generator"]
    gd["get_data\nREST or export check"]
    hlp["helper\nJSON Merger"]
    td["transform_data"]
    br["build_reports"]
    pf["portfolio\nSolutions & Portfolios"]
    harmo["harmonisation"]
    reg(["🗂️ Governance registers\nJSON"])
    sim["simulate\nMonte-Carlo forecast"]
    out(["📄 HTML / PDF\n📊 Excel"])
    pfout(["📄 Report · Conference pre-read\nDelta briefing · One-pager"])

    jira -- "JSON\nmultiple pages" --> hlp
    gd -- "JSON" --> td
    gd -- REST --> jira
    hlp -- "merged.json" --> td
    tdg -- "JSON" --> td
    td -- "IssueTimes.xlsx\nCFD.xlsx\nTransitions.xlsx" --> br
    td -- "IssueTimes.xlsx" --> sim
    td -- "IssueTimes.xlsx\nper ART" --> pf
    reg --> pf
    harmo -- "decision matrix" --> pf
    br --> out
    sim --> out
    pf --> pfout
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

---

## Level 3 — Components: simulate

```mermaid
C4Component
    title Components: simulate

    Person(user, "User")
    System_Ext(xlsx_in, "IssueTimes.xlsx", "from transform_data")
    System_Ext(report_out, "Report output", "HTML (Plotly)")

    Container_Boundary(sim, "simulate") {
        Component(main, "__main__ / cli", "Python · argparse", "Entry point: GUI without args, CLI with args; run_simulation()")
        Component(gui, "gui", "tkinter", "File pickers + parameters (horizon, backlog, runs, split rate, seed); 5-language switch; project-template save/load")
        Component(throughput, "throughput", "Python", "ReportData -> daily throughput series incl. zero days")
        Component(forecast, "forecast", "Python (stdlib)", "Monte-Carlo engine: how_many / when_done / probability_at_least")
        Component(charts, "charts", "Plotly", "Exceedance curve, target marker, confidence gauge, distribution")
    }

    Rel(user, main, "starts (CLI)")
    Rel(user, gui, "starts (GUI)")
    Rel(main, throughput, "builds sample")
    Rel(gui, main, "run_simulation()")
    Rel(throughput, xlsx_in, "reads via build_reports loader")
    Rel(throughput, forecast, "ThroughputSample")
    Rel(forecast, charts, "forecast results")
    Rel(charts, report_out, "writes")
```

| File | Responsibility |
|------|---------------|
| `__main__.py` / `cli.py` | Entry point; argparse; `run_simulation()` |
| `gui.py` | tkinter UI (5 languages via flag switch); parameters; project-template save/load (`project_template`, `MODULE_SIMULATE`); HTML report + browser |
| `throughput.py` | `ReportData` → daily throughput series (incl. zero days) |
| `forecast.py` | Monte-Carlo engine: `how_many`, `when_done` (scope growth), `probability_at_least` |
| `charts.py` | Plotly: exceedance curve, target marker, confidence gauge, when-done distribution |

Standard library only (`random`, `bisect`, `statistics`) — no numpy/pandas — for
maximum portability; reuses `build_reports.loader` to read the input.

---

## Level 3 — Components: portfolio

```mermaid
C4Component
    title Components: portfolio

    Person(user, "User")
    System_Ext(xlsx_in, "IssueTimes.xlsx per ART", "from transform_data")
    System_Ext(registers, "Governance registers", "JSON: risks · NFR · capabilities · dependencies · decisions · SLO · DORA · flow problems · themes · solution areas")
    System_Ext(harmo, "harmonisation workspace", "decision matrix (annex)")
    System_Ext(out, "Output", "HTML · PDF · conference pre-read · delta briefing · one-pager · snapshot JSON")

    Container_Boundary(pf, "portfolio") {
        Component(cli, "__main__ / cli", "Python · argparse", "GUI without arguments; CLI: report, PDF, conference, snapshot, delta, one-pager, AI switches")
        Component(gui, "gui", "tkinter", "Solutions & Portfolios editor; data-source dialog with eleven registers; data folder (Datenraum)")
        Component(config, "solution_config + *_config", "Python", "Solution/portfolio config and one parse/load/save module per register (schema-versioned)")
        Component(aggregator, "aggregator", "Python · Plotly", "Record-level pooling over build_reports metrics; collectors per register; HTML/PDF/conference rendering")
        Component(summary, "summary", "Python", "Management summary, data quality, register blocks with legends (five languages)")
        Component(snapshot, "snapshot / delta", "Python", "Freeze a report state (eight governance registers); diff two states into the delta briefing")
        Component(ai, "exec_summary / red_team / conference_draft", "Python", "Contracts for the AI: numbers only from the snapshot, questions, pre-read draft (file or inline)")
        Component(onepager, "onepager", "Python", "Situation-briefing one-pager: four dimensions × three questions, BLUF template sentence, kata mode")
    }

    Rel(user, cli, "starts")
    Rel(cli, gui, "opens (no argument)")
    Rel(cli, aggregator, "calls")
    Rel(gui, aggregator, "calls")
    Rel(aggregator, config, "reads")
    Rel(config, registers, "loads")
    Rel(aggregator, xlsx_in, "pools via build_reports loader")
    Rel(aggregator, harmo, "embeds matrix")
    Rel(aggregator, summary, "renders blocks")
    Rel(snapshot, aggregator, "reuses collectors")
    Rel(ai, snapshot, "reads contract from")
    Rel(onepager, aggregator, "reuses collectors")
    Rel(aggregator, out, "writes")
    Rel(snapshot, out, "writes")
    Rel(onepager, out, "writes")
```

| File | Responsibility |
|------|---------------|
| `__main__.py` / `cli.py` | Entry point; argparse; `--pdf`, `--conference`, `--snapshot`, `--delta`, `--onepager`, `--kata`, AI switches |
| `gui.py` | Solutions & Portfolios GUI; data-source dialog (eleven register paths); templates; data folder |
| `solution_config.py` | Solution/portfolio config (members, mode, stage map, register paths, conference date) |
| `*_config.py` | One module per register: ROAM risks, NFR/runway, capabilities, dependencies, decisions, SLO, DORA, flow problems, themes, solution areas |
| `aggregator.py` | Record pooling; collectors; HTML report, PDF pages, conference pre-read (four inputs + annex) |
| `summary.py` | Management summary, data-quality flag, register tables and figures, legends |
| `decision_point.py` | Cross-value-stream pressure and the decision-point alarm (P4) |
| `snapshot.py` / `delta.py` | Report snapshot (eight governance registers) and delta briefing |
| `exec_summary.py` / `red_team.py` / `conference_draft.py` | AI contracts (D1, D5, D8) — numbers come from the snapshot, never from the model |
| `onepager.py` | One-pager (P6): deterministic reading of the same collectors; decision points only, no recommendations |
| `briefing.py` | Spoken briefing draft (M6): the one-pager's cells as citable facts `E/…` plus the fact index; guarded like D3/D4; own file, page stays AI-free |
| `report_texts.py` | All report texts in five languages |

---

## Level 3 — Components: harmonisation

| File | Responsibility |
|------|---------------|
| `__main__.py` / `cli.py` | GUI without arguments; CLI: report, `--since`/`--delta`, `--narrate` |
| `model.py` | Workspace (catalogue, processes, assessments, decisions) with schema validation |
| `score.py` | Score arithmetic: 0–4 plus "unknown", evidence grade → confidence, median and range |
| `delta.py` | Change between two states (`filter_as_of`, `compute_delta`) |
| `reading.py` | AI reading: contract without persons, prompt forbids recommendations, exit code 3 without a draft |
| `render.py` | Decision matrix, delta HTML, matrix block for the portfolio conference pre-read |
| `gui.py` | tkinter editor and report dialog (five languages) |

---

## Level 3 — Components: llm

| File | Responsibility |
|------|---------------|
| `base.py` | Provider protocol, `LlmResult`, deployment classes (local · remote · export · mock) |
| `providers/*.py` | Backends: `ollama` (local), `claude` (API), `export` (writes the prompt bundle instead of calling a model), `mock` |
| `narrate.py` | One entry point for every AI purpose: contract in, draft out, guards applied |
| `guard.py` | Numbers guard (no figure that is not in the contract) and the labelling banner (Art. 50) |
| `audit.py` | Operator record: one JSONL line per call (purpose, provider, model, address, hashes) |
| `prompts.py` | Versioned system prompts per purpose (exec summary, narration, red team, translation, conference draft, harmonisation reading) |
| `export.py` | Prompt bundle (`build_bundle`, `write_bundle`, clipboard) for a model run on another machine |
| `translate.py` | Report translation (D6) through the same guards |
