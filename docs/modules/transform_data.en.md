# transform_data

Reads a Jira JSON export and a workflow definition and produces three XLSX files with stage-time metrics.

## Start

### GUI

```bash
python -m transform_data
```

Opens a window with file selection dialogs. When a JSON file is chosen, the output folder and prefix are automatically pre-filled.

```bash
python -m transform_data.gui
```

Launches the GUI directly (without argument checking).

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

### Overview

| Command | Result |
|---------|--------|
| `python -m transform_data` | GUI |
| `python -m transform_data <json> <workflow>` | CLI |
| `python -m transform_data.gui` | GUI (direct) |
| `python -m transform_data.transform <json> <workflow>` | CLI (direct) |
| `python -m transform_data --help` | CLI help |

## Workflow definition file

Text file, one stage per line.

```
Funnel:To Do
Analysis
Implementation
<First>Analysis
<InProgress>Implementation
<Closed>Done
Done
```

| Format | Meaning |
|--------|---------|
| `Stage` | Canonical stage name |
| `Stage:Alias1:Alias2` | Stage with Jira status names mapped to it |
| `<First>Stage` | This stage sets the "First Date" |
| `<InProgress>Stage` | This stage sets the "Implementation Date" |
| `<Closed>Stage` | This stage sets the "Closed Date" |

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
| Closed Date | First entry into the `<Closed>` stage |
| *Stage columns* | Minutes spent in the respective stage |
| Resolution | Jira resolution |

### CFD.xlsx

Cumulative Flow Diagram — one row per calendar day. Stage columns contain the number of issues in each stage on that day.

## Stage-time calculation

- Time from issue creation to the first explicit transition is attributed to the initial stage.
- Unmapped initial statuses fall back to the first stage in the workflow definition.
- The last stage accumulates time until the execution time (`reference_dt`).
- Issues without transitions have zero for all stages.
