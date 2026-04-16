# build_reports

Reads the XLSX files produced by `transform_data` and computes flow metrics as interactive charts. Supports SAFe and Global terminology, optional filters, and PDF export.

## Start

### GUI

```bash
python -m build_reports
```

Opens the build_reports window with file selection, filter fields, metric checkboxes, and a terminology toggle. Charts are displayed in the default browser as interactive HTML. PDF export opens a save dialog.

Alternatively: double-click `build_reports_gui.pyw` in the project directory — opens the GUI without a console window.

### Command line

```bash
python -m build_reports.cli <IssueTimes.xlsx> [options]
```

**Arguments**

| Argument | Description |
|----------|-------------|
| `IssueTimes.xlsx` | Output file from `transform_data` (required) |
| `--cfd CFD.xlsx` | CFD output file (required for the CFD metric) |
| `--metrics ID …` | Select metrics to compute (default: all) |
| `--from-date YYYY-MM-DD` | Include only issues closed on or after this date |
| `--to-date YYYY-MM-DD` | Include only issues closed on or before this date |
| `--projects KEY …` | Restrict to these project keys |
| `--issuetypes TYPE …` | Restrict to these issue types |
| `--terminology` | Terminology mode: `SAFe` (default) or `Global` |
| `--pdf FILE` | Export all charts to this PDF file |
| `--browser` | Open charts in the default browser |

**Examples**

```bash
# All metrics, save PDF
python -m build_reports.cli data/ART_A_IssueTimes.xlsx --cfd data/ART_A_CFD.xlsx --pdf report.pdf

# Flow Time only, date filter, browser display
python -m build_reports.cli data/ART_A_IssueTimes.xlsx \
    --metrics flow_time \
    --from-date 2025-01-01 --to-date 2025-12-31 \
    --browser

# Multiple metrics, Global terminology
python -m build_reports.cli data/ART_A_IssueTimes.xlsx --cfd data/ART_A_CFD.xlsx \
    --metrics flow_time flow_velocity cfd \
    --terminology Global \
    --pdf quarterly_report.pdf
```

### Overview

| Command | Result |
|---------|--------|
| `python -m build_reports` | GUI |
| `python -m build_reports.cli <xlsx> --browser` | CLI, browser display |
| `python -m build_reports.cli <xlsx> --pdf out.pdf` | CLI, PDF export |
| `python -m build_reports.cli --help` | CLI help |
| Double-click `build_reports_gui.pyw` | GUI without console window |

## Metrics

### Flow Time / Cycle Time

**Metric ID:** `flow_time`

Computes lead time (in days) from first activity (`First Date`) to completion (`Closed Date`) for all closed issues. Issues missing either date or with a lead time of 0 days are excluded.

**Charts:**

- **Boxplot** — Distribution of lead times with a statistics header (median, mean, min, max, 90th percentile, coefficient of variation)
- **Scatterplot** — Lead time per closing date with a trend line and reference lines (median, 85th and 95th percentile)

| SAFe | Global |
|------|--------|
| Flow Time | Cycle Time |

---

### Flow Velocity / Throughput

**Metric ID:** `flow_velocity`

Counts completed issues (with `Closed Date`) per time period.

**Charts:**

- **Daily frequency** — Histogram: how many issues are typically completed on a single day
- **Weekly trend** — Line chart of weekly completions (format `YYYY.WW`)
- **PI trend** — Bar chart of completions per PI (ISO calendar week) with an average line

| SAFe | Global |
|------|--------|
| Flow Velocity | Throughput |

---

### Flow Load / WIP

**Metric ID:** `flow_load`

Analyses **open** issues (without `Closed Date`) by their current stage and age (days since `First Date` or creation date).

**Chart:** Grouped boxplot with individual data points, broken down by current stage. Reference lines derived from closed issues (mean, median, 85th and 95th percentile of lead time) provide context for the age of open work.

| SAFe | Global |
|------|--------|
| Flow Load | WIP |

---

### Cumulative Flow Diagram

**Metric ID:** `cfd`

Reads the daily stage counts from `CFD.xlsx`. Shows the state of the system over time.

**Chart:** Stacked area chart (first stage on top) with two trend lines (inflow/outflow) and the In/Out ratio in the title.

| SAFe | Global |
|------|--------|
| Cumulative Flow Diagram | Cumulative Flow Diagram |

---

### Flow Distribution

**Metric ID:** `flow_distribution`

Shows the composition of the issue backlog by issue type and current status.

**Chart:** Two donut pie charts side by side — left by issue type, right by status.

| SAFe | Global |
|------|--------|
| Flow Distribution | Flow Distribution |

---

## Filters

Filters can be set in the GUI via input fields or passed as CLI arguments.

| Filter | GUI | CLI |
|--------|-----|-----|
| From date | "Von (YYYY-MM-DD)" field | `--from-date` |
| To date | "Bis (YYYY-MM-DD)" field | `--to-date` |
| Projects | "Projekte" field (comma-separated) | `--projects` |
| Issue types | "Issuetypen" field (comma-separated) | `--issuetypes` |

- The date filter applies to the `Closed Date` of issues.
- Issues without a `Closed Date` are excluded when a date range is set.
- CFD data is filtered by date only (no project or issue type dimension).

## Terminology

All metric labels can be switched between SAFe and Global. The switch affects chart titles, axis labels, and legends.

| Metric ID | SAFe | Global |
|-----------|------|--------|
| `flow_time` | Flow Time | Cycle Time |
| `flow_velocity` | Flow Velocity | Throughput |
| `flow_load` | Flow Load | WIP |
| `cfd` | Cumulative Flow Diagram | Cumulative Flow Diagram |
| `flow_distribution` | Flow Distribution | Flow Distribution |

## Export

### Browser display

All charts are written to a combined HTML file in a temporary location and opened in the default browser. Charts are fully interactive (zoom, pan, hover tooltips, legend toggle).

### PDF export

```bash
python -m build_reports.cli <xlsx> --pdf report.pdf
```

- A single chart is exported directly as a PDF.
- Multiple charts are merged into a multi-page PDF using `pypdf`.
- Export uses `kaleido` for rasterisation (run `choreo_get_chrome` once if kaleido has not yet located its Chrome binary).

## Plugin system

New metrics can be added as a standalone module inside `build_reports/metrics/`:

```python
# build_reports/metrics/my_metric.py
from build_reports.metrics.base import MetricPlugin, MetricResult, register
import plotly.graph_objects as go

class MyMetric(MetricPlugin):
    metric_id = "my_metric"

    def compute(self, data, terminology):
        # computation ...
        return MetricResult(metric_id=self.metric_id, stats={}, chart_data={})

    def render(self, result, terminology):
        fig = go.Figure(...)
        return [fig]

register(MyMetric())
```

Then add the import in `build_reports/metrics/__init__.py` — the new metric will automatically appear in both the GUI and the CLI.

## Tests

```bash
python -m pytest tests/build_reports/
```

| Type | Directory | Content |
|------|-----------|---------|
| Unit | `tests/build_reports/unit/` | Isolated tests for each module using synthetic fixtures; kaleido is mocked |
| Acceptance | `tests/build_reports/acceptance/` | Tests against the real ART_A dataset; verify business correctness of metrics, export, and GUI input handling |
