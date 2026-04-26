# build_reports

Calculates flow metrics from the XLSX files produced by `transform_data` and presents the results as interactive Plotly charts in the browser or as a PDF export.

## Overview

| Property | Value |
|----------|-------|
| Status | available |
| GUI entry point | `build_reports_gui.pyw` |
| CLI entry point | `python -m build_reports` |
| User Manual (DE) | [build_reports_Benutzerhandbuch.pdf](../build_reports_Benutzerhandbuch.pdf) |
| User Manual (EN) | [build_reports_UserManual.pdf](../build_reports_UserManual.pdf) |

## Metrics

| Metric (SAFe) | Metric (Global) | Description | Required file |
|---------------|-----------------|-------------|--------------|
| Flow Time | Cycle Time | Cycle time from start to completion | IssueTimes.xlsx |
| Flow Velocity | Throughput | Issues completed per time period | IssueTimes.xlsx |
| Flow Load | WIP | Issues currently in progress by stage | IssueTimes.xlsx |
| Cumulative Flow Diagram | Cumulative Flow Diagram | Cumulative stage entries over time | CFD.xlsx |
| Flow Distribution | Flow Distribution | Distribution by type, stage dominance and avg cycle time | IssueTimes.xlsx |
| Process Flow | Process Flow | Directed graph of all status transitions | Transitions.xlsx |

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
python -m build_reports IssueTimes.xlsx --metrics flow_time process_flow --from-date 2025-01-01
```

## Templates

The GUI supports saving and loading all settings as a JSON template (menu → Templates). Templates are versioned (`"version": 4`) and backwards-compatible.
