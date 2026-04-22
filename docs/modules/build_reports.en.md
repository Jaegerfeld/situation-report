# build_reports

Reads the XLSX files produced by `transform_data` and computes flow metrics as interactive charts. Supports SAFe and Global terminology, optional filters, PDF export, and a fully localised GUI (German/English).

!!! tip "User Manual (PDF)"
    A comprehensive user manual for non-technical users is available:
    **[build_reports_Benutzerhandbuch.pdf](../build_reports_Benutzerhandbuch.pdf)**
    — covers setup, GUI walkthrough, metric explanations, FAQ, and glossary.

## Start

### GUI

```bash
python -m build_reports
```

Opens the build_reports window. Alternatively: double-click `build_reports_gui.pyw` in the project directory — opens the GUI without a console window.

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
| `--exclude-status STATUS …` | Completely exclude issues with these Jira statuses |
| `--exclude-resolution RES …` | Completely exclude issues with these resolutions |
| `--exclude-zero-day` | Exclude zero-day issues (CT below threshold) |
| `--zero-day-threshold MINUTES` | Cycle time threshold in minutes for zero-day detection (default: 5) |
| `--terminology` | Terminology mode: `SAFe` (default) or `Global` |
| `--ct-method` | CT calculation method: `A` (calendar days, default) or `B` (stage minutes) |
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

# Multiple metrics, Global terminology, CT method B
python -m build_reports.cli data/ART_A_IssueTimes.xlsx --cfd data/ART_A_CFD.xlsx \
    --metrics flow_time flow_velocity cfd \
    --terminology Global \
    --ct-method B \
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

## GUI

### Options menu

The menu bar contains two menus:

**Options**

- **Language** — Toggle between German and English; all labels, tooltips, and menu items are updated immediately.
- **Terminology** — Toggle between SAFe and Global; affects chart titles, axis labels, and metric checkboxes.

**Templates**

- **Save…** — Saves the entire current configuration (file paths, date filters, projects, issue types, terminology, CT method, metric selection, language) as a JSON file.
- **Load…** — Loads a saved configuration and populates all fields. Paths that no longer exist are shown in the log.

### Files

- **IssueTimes** — Required. After selection, projects and issue types are automatically loaded from the file (background thread). If a CFD file is already set, a stage consistency check is run at the same time.
- **CFD (optional)** — Only needed for the CFD metric. Setting it triggers the stage consistency check.

### Filters

| Field | Description |
|-------|-------------|
| From / To | Date filter on `Closed Date`. Default: last 365 days. Direct input (YYYY-MM-DD) or calendar picker (📅 button). |
| Last 365 days | Sets From and To to today − 365 days through today. |
| Projects | Comma-separated project keys, e.g. `ARTA, ARTB`. Empty = all. The ▾ button opens a selection list from the loaded file. |
| Issue types | Comma-separated issue types, e.g. `Feature, Bug`. Empty = all. The ▾ button opens a selection list. |

### Exclusions

Specific issues can be completely removed from all metrics — even if they have a Closed Date.

| Field | Description |
|-------|-------------|
| Status | Comma-separated Jira statuses, e.g. `Canceled`. The ▾ button opens a selection list. |
| Resolution | Comma-separated resolutions, e.g. `Won't Do, Duplicate`. The ▾ button opens a selection list. |
| Exclude zero-day issues | Checkbox + spinbox (1–60 min). Issues whose cycle time (First → Closed Date) is below the threshold are removed. Default: 5 minutes. |

Exclusion defaults can be saved permanently via **Templates → Save exclusions as default** and restored with **Load default exclusions**.

!!! info "Zero-day issues"
    Typical example: an issue was manually clicked through all workflow stages within seconds, without any actual development work taking place. Such issues distort flow time statistics and should be excluded using the threshold.

### Metrics and CT method

Individual metrics can be enabled or disabled via checkboxes. **All** and **None** set all checkboxes at once.

The CT method (relevant for Flow Time only) is selected via radio button:

| Method | Calculation |
|--------|-------------|
| A (default) | Calendar days: `Closed Date − First Date` |
| B | Sum of stage minutes from `First Date` to `Closed Date` (last stage excluded) |

### Stage consistency check

When IssueTimes or CFD is loaded, the stage columns of both files are compared. Discrepancies are shown in the log:

```
Stage only in IssueTimes: Review
Stage only in CFD: In Review
```

### Tooltips

All interactive elements (input fields, buttons, radio buttons, checkboxes) show an explanatory tooltip on hover. Tooltips are updated automatically when the language is switched.

## Metrics

### Flow Time / Cycle Time

**Metric ID:** `flow_time`

Computes lead time (in days) from first activity (`First Date`) to completion (`Closed Date`) for all closed issues. Issues missing either date or with a lead time of 0 days are excluded.

**CT calculation methods:**

- **Method A** (default): Difference in calendar days between `First Date` and `Closed Date`.
- **Method B**: Sum of stage minutes for all stages except the last, divided by 1440.

**Charts:**

- **Boxplot** — Distribution of lead times with a statistics header (Min, Q1, Mean, Median, Q3, Max, **90d CT%** = share of issues with CT ≤ 90 days, standard deviation, coefficient of variation, zero-day issue count).
- **Scatterplot** — Lead time per closing date with:
  - **LOESS trend line** (blue, solid) — locally weighted regression, no external dependency.
  - **Reference lines** (dotted): Median (red), 85th percentile (light green), 95th percentile (cyan).
  - **Point colour coding**: ≥ 95th percentile = red, ≥ 85th percentile = orange, below = steelblue.
  - **X-axis**: monthly ticks; odd months show an abbreviated name, even months show "·".

**Zero-day issues:**

Two mechanisms apply independently:

1. **Before metric computation (exclusion filter):** Issues whose cycle time (First → Closed Date) is below the configured threshold (default: 5 minutes) are completely removed from all metrics — when the checkbox in the Exclusions section is active.
2. **Within the metric:** Issues with a lead time ≤ 0 days (e.g. same calendar day) are removed from the calculation and reported separately.

- **PDF export**: Automatically saved as `<reportname>_zero_day_issues.xlsx` in the same folder (when issues are present).
- **Browser display**: Issue keys are listed in the log window.

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

Reads the daily entry counts from `CFD.xlsx` and accumulates them cumulatively. Shows how many issues have entered each stage in total up to a given day.

**Chart:** Stacked area chart (first stage on top) with two trend lines (inflow/outflow) and the In/Out ratio in the title. The chart always starts at 0 — regardless of the selected start date.

- **Upper trend line** — runs from the cumulative total inflow on the first to the last day.
- **Lower trend line** — runs from the cumulative value of the last stage (e.g. "Done" / "Closed") on the first to the last day.
- **X-axis** — month boundaries are labelled prominently (e.g. "Jan 2025"); ISO calendar-week Mondays are shown small and in grey (e.g. "W03") to prevent label overlap.

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
| From date | "From" field, 📅 button, or "Last 365 days" | `--from-date` |
| To date | "To" field, 📅 button, or "Last 365 days" | `--to-date` |
| Projects | "Projects" field (comma-separated) or ▾ selection | `--projects` |
| Issue types | "Issue types" field (comma-separated) or ▾ selection | `--issuetypes` |
| Status exclusion | Exclusions → Status (comma-separated) or ▾ selection | `--exclude-status` |
| Resolution exclusion | Exclusions → Resolution (comma-separated) or ▾ selection | `--exclude-resolution` |
| Zero-day exclusion | Exclusions → checkbox + threshold (minutes) | `--exclude-zero-day` / `--zero-day-threshold` |

- The date filter applies to the `Closed Date` of issues.
- Issues without a `Closed Date` are excluded when a date range is set.
- Excluded issues (status, resolution, zero-day) are removed **before** metric computation and do not appear in any output.
- CFD data is filtered by date only (no project or issue type dimension).
- Default date range: the last 365 days up to today.

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

All charts are written to a combined HTML file in a temporary location and opened in the default browser. Charts are fully interactive (zoom, pan, hover tooltips, legend toggle). Each metric receives a heading in the HTML document.

### PDF export

```bash
python -m build_reports.cli <xlsx> --pdf report.pdf
```

- A single chart is exported directly as a PDF.
- Multiple charts are merged into a multi-page PDF using `pypdf`.
- Export uses `kaleido` for rasterisation (run `choreo_get_chrome` once if kaleido has not yet located its Chrome binary).
- If zero-day issues are present, `report_zero_day_issues.xlsx` is automatically created in the same folder.
- A **report Excel file** with the same filename (extension `.xlsx`) is always created alongside the PDF.

### Report Excel

Every PDF export automatically produces an XLSX file (`<reportname>.xlsx`). It contains all filtered issues in IssueTimes format, extended by three additional columns:

| Column | Content |
|--------|---------|
| `Status Group` | Status group of the issue: `To Do`, `In Progress`, or `Done` (derived from `First Date` and `Closed Date`) |
| `Cycle Time (First->Closed)` | Lead time in calendar days (`Closed Date − First Date`); empty when either date is missing |
| `Cycle Time B (days in Status)` | Sum of stage minutes (all stages except the last) divided by 1440; empty when either date is missing |

### Zero-day issues Excel

The exported file contains the same columns as IssueTimes (Project, Key, Issuetype, Status, Dates, Resolution), sorted by project and key. The filename is derived automatically from the PDF name.

## Plugin system

New metrics can be added as a standalone module inside `build_reports/metrics/`:

```python
# build_reports/metrics/my_metric.py
from build_reports.metrics.base import MetricPlugin, MetricResult
from build_reports.metrics import register
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
