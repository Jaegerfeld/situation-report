# SituationReport

Toolsuite for retrieving Jira issue data and preparing it for metrics and reports.

!!! tip "📚 The Memoranda Series — the thinking behind the tool"
    The software is the tool; the **memoranda (Denkschriften)** are its conceptual foundation: how large IT portfolios are led — with an honest **situational picture**, trained **staffs**, and **AI as a staff member**. Six memoranda for decision-makers, freely available in English and German, each with its single most important sentence up front.

    **→ [Read the memoranda](denkschriften/index.md)**

    [![The memoranda series at a glance](denkschriften/Memoranda-Series_Overview-en.png)](denkschriften/index.md)

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| [`launcher`](modules/launcher.md) | Central entry point – launches all modules | available |
| [`transform_data`](modules/transform_data.md) | Transform raw Jira data into stage-time metrics | available |
| [`build_reports`](modules/build_reports.md) | Generate metrics and reports | available |
| [`portfolio`](modules/portfolio.md) | Aggregated Large-Solution & Portfolio reports across several ARTs | available (Alpha) |
| [`helper`](modules/helper.md) | Merge JSON files (Jira pagination) | available (Alpha) |
| [`testdata_generator`](modules/testdata_generator.md) | Generate synthetic test data | available (Beta) |
| [`get_data`](modules/get_data.md) | Retrieve data from Jira — REST or export validation | available (Alpha) |
| [`sources`](modules/sources.md) | Pluggable external metric sources (SLO, DORA, quality) | available (Alpha) |
| [`llm`](modules/llm.md) | Pluggable AI narration (local Ollama, Claude API, mock) | available (Alpha) |
| [`simulate`](modules/simulate.md) | Simulations and prediction models | available (Alpha) |

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
