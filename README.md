# situation-report

**Version 0.8.2** ![Coverage](docs/coverage.svg)

Toolsuite for querying Jira issue data and processing it into flow metrics and reports.

**Documentation:** https://jaegerfeld.github.io/situation-report/  
**Architecture:** https://jaegerfeld.github.io/situation-report/architecture/  
**Roadmap:** https://github.com/users/Jaegerfeld/projects/1

---

> This project was created as an exploration of the possibilities of AI-driven development.
> More than 98% of the code is written by AI — currently using [Claude Code](https://claude.ai/code) (Anthropic).
>
> The primary goal is to study the challenges, solutions, and risks that arise when AI authors production software. At some point this may transition to a regular project with more human authorship — but not yet.
>
> The software is intended to be genuinely useful and will continue to evolve. Feel free to use it and share feedback.
>
> Don't be surprised if something feels a little off — even the quirks were produced by Claude.
>
> — Robert "Jaegerfeld" Seebauer

---

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| [`launcher`](https://jaegerfeld.github.io/situation-report/modules/launcher/) | Central launcher GUI for all modules | available |
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

## Usage

Start the launcher GUI:

- **Windows:** double-click `SituationReport.bat`
- **macOS:** double-click `SituationReport.command`
- **Linux:** run `./SituationReport.sh`
- **Terminal (all platforms):** `python -m launcher`

The launcher opens a central window from which all available modules can be started.

## License

BSD-3-Clause — see [LICENSE](LICENSE)
