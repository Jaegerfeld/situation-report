# build_reports

Calculates flow metrics from the XLSX files produced by `transform_data` and presents the results as interactive Plotly charts in the browser or as a PDF export.

## Overview

| Property | Value |
|----------|-------|
| Status | available |
| GUI entry point | `build_reports_gui.pyw` |
| CLI entry point | `python -m build_reports` |
| Benutzerhandbuch (DE) | [build_reports_Benutzerhandbuch.pdf](../build_reports_Benutzerhandbuch.pdf) |
| User Manual (EN) | [build_reports_UserManual.pdf](../build_reports_UserManual.pdf) |
| Manual de Utilizator (RO) | [build_reports_ManualUtilizator.pdf](../build_reports_ManualUtilizator.pdf) |
| Manual do Utilizador (PT) | [build_reports_ManualUtilizador.pdf](../build_reports_ManualUtilizador.pdf) |
| Manuel d'utilisation (FR) | [build_reports_ManuelUtilisateur.pdf](../build_reports_ManuelUtilisateur.pdf) |

## Metrics

| Metric (SAFe) | Metric (Global) | Description | Required file |
|---------------|-----------------|-------------|--------------|
| Flow Time | Cycle Time | Cycle time from start to completion | IssueTimes.xlsx |
| Flow Velocity | Throughput | Issues completed per time period | IssueTimes.xlsx |
| Flow Load | WIP | Issues currently in an In Progress stage, grouped by stage and age | IssueTimes.xlsx |
| Cumulative Flow Diagram | Cumulative Flow Diagram | Cumulative stage entries over time | CFD.xlsx |
| Flow Distribution | Flow Distribution | Distribution by type, stage dominance and avg cycle time | IssueTimes.xlsx |
| Process Flow: Transitions | Process Flow: Transitions | Directed graph of all status transitions (count) | Transitions.xlsx |
| Process Flow: Time | Process Flow: Time | Directed graph with node and edge width based on median dwell time | Transitions.xlsx |

## Input files

| File | Required | Description |
|------|----------|-------------|
| `IssueTimes.xlsx` | ✅ | All issues with time data per stage |
| `CFD.xlsx` | optional | Daily stage entries for the CFD |
| `Workflow.txt` | optional | `<First>` / `<Closed>` markers for CFD trend lines |
| `pi_config_example.json` | optional | Custom PI intervals for Flow Velocity |
| `Transitions.xlsx` | optional | Status transitions per issue for Process Flow |

## Architecture

```
build_reports/
├── metrics/             # Plugin registry + individual metric modules
│   ├── base.py          # MetricPlugin / MetricResult base classes
│   ├── flow_time.py
│   ├── flow_velocity.py
│   ├── flow_load.py
│   ├── cfd.py
│   ├── flow_distribution.py
│   └── process_flow.py
├── loader.py            # Load all XLSX files → ReportData
├── filters.py           # FilterConfig + apply_filters()
├── cli.py               # run_reports() + argparse CLI
├── gui.py               # tkinter GUI
├── export.py            # PDF and Excel export
└── terminology.py       # SAFe / Global terminology switching
```

The plugin system registers metrics automatically on import:

```python
from build_reports.metrics import get_metric, all_metrics
plugin = get_metric("flow_time")
result = plugin.compute(data, terminology="SAFe")
figs = plugin.render(result, "SAFe")
```

## Quick start CLI

```bash
python -m build_reports IssueTimes.xlsx --pdf report.pdf
python -m build_reports IssueTimes.xlsx --cfd CFD.xlsx --transitions Transitions.xlsx --browser
python -m build_reports IssueTimes.xlsx --metrics flow_time process_flow process_flow_time --from-date 2025-01-01
```

## Templates

The GUI supports saving and loading all settings as a JSON template (menu → Templates). Templates are versioned (`"version": 4`) and backwards-compatible.

## Data hand-over from transform_data

`build_reports` can be launched directly from `transform_data`: after a
transformation, its **Open in build_reports** button pre-fills the IssueTimes,
CFD, Transitions and workflow fields here. Internally the data is passed as a
project template via the `--gui-template <path>` command-line flag, which the
GUI loads on startup. If a project template was loaded in `transform_data`, its
build_reports settings (PI config, filters, metric selection) carry over too;
otherwise the PI config and filters remain empty for you to choose.

## Note: Flow Time Method B and workflow structure

Method B sums stage minutes **up to, but not including, the `<Closed>` stage**. Stages defined after the closed stage in the workflow (e.g. "Monitoring", "Done") are also excluded. The closed stage itself carries a carry-forward value (`reference_dt − closed_date`) for completed issues that would distort the measured cycle time — it is therefore excluded.

Method A (calendar days `First Date → Closed Date`) is not affected and is recommended as a comparison.
