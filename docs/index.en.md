# SituationReport

Toolsuite for retrieving Jira issue data and preparing it for metrics and reports.

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| [`transform_data`](modules/transform_data.md) | Transform raw Jira data into stage-time metrics | available |
| [`get_data`](modules/get_data.md) | Retrieve data from Jira via REST API | planned |
| [`build_reports`](modules/build_reports.md) | Generate metrics and reports | available |
| [`testdata_generator`](modules/testdata_generator.md) | Generate synthetic test data | available (Alpha) |
| [`simulate`](modules/simulate.md) | Simulations and prediction models | planned |
| [`helper`](modules/helper.md) | Helper tools (JSON Merger etc.) | available (Alpha) |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -e .
```

To preview the documentation locally:

```bash
pip install -e ".[docs]"
mkdocs serve
```
