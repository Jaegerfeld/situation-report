# Development

## Prerequisites

- Python >= 3.11
- Git

## Setup

```bash
git clone https://github.com/Jaegerfeld/situation-report.git
cd situation-report
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -e ".[docs]"
```

## Preview documentation locally

```bash
mkdocs serve
```

The documentation is then available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Branch convention

New work on a module is done on a dedicated branch:

```
dev/<module_name>
```

After completion, a pull request is opened against `main`. The finished state is tagged with the module name (e.g. `transform_data`).

## Technology stack

| Area | Technology |
|------|------------|
| Language | Python >= 3.11 |
| Package management | pip / pyproject.toml |
| Version control | Git / GitHub |
| Documentation | MkDocs + Material Theme |
| Data source | Jira REST API |
| Output format | XLSX (openpyxl) |
