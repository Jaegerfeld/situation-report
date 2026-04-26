# situation-report

**Version 0.4.0**

Toolsuite for querying Jira issue data and processing it into flow metrics and reports.

**Documentation:** https://jaegerfeld.github.io/situation-report/  
**Architecture:** https://jaegerfeld.github.io/situation-report/architecture/

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| [`transform_data`](https://jaegerfeld.github.io/situation-report/modules/transform_data/) | Transform raw Jira data into stage-time metrics | available |
| [`build_reports`](https://jaegerfeld.github.io/situation-report/modules/build_reports/) | Generate flow metrics and reports | available |
| `get_data` | Fetch issue data from Jira via REST API | planned |
| `testdata_generator` | Generate synthetic test data | planned |
| `simulate` | Simulations and forecasting models | planned |

## Setup

```bash
git clone https://github.com/Jaegerfeld/situation-report.git
cd situation-report
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## License

BSD-3-Clause — see [LICENSE](LICENSE)
