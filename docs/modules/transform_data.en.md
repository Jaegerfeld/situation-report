# transform_data

Reads a Jira JSON export and a workflow definition and produces three XLSX files with stage-time metrics.

!!! tip "User Manual (PDF)"
    A detailed user manual for non-technical users is available:
    **[transform_data_Benutzerhandbuch.pdf](../transform_data_Benutzerhandbuch.pdf)**

## Start

### GUI

```bash
python -m transform_data
```

Opens a window with file selection dialogs. When a JSON file is chosen, the output folder and prefix are automatically pre-filled. Warnings and results appear in the log area.

```bash
python -m transform_data.gui
```

Launches the GUI directly (without argument checking).

Alternatively: double-click `start_gui.pyw` in the project directory — opens the GUI without a console window.

### Command line

```bash
python -m transform_data <json_file> <workflow_file> [options]
python -m transform_data.transform <json_file> <workflow_file> [options]
```

Both variants are equivalent. The second (`transform_data.transform`) is always a pure CLI call, regardless of the number of arguments.

**Arguments**

| Argument | Description |
|----------|-------------|
| `json_file` | Jira JSON export (required) |
| `workflow_file` | Workflow definition file (required) |
| `--output-dir` | Output directory (default: directory of the JSON file) |
| `--prefix` | Output file prefix (default: stem of the JSON filename) |

**Example**

```bash
python -m transform_data data/ART_A.json data/workflow_ART_A.txt --output-dir out/ --prefix ART_A
```

Produces:

- `out/ART_A_Transitions.xlsx`
- `out/ART_A_IssueTimes.xlsx`
- `out/ART_A_CFD.xlsx`

### Overview

| Command | Result |
|---------|--------|
| `python -m transform_data` | GUI |
| `python -m transform_data <json> <workflow>` | CLI |
| `python -m transform_data.gui` | GUI (direct) |
| `python -m transform_data.transform <json> <workflow>` | CLI (direct) |
| `python -m transform_data --help` | CLI help |
| Double-click `start_gui.pyw` | GUI without console window |

## Workflow definition file

Text file, one stage per line.

```
Funnel:New:Open
Analysis:In Analysis
Implementation:In Progress
Done:Canceled
<First>Analysis
<InProgress>Implementation
<Closed>Done
```

| Format | Meaning |
|--------|---------|
| `Stage` | Canonical stage name |
| `Stage:Alias1:Alias2` | Stage with Jira status names mapped to it |
| `<First>Stage` | This stage sets the "First Date" |
| `<InProgress>Stage` | This stage sets the "Implementation Date" (default: stage named "Implementation") |
| `<Closed>Stage` | This stage sets the "Closed Date" |

### Workflow file validation

The following checks are performed when loading the workflow file:

| Situation | Behaviour |
|-----------|-----------|
| `<First>` / `<Closed>` not defined | Warning: date column stays empty |
| Stage name in marker does not exist in the file | **Error** with list of valid stage names |
| Stage defined but never reached by any issue | No intervention — date column stays empty |

### Unmapped Jira statuses

If the Jira export contains statuses that are not defined as a stage or alias in the workflow file, the tool issues a warning:

```
WARNING: 2 statuses in the data are not mapped in the workflow file:
  - To Do
  - Unknown
  > Time in these statuses is attributed to the last known stage.
```

Time spent in unmapped statuses is attributed to the **last known stage** (carry-forward). Issues remain fully present in all outputs.

## Output files

### Transitions.xlsx

One row per status change per issue, sorted chronologically.

| Column | Content |
|--------|---------|
| Key | Issue key |
| Transition | Stage name (or "Created") |
| Timestamp | Time of the transition |

### IssueTimes.xlsx

One row per issue with time spent (in minutes) per stage.

| Column | Content |
|--------|---------|
| Project, Key, Issuetype, Status, … | Issue master data |
| Created Date | Creation timestamp |
| First Date | First entry into the `<First>` stage |
| Implementation Date | First entry into the `<InProgress>` stage |
| Closed Date | Last entry into the `<Closed>` stage |
| *Stage columns* | Minutes spent in the respective stage |
| Resolution | Jira resolution |

### CFD.xlsx

Cumulative Flow Diagram — one row per calendar day. Stage columns contain the number of issues in each stage on that day.

## Stage-time calculation

- Time from issue creation to the first explicit transition is attributed to the initial stage.
- Unmapped initial statuses fall back to the first stage in the workflow definition.
- When a transition targets an unmapped status, time continues to accumulate in the **last known stage** (carry-forward).
- The last known stage accumulates time until the execution time.
- Issues without transitions have zero for all stages.

!!! info "Closed Date"
    The Closed Date is set on the **last** entry into the `<Closed>` stage. For issues that were reopened and closed again, the most recent closing timestamp is used.

!!! info "Skipped Closed Stage"
    If an issue has a First Date but the `<Closed>` stage was skipped (e.g. a direct transition from Implementation to Done), the **first stage chronologically after the Closed stage** in the workflow order is used as the Closed Date. This ensures that issues where development took place but a status was skipped are correctly counted as closed. Issues without a First Date (e.g. cancelled before development started) receive no Closed Date.

## Tests

```bash
python -m pytest tests/transform_data/
```

| Type | Directory | Content |
|------|-----------|---------|
| Unit | `tests/transform_data/unit/` | Isolated tests for `workflow.py` and `processor.py` with synthetic fixtures |
| Acceptance | `tests/transform_data/acceptance/` | Tests against the real ART_A dataset; verify business correctness |
