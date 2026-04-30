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
┌────────────────────────────────────┐
│  SituationReport          v0.8.0  🌐 │
├────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐  │
│  │  📊          │ │  🔄          │  │
│  │ Build Reports│ │Transform Data│  │
│  │Flow metrics  │ │Prepare data  │  │
│  │  [Launch]    │ │  [Launch]    │  │
│  └──────────────┘ └──────────────┘  │
│  ┌──────────────┐ ┌──────────────┐  │
│  │  📥          │ │  🎲          │  │
│  │  Get Data    │ │   Simulate   │  │
│  │(coming soon) │ │(coming soon) │  │
│  └──────────────┘ └──────────────┘  │
│  ┌──────────────┐                   │
│  │  🧪          │                   │
│  │Testdata Gen. │                   │
│  │(coming soon) │                   │
│  └──────────────┘                   │
└────────────────────────────────────┘
```

## Modules

| Module | Status | Description |
|--------|--------|-------------|
| `build_reports` | available | Flow metrics and reports |
| `transform_data` | available | Prepare raw Jira data |
| `get_data` | planned | Fetch data from Jira |
| `simulate` | planned | Forecasts and simulations |
| `testdata_generator` | planned | Generate synthetic test data |

## Behaviour

- Clicking **Launch** opens the module as an **independent process** in a separate window.
- The launcher stays open — multiple modules can run simultaneously.
- Planned modules are visible but not clickable.

## Language

The language is switched via the flag button in the top right (DE → EN → RO → PT → FR → DE …).
The setting is saved in `~/.situation_report/prefs.json` and applies to all modules.
