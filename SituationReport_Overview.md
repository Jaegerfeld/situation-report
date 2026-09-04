# SituationReport – Overview for Beginners

**Version 0.13.0** | Created: 2026-05-03 | Updated: 2026-05-17

This document summarises all parts of SituationReport and explains them in
plain language. Technical details from the original documentation have been
simplified or omitted.

> **📖 Note on explanations:**
> Sections that start with this symbol are additional explanations for
> non-technical readers and are not part of the original documentation.

---

## What is SituationReport?

SituationReport is a toolsuite that draws a **situational picture** of large
solutions and portfolios: how work actually flows, where it stalls, what is at
risk — and what changed since the last look. The flow metrics come from the
project management tool **Jira**; alongside them the suite keeps governance
registers (capabilities, risks, NFRs, dependencies, decisions, service levels
and delivery performance), prepares the Value Stream Conference, forecasts
delivery dates, and can have a language model draft the accompanying narrative.
The software runs locally on your own computer — no data is uploaded to any
cloud, and the language model is local by default too.

> **📖 Explanation:**
> Jira is a widely used tool in which teams manage their tasks (called
> "issues" or "tickets"). Each task moves through several stages, for
> example: Backlog → In Progress → In Review → Done. SituationReport reads
> this data and computes how fast and how evenly a team works.

The project was created as an experiment in AI-assisted software development.
More than 98% of the code was written by Claude (Anthropic).

---

## How the tools work together

The typical workflow looks like this:

```
[Jira export]  →  (Helper)  →  Transform Data  →  Build Reports
                   optional
                 (multiple
                  files)
```

1. **Jira export:** The data is exported from Jira as a file.
2. **Helper** *(optional)*: If there are multiple export files, they are
   merged into a single one with the Helper tool.
3. **Transform Data:** The raw data is processed and turned into structured
   tables.
4. **Build Reports:** Charts and reports are generated from the tables.

> **📖 Explanation:**
> Think of the workflow as a funnel: first the raw data comes out of Jira
> (unstructured, large), then it is sorted and summarised (Transform Data),
> and at the end you get finished reports with charts (Build Reports).

There are also two helper tools for everyday use:

- **Testdata Generator:** Generates synthetic test data so you can try out
  the software without needing real project data.
- **Launcher:** The start window from which all tools are opened.

---

## Installation and start

### Download

All available versions are on the
[GitHub Releases page](https://github.com/Jaegerfeld/situation-report/releases).
There are stable versions (e.g. `v0.13.0`) and development builds
(`dev-latest`). For regular use, always pick the **latest stable version**.

> **📖 Explanation:**
> A "release" is a published, tested version of the software. "Dev build"
> means the latest development state, which has not been fully tested and
> may therefore contain new, possibly broken functionality.

### Windows

1. Download `SituationReport-Windows.zip`
2. Extract the zip (right-click → *Extract All*)
3. Double-click `SituationReport.bat` → the start window opens

> **📖 Explanation:**
> On the first launch, Windows SmartScreen may show a security warning.
> This is normal because the software is not certified by Microsoft. Click
> **More info → Run anyway**. The Windows package already bundles Python and
> Chrome — nothing needs to be installed separately.

### macOS

1. Download and extract `SituationReport-macOS-ARM.zip`
2. *Right-click* `SituationReport.command` → *Open* → confirm *Open* again
   in the dialog (needed once)
3. On the first launch a Python environment is set up automatically
   (~1 minute, internet connection required)

### Linux

1. Download and extract `SituationReport-Linux.zip`
2. In the terminal: `./SituationReport.sh`
3. On the first launch a Python environment is set up automatically
   (~1 minute, internet connection required)

---

## The Launcher: the start window

The launcher is the central start window of SituationReport. It shows all
available and planned tools as tiles.

```
┌──────────────────────────────────────────┐
│  SituationReport  v0.13.0  BETA    ?  🌐 │
├──────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐       │
│  │  🔄  BETA    │ │  📊  BETA    │       │
│  │Transform Data│ │ Build Reports│       │
│  │  [Launch]    │ │  [Launch]    │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────┐ ┌──────────────┐       │
│  │  📥          │ │  🎲          │       │
│  │  Get Data    │ │   Simulate   │       │
│  │(coming soon) │ │(coming soon) │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────┐ ┌──────────────┐       │
│  │  🧪  BETA    │ │  🔧  ALPHA   │       │
│  │Testdata Gen. │ │   Helper     │       │
│  │  [Launch]    │ │  [Launch]    │       │
│  └──────────────┘ └──────────────┘       │
└──────────────────────────────────────────┘
```

**What the tiles show:**

| Tile | Status | Meaning |
|------|--------|---------|
| Transform Data | BETA | Available, stable |
| Build Reports | BETA | Available, stable |
| Get Data | *(coming soon)* | Not finished yet |
| Simulate | *(coming soon)* | Not finished yet |
| Testdata Generator | BETA | Available, stable |
| Helper | ALPHA | Available, experimental |

> **📖 Explanation of maturity levels:**
> - **BETA** (orange): The tool is finished and suitable for production use.
>   Minor bugs may still occur.
> - **ALPHA** (red): The tool basically works but is still new and may
>   still change.
> - **No badge / "coming soon"**: The tool is still being planned and is
>   not usable yet.

Clicking **Launch** opens the selected tool in its own window. The launcher
stays open.

**Other launcher features:**

- **? (question mark):** Opens the user manual in the browser
- **🌐 (flag):** Switches the language (English → German → Romanian →
  Portuguese → French → English …)
- **Yellow update banner:** Appears automatically when a newer version is
  available on GitHub, with a download link

---

## Transform Data: preparing the data

Transform Data reads a Jira export and a workflow description and produces
three structured tables (Excel files) that Build Reports processes further.

> **📖 Explanation:**
> Jira stores all information about a task (when it was created, which
> stages it went through, how long it stayed where) internally as a list of
> events. Transform Data reads this event list and computes: how much time
> did the task spend in each stage? The result is clean tables you can look
> at directly in Excel or analyse with Build Reports.

### What is needed?

1. **Jira JSON export:** A file with the task data from Jira
2. **Workflow file:** A simple text file describing which stages (statuses)
   exist in this project

> **📖 Explanation of the workflow file:**
> The workflow file is needed because Jira projects can be set up very
> differently. One project might have the stages
> "Backlog → In Analysis → In Development → Done", another completely
> different names. The workflow file tells the program what the stages are
> called in this specific project and in what order they occur. It also
> defines which stage marks the start of active work (`<First>`) and which
> stage marks the end (`<Closed>`).

Example of a workflow file:
```
Funnel
Analysis:In Analysis
Implementation:In Progress
Done:Canceled
<First>Analysis
<Closed>Done
```

### What is produced?

| File | Contents |
|------|----------|
| `*_IssueTimes.xlsx` | One row per task with the time (in minutes) in each stage |
| `*_Transitions.xlsx` | One row per status change per task, chronological |
| `*_CFD.xlsx` | Daily entry counts per stage (basis for the CFD chart) |

> **📖 Explanation of the output files:**
> - **IssueTimes** is the most important file. For each task it shows
>   exactly when it was created, when work on it started, when it was
>   completed — and how much time it spent in each stage.
> - **Transitions** is the full log of all status changes. Useful when you
>   want to trace exactly when something happened.
> - **CFD** contains the data for the Cumulative Flow Diagram — a special
>   kind of chart that shows how many tasks flowed through the system over
>   time.

### Special cases

- **Unmapped statuses:** If a Jira status does not appear in the workflow
  file, a warning is issued. The time spent in that status is attributed to
  the last known stage.
- **Skipped stages:** If a task skipped a stage, Transform Data detects this
  automatically and handles it correctly.

> **📖 Explanation:**
> In practice it sometimes happens that a task skipped a stage (for example
> moving directly from "In Analysis" to "Done" without going through
> "In Development"). Transform Data recognises such cases and still computes
> meaningful values.

---

## Build Reports: creating reports

Build Reports reads the tables produced by Transform Data and creates
interactive charts and reports from them. The charts can be shown in the
browser or exported as PDF.

> **📖 Explanation:**
> Build Reports is the "analysis tool". It answers questions like: how long
> does it take on average until a task is finished? How many tasks are
> completed per week? How many tasks are currently in progress at the same
> time? The answers are presented as charts.

### Filters and settings

Before the reports are created, you can restrict the data:

| Setting | Meaning |
|---------|---------|
| From / To | Only consider tasks that were completed in this period |
| Projects | Only analyse certain Jira projects |
| Issue types | Only certain task types (e.g. only "Feature", not "Bug") |
| Status exclusion | Completely ignore tasks with certain statuses (e.g. "Canceled") |
| Zero-day exclusion | Ignore tasks that went through all stages too quickly (probably test tasks or errors) |

> **📖 Explanation of zero-day issues:**
> Sometimes there are tasks that were moved through all stages within
> seconds — for example because someone created a task only for testing and
> immediately closed it again. These "zero-day tasks" would distort the
> statistics and can therefore be filtered out.

Configurations can be saved as a **template** and loaded again later —
useful when you regularly create the same report. Since v0.11.0 there is a
**shared project template** for all GUI modules: a single file holds one
section per module, so the pipeline configuration (workflow, paths, project,
date range) only has to be set once and can be reused everywhere.

### The metrics (charts)

#### Flow Time / Cycle Time — how long does a task take?

> **📖 Explanation:**
> This metric answers the question: "How long does it take from the moment
> we start working on a task until it is finished?" This is one of the most
> important figures for a team — it shows whether the process is fast or
> slow and whether it is predictable.

**Two charts:**

- **Boxplot:** Shows the distribution of all lead times. How wide the box
  is shows how varied (unpredictable) the times are. The header shows key
  figures: minimum, maximum, average, median, and the share of tasks
  completed in 90 days or less.

  > **📖 Explanation of the boxplot:**
  > A boxplot is a compact representation of a distribution. The box
  > encloses the middle 50% of the values. The line in the middle is the
  > median (the middle value). The "whiskers" show the range in which most
  > values lie. The narrower the box and the shorter the whiskers, the more
  > predictable the process.

- **Scatter plot:** Shows every single completion as a dot on a time axis.
  Colour coding: red dots = particularly slow, orange = above-average slow,
  blue = normal. A trend line (blue) shows whether times are improving or
  worsening over time.

  > **📖 Explanation of the reference lines:**
  > The scatter plot has three horizontal lines:
  > - **Median (red):** 50% of the tasks were faster, 50% slower.
  > - **P85 (light green):** 85% of the tasks were faster than this value.
  > - **P95 (cyan):** 95% of the tasks were faster.
  > These lines help with forecasting: "If we start a task today, when will
  > it be finished with 85% probability?"

#### Flow Velocity / Throughput — how many tasks get done?

> **📖 Explanation:**
> This metric answers the question: "How many tasks does the team complete
> per week or month?" A stable, high throughput is a sign of a well-running
> process.

**Three charts:**

- **Daily frequency:** How many tasks are typically completed on a single
  day? (Most teams complete several tasks on some days, none on others.)
- **Weekly trend:** Line chart of the weekly completions — shows trends and
  fluctuations over time.
- **PI trend:** Bar chart of completions per Planning Interval (SAFe term
  for a larger planning cycle).

  > **📖 Explanation of PI:**
  > In SAFe (Scaled Agile Framework), quarters are divided into "Program
  > Increments" (PIs) — typically 8–12 weeks each with several sprints. The
  > PI trend shows how productive the team was in each PI.

#### Flow Load / WIP — how many tasks are in progress right now?

> **📖 Explanation:**
> WIP stands for "Work in Progress" — tasks that have been started but are
> not yet finished. Too many tasks in progress at the same time slow down
> the process (everyone is busy, but nothing moves forward). This metric
> shows the current state.

**One chart:** Grouped boxplot of all running tasks, split by stage. The age
of each task (days since work started) is visible. Reference lines from the
historical completion data provide context: tasks running longer than the
median or the 85th percentile may be blocked.

> **📖 Explanation:**
> Flow Load shows a "snapshot" of the system: which tasks are currently
> where? And how long have they been there? Tasks that stay in a stage very
> long can indicate a problem — for example a bottleneck or a blockage.

#### Cumulative Flow Diagram (CFD) — how does the work flow?

> **📖 Explanation:**
> The CFD is one of the most informative visualisations in agile project
> management. For each day it shows how many tasks in total entered each
> stage. From the shape of the chart you can read: is the system running
> evenly? Are tasks piling up in a certain stage? Is enough being completed?

**One chart:** Stacked area chart. The width between the upper and lower
trend line shows the average lead time (the wider, the longer). A shrinking
width means: the team is getting faster. A growing width means: the process
is slowing down.

#### Flow Distribution — what is the team working on?

> **📖 Explanation:**
> This metric shows the composition of the work. What percentage are new
> features? How much are bugs? Which stage occupies the team the most? Where
> do tasks spend the most time?

**Three charts:**

- **By Issue Type:** Pie chart — what shares do the different task types
  (Feature, Bug, Enabler …) have?
- **Stage Prominence:** Pie chart — in which stage do tasks spend the most
  time? This shows where the actual focus of the work lies.
- **Avg Cycle Time by Type:** Bar chart — do features take longer than
  bugs? This view shows the average lead time per task type.

### Terminology

Build Reports supports two different naming systems:

| SAFe term | General term |
|-----------|--------------|
| Flow Time | Cycle Time |
| Flow Velocity | Throughput |
| Flow Load | WIP (Work in Progress) |

> **📖 Explanation:**
> Depending on the team's or company's context, these concepts are named
> differently. In SAFe (a common agile framework) it is called "Flow Time",
> in other contexts "Cycle Time". The same thing is meant. Switching only
> affects the labels in the charts.

### Export

- **Browser:** All charts are opened in an HTML file in the browser. There
  they are interactive (zoom, tooltip on hover, toggle legend).
- **PDF:** All charts are combined into a multi-page PDF. At the same time
  an Excel file with all analysed tasks is created automatically.

---

## Helper: merging files

The Helper module currently contains one tool: the **JSON Merger**.

> **📖 Explanation — the problem:**
> Jira can export a maximum of 1,000 tasks at a time. If a project has more
> than 1,000 tasks, you have to perform several exports — and end up with
> several files. Transform Data, however, expects a single file. The Helper
> solves this problem: it takes all export files and merges them into one.

### What the JSON Merger does

1. All specified Jira JSON files are read
2. The tasks from all files are combined
3. Duplicate tasks (by task ID) are removed automatically (deduplication)
4. The result is a single file that can be processed directly by Transform
   Data

> **📖 Explanation of deduplication:**
> When you run several Jira exports with overlapping time ranges, the same
> task may appear in multiple files. The Helper detects this and removes
> the duplicates automatically. A message is shown in the log for each
> detected duplicate.

### User interface

```
Input files
┌─────────────────────────────────┐
│ /path/to/export_0.json          │
│ /path/to/export_1000.json       │
│ /path/to/export_2000.json       │
└─────────────────────────────────┘
[Add…]  [Remove]

Output file (JSON)
[/path/to/merged.json    ] [Browse…]

☑ Remove duplicates

         [Merge]
```

---

## Testdata Generator: creating test data

The Testdata Generator produces synthetic Jira data that matches the real
Jira format. The generated files can be processed directly with Transform
Data and Build Reports.

> **📖 Explanation — what is this useful for?**
> You can try out SituationReport without needing real project data. The
> Testdata Generator is also useful for training, demonstrations or testing
> new functionality. The generated data looks realistic: there are tasks
> that finished quickly, others that took very long, some that are still
> open — just like in a real project.

### Configurable parameters

| Parameter | Meaning |
|-----------|---------|
| Workflow file | Which stages should the tasks go through? |
| Project key | What should the task IDs be called (e.g. "DEMO-1", "DEMO-2"…)? |
| Number of tasks | How many tasks should be generated? |
| Date range | Between which dates should the tasks have been created? |
| Issue types | What share should be Feature, Bug, Enabler etc.? |
| Completion rate | What percentage of tasks should already be completed? |
| Backflow probability | How often should a task jump back to an earlier stage? |
| Seed | A number that always produces exactly the same data (for reproducible tests) |
| Mean cycle time | Average lead time in days (lognormally distributed) |
| Standard deviation | Spread of the cycle time |
| Flow pattern | Which anti-pattern should be simulated? (Triangle, Flat Triangle, Cluster, Batch) |
| PI cycle length | Length of a Program Increment in weeks (for cluster/batch patterns) |

> **📖 Explanation of the seed:**
> Normally the generated data is random. With a seed (any number, e.g.
> "42") the randomness is fixed: whoever uses the same seed always gets
> exactly the same data. This is useful when you want to make sure that a
> test always runs with the same data.

### Flow anti-pattern shapes (new in v0.9.9)

The Testdata Generator can simulate typical problems from agile process
monitoring:

| Pattern | What it shows | What it is useful for |
|---------|---------------|-----------------------|
| **Triangle** | Cycle time rises continuously over time — the team gets slower and slower | Detecting gradual process degradation |
| **Flat Triangle** | Like Triangle, but the increase flattens towards the end | Shows a process that stabilises but at a high level |
| **Cluster of Dots** | Many deliveries cluster just before the PI end — in normal time | Shows deadline-driven behaviour, batching at the PI end |
| **Batch Transfers** | Like Cluster, but with very different cycle times | Shows that short and very long tasks are delivered together at the PI end |

> **📖 Explanation of flow anti-patterns:**
> Daniel Vacanti and Prateek Singh described typical patterns that indicate
> problems in the agile process. The Triangle pattern means: over time
> every task takes longer — a sign that the process is being overloaded.
> The Cluster pattern means: the team does not deliver evenly but collects
> tasks and pushes them through just before the PI end — which leads to
> unnecessary stress and lower quality.

### Direct report (new in v0.12.0)

After a successful generation, the **"Create Report"** button becomes
active in the GUI. One click runs Transform Data and Build Reports directly
and opens a combined report (a single HTML page with all metrics) in the
browser, covering the entire generated date range — no date filter needed.

---

## Planned modules (not available yet)

### Get Data — direct Jira retrieval

This module is still being planned. It is intended to fetch data directly
via the Jira REST API — without a manual export.

> **📖 Explanation:**
> Currently you have to export data manually from Jira (download it as a
> file). Once Get Data is finished, SituationReport can fetch the data from
> Jira itself — you only enter which project you want to analyse and the
> program retrieves the data automatically.

**Workaround until it is finished:** Export Jira data manually, merge with
the Helper if needed, then process with Transform Data.

### Simulate — forecasts and predictions

This module is still being planned. Based on historical data it is intended
to enable forecasts — for example: "When will we likely be finished with
this amount of tasks?"

> **📖 Explanation:**
> With historical data (how long has the team needed so far?) you can make
> predictions using statistical methods. For example: "We still have 20
> tasks open. If we historically complete 3 per week, we will be done in 7
> weeks — with 85% probability even within 9 weeks." These forecasts are
> more honest than classic estimates because they are based on real
> measurement data.

---

## Version history (summary)

| Version | Date | Key changes |
|---------|------|-------------|
| **0.13.0** | 2026-05-17 | English as the default language (docs site, changelog, GUI default) |
| 0.12.1 | 2026-05-17 | Testdata Generator promoted from Alpha to Beta |
| 0.12.0 | 2026-05-17 | Testdata Generator: direct combined report in the browser |
| 0.11.0 | 2026-05-16 | Shared project template for all GUI modules |
| 0.9.9 | 2026-05-13 | Testdata Generator: flow anti-patterns (Triangle, Flat Triangle, Cluster, Batch), lognormal cycle time |
| 0.9.8 | 2026-05-09 | Pixel flag buttons in all GUIs |
| 0.9.0 | 2026-05-03 | Helper module (JSON Merger) |
| 0.8.5 | 2026-05-02 | Testdata Generator, BETA badge for stable modules |
| 0.8.4 | 2026-04-30 | Manuals in Romanian, Portuguese, French |
| 0.8.3 | 2026-04-30 | Scrollable form in Build Reports |
| 0.8.1 | 2026-04-30 | Automatic update notification in the launcher |
| 0.8.0 | 2026-04-30 | Launcher GUI, double-click start scripts |
| 0.7.0 | 2026-04-30 | Process Flow metric, CI/CD release workflow |
| 0.5.0 | 2026-04-26 | Process Flow chart |
| 0.4.0 | 2026-04-26 | Bilingual GUIs (DE/EN) |
| 0.2.0 | 2026-04-25 | First official SemVer version |

> **📖 Explanation of the version number:**
> SituationReport uses semantic versioning: `MAJOR.MINOR.PATCH`.
> - **PATCH** (last number): small bug fix
> - **MINOR** (middle number): new feature, backwards-compatible
> - **MAJOR** (first number): fundamental change, compatibility not guaranteed
> Version 1.0.0 will be assigned when the project is considered fully stable.

---

## Technical notes

> **📖 Explanation:**
> This section is aimed at people with a technical background who want to
> know more about how the software is structured.

SituationReport is built as a **monorepo**: all modules live in a single
code repository but can be used independently of each other.

```
situation-report/
├── launcher/           → start window
├── transform_data/     → data preparation
├── build_reports/      → report generation
├── testdata_generator/ → test-data generation
├── helper/             → helper tools
├── get_data/           → (planned)
└── simulate/           → (planned)
```

- **Language:** Python
- **GUI framework:** tkinter
- **Charts:** Plotly
- **Tests:** pytest (approx. 750+ tests, as of v0.13.0)
- **CI/CD:** GitHub Actions (automatic builds for Windows, macOS, Linux)
- **License:** BSD-3-Clause

---

*This document was created from the project's source documentation and
adapted for non-technical readers (updated 2026-05-17).*
