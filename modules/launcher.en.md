# launcher

The `launcher` is the central entry point for SituationReport. It displays all available and planned modules as a card grid and allows launching them with a single click.

**Start:**
```bash
python -m launcher
```

Or via the start script in the portable package:
- **Windows:** `SituationReport.bat`
- **macOS:** `SituationReport.command`
- **Linux:** `SituationReport.sh`

## Interface

```
┌──────────────────────────────────────────┐
│  SituationReport  v0.8.2  ALPHA    ?  🌐 │
├──────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐       │
│  │  🔄          │ │  📊          │       │
│  │Transform Data│ │ Build Reports│       │
│  │Prepare data  │ │Flow metrics  │       │
│  │  [Launch]    │ │  [Launch]    │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────┐ ┌──────────────┐       │
│  │  📥          │ │  🎲          │       │
│  │  Get Data    │ │   Simulate   │       │
│  │(coming soon) │ │(coming soon) │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────┐                        │
│  │  🧪          │                        │
│  │Testdata Gen. │                        │
│  │(coming soon) │                        │
│  └──────────────┘                        │
└──────────────────────────────────────────┘
```

## Modules

| Module | Status | Description |
|--------|--------|-------------|
| `transform_data` | available | Prepare raw Jira data |
| `build_reports` | available | Flow metrics and reports |
| `get_data` | planned | Fetch data from Jira |
| `simulate` | planned | Forecasts and simulations |
| `testdata_generator` | planned | Generate synthetic test data |

## Behaviour

- Clicking **Launch** opens the module as an **independent process** in a separate window.
- The launcher stays open — multiple modules can run simultaneously.
- Planned modules are visible but not clickable.

## ALPHA indicator

The launcher displays a red **ALPHA** badge in the title bar while the project is in its alpha phase. This signals that features and stability are not yet at their final state.

## Update check

On startup, the launcher checks in the background whether a newer version is available on GitHub. If so, a yellow banner appears above the module grid:

```
Update available: v0.9.0   [Download]
```

Clicking **Download** opens the GitHub releases page in the browser. The check runs silently — no error is shown when there is no internet connection.

## Language

The language is switched via the flag button in the top right (DE → EN → RO → PT → FR → DE …).
The setting is saved in `~/.situation_report/prefs.json` and applies to all modules.

## User manual

The **?** button in the title bar opens the user manual as a PDF in the browser (language-dependent: German or English).
