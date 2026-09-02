# portfolio

Aggregates several already-configured ARTs into a combined **Large-Solution** or
**Portfolio** report — as **pooled** (the solution seen as one system) or
**comparison** (units side by side). It reuses the `build_reports` metrics; the
individual ART reports are only referenced, not changed.

**Status:** available (Alpha)

## Manuals

| Language | Download |
|----------|----------|
| Deutsch (DE) | [Benutzerhandbuch](../portfolio_Benutzerhandbuch.pdf) |
| English (EN) | [User Manual](../portfolio_UserManual.pdf) |
| Română (RO) | [Manual de Utilizator](../portfolio_ManualUtilizator.pdf) |
| Português (PT) | [Manual do Utilizador](../portfolio_ManualUtilizador.pdf) |
| Français (FR) | [Manuel d'utilisation](../portfolio_ManuelUtilisateur.pdf) |

---

## Key concepts

| Term | Meaning |
|------|---------|
| ART | Agile Release Train / team group — the level you already report on in `build_reports`. |
| Solution | A grouping of several ARTs (references their project templates). |
| Portfolio | A grouping of several Solutions (Portfolio > Solutions > ARTs). |
| Pooled | Mode: all issues are merged into **one** dataset — the solution as a single system. |
| Comparison | Mode: each unit (ART or Solution) is shown separately, side by side. |

## Interface

![Portfolio GUI screenshot](../assets/Portfolio-GUI.png)

## Start

### GUI

```bash
python -m portfolio
```

Or click the **Solutions & Portfolios** card on the left of the SituationReport
launcher.

### Command line

```bash
python -m portfolio solution.json --mode pooled --output report.html
# comparison mode / PDF output:
python -m portfolio solution.json --mode comparison --pdf report.pdf
```

The configuration file (`solution.json`) lists the members (ARTs for a solution,
Solutions for a portfolio) and is created/edited in the GUI.

## Report contents

Every report starts with the **management summary** — one row per unit (pooled:
the whole solution/portfolio): items, completed, open (WIP), cycle-time
percentiles (median/85th/95th), the target-CT share, and the **end-to-end lead
time** (Created → Closed, median/85th; in pooled mode the solution lead time
across all ARTs).

Below it, the **Data Quality per Source** table shows for every source: record
count, its **share** of all items, the share without a First Date, the open
share, whether CFD data was supplied, the data freshness — and a traffic-light
**confidence** (high/medium/low, thresholds documented in `summary.py`). The
title carries the coverage ratio ("x/y sources delivered data"). In the PDF the
table is page 2.

In **comparison** mode, Median-CT and 95th-percentile cells are highlighted
red when they exceed 1.5× the column median (three rows minimum) — the
"which unit is the outlier?" question answers itself.

## Custom stage map (optional, config schema 2)

By default, differing ART workflows pool into the three canonical groups
To Do / In Progress / Done. A solution config may instead define its own
canonical stages:

```json
"stage_map": {
  "stages": {
    "Backlog":     ["Funnel", "Analysis"],
    "In progress": ["Implementing", "Review"],
    "Done":        ["Done", "Released"]
  },
  "first_stage": "In progress",
  "closed_stage": "Done"
}
```

`first_stage`/`closed_stage` mark the CFD boundaries. Source stages the map
does not mention fall into `first_stage` with a logged warning. Configs without
the block keep the previous behaviour unchanged (v1 files load as before).

## Architecture

```
portfolio/
├── __main__.py        Dispatcher: GUI without arguments, CLI with arguments
├── cli.py             run_solution_report() + argparse CLI
├── solution_config.py Solution/Portfolio config (members, mode, terminology)
├── aggregator.py      Record-level pooling + rendering (HTML/PDF)
└── summary.py         Management summary + data quality/confidence (A1/A2), outliers (A3)
```

Reuses `build_reports` (loader, metrics, export). Aggregation is done by
**record pooling** — ART issues are merged at the record level and the existing
metrics run over them unchanged (a pooled median ≠ the mean of medians).

## Tests

```bash
python -m pytest tests/portfolio/
```
