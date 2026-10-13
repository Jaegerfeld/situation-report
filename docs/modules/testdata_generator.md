# testdata_generator

Generates synthetic Jira issue JSON files in Jira REST API format.
The generated files can be processed directly by `transform_data` and are
suitable for development, testing, and demonstrations without real Jira data.

## Start

### GUI

```bash
python -m testdata_generator
```

### Command line

```bash
python -m testdata_generator \
    --workflow workflow_ART_A.txt \
    --project ART_A_GEN \
    --issues 200 \
    --seed 42 \
    --output ART_A_generated.json
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--workflow FILE` | (required) | Workflow definition file |
| `--output FILE.json` | `<project>_generated.json` | Output file |
| `--project KEY` | `TEST` | Jira project key |
| `--issues N` | `100` | Number of issues to generate |
| `--from-date YYYY-MM-DD` | `2025-01-01` | Earliest creation date |
| `--to-date YYYY-MM-DD` | `2025-12-31` | Latest transition date |
| `--issue-types TYPE:W …` | `Feature:0.6 Bug:0.3 Enabler:0.1` | Issue types with weights |
| `--completion-rate FLOAT` | `0.7` | Fraction of closed issues (0–1) |
| `--todo-rate FLOAT` | `0.15` | Fraction of open issues in To Do stages (0–1) |
| `--backflow-prob FLOAT` | `0.1` | Probability of backward transitions (0–1) |
| `--seed INT` | (random) | Seed for reproducible output |
| `--mean-cycle-days FLOAT` | (none) | Target mean cycle time in days (lognormal) |
| `--std-cycle-days FLOAT` | (30 % of mean) | Standard deviation of cycle time |
| `--pattern PATTERN` | `none` | Flow anti-pattern: `none` / `triangle` / `flat_triangle` / `cluster` / `batch` |
| `--pi-duration-weeks INT` | `12` | PI cycle length in weeks (for `cluster`/`batch`) |
| `--realism 0–100` | `0` | Untidiness of the stage paths (skips, cancels, parking, self-loops, reopening); about 70 is like a real ART |
| `--continue OLD.json` | (none) | Continue an earlier extract up to `--to-date` (since 0.39.0); `--issues` = number of NEW issues, `--rate-per-day` alternative |
| `--rate-per-day FLOAT` | (rate of the first window) | With `--continue`: new issues per day |

## Flow Patterns

Simulatable anti-patterns via `--mean-cycle-days` + `--pattern`:
`triangle` (CT rises linearly), `flat_triangle` (rise flattens out),
`cluster` (deliveries cluster at PI end), `batch` (PI clustering + high CT variance).

## Realistic stage paths (since 0.38.0)

A real ART does not walk neatly through every stage. Measured on the real ART_A (458 issues,
9 stages): 40 distinct transition pairs, 12 % backward, 7.5 % self-loops, 358 jumps over at
least one stage, 149 entries into the final stage without closing, median 4 transitions per
issue. The generator before 0.38.0 produced 11 pairs, 0 % loops, median 7.

`--realism` (0–100) scales eight disturbances of the path: jumps over stages, cancellations
straight into the final stage, parking in a side-track stage (recognised by name: Blocker,
Blocked, On Hold, Waiting …), self-loops, backflow over several stages, reopening, a start
outside the first working stage, and the move from closing into the final stage
(Releasing → Done). **0 is the previous behaviour** (only `--backflow-prob`), **about 70
matches the real ART_A** — the calibration is pinned by tests. Path and time are separate:
the disturbances apply in every mode, including the flow patterns, where the cycle time is
spread over the longer or shorter path.

The portfolio scenario builds its six ARTs with realism 60 since 0.38.0 (profile field
`realism`, overridable per ART). Seeds produce different data than before 0.38.0 — the
order of random draws changed.

## Continuation — the second extract (since 0.39.0)

A generated raw data set is an extract taken on T1. `--continue` produces the extract one
would have taken on T2 — exactly as if the data had been pulled manually twice:

```bash
python -m testdata_generator --workflow workflow.txt --continue ART_A.json --to-date 2026-03-01
```

- **The past is untouchable:** keys, creation dates and every transition up to T1 stay byte
  for byte; closed and cancelled issues are not touched at all.
- **Open issues move on:** new transitions after T1 under the same path and time model
  (realism, backflow, cycle time) until they finish or T2 is reached — whatever would fall
  after T2 stays open.
- **New issues** join in (T1, T2] with continuing keys; their number follows the rate of
  the first window, or `--issues N` / `--rate-per-day X`.
- **Reproducible:** the same seed and the same T2 give the same extract; a chain
  T1 → T2 → T3 keeps every earlier state in full.

For this the generator writes a `generator` record into the JSON envelope since 0.39.0
(cuts, seed, knobs, stages); `transform_data` reads only `issues` and is unaffected. A data
set without the record (older, or a real export) can be continued when the knobs are given —
T1 is then the youngest timestamp. Output: `<name>_<T2>.json` next to the source, or
`--output`. GUI: button **Continue…** next to **Generate** (To date and realism from the form).

## Workflow file

Same format as in `transform_data`:

```
CanonicalStageName:Alias1:Alias2
<First>StageName
<Closed>StageName
```

## Output and further processing

```bash
# Generate
python -m testdata_generator --workflow workflow.txt --project ART_TEST --seed 1

# Process directly with transform_data
python -m transform_data ART_TEST_generated.json workflow.txt
```

The generated JSON file contains Jira changelog histories with status transitions
along the defined workflow. `transform_data` processes them into
`IssueTimes.xlsx`, `CFD.xlsx`, and `Transitions.xlsx`.

## Architecture

```
testdata_generator/
├── __main__.py          # Dispatcher: GUI without arguments, CLI with arguments
├── cli.py               # run_generate() + argparse CLI
├── generator.py         # Core logic: issue simulation (time onto the path)
├── paths.py             # Stage paths: realism disturbances, parking stage (0.38.0)
├── continuation.py      # Continuation: second extract, envelope record (0.39.0)
└── workflow_parser.py   # Re-export from transform_data.workflow
```

## Tests

```bash
python -m pytest tests/testdata_generator/
```
