# launcher

Der `launcher` ist der zentrale Einstiegspunkt für SituationReport. Er zeigt alle verfügbaren und geplanten Module als Karten-Grid und ermöglicht den direkten Start per Klick.

**Start:**
```bash
python -m launcher
```

Oder über die Startdatei im portablen Paket:
- **Windows:** `SituationReport.bat`
- **macOS:** `SituationReport.command`
- **Linux:** `SituationReport.sh`

## Oberfläche

```
┌────────────────────────────────────┐
│  SituationReport          v0.8.0  🌐 │
├────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐  │
│  │  📊          │ │  🔄          │  │
│  │ Build Reports│ │Transform Data│  │
│  │Flow-Metriken │ │Jira aufberei.│  │
│  │  [Starten]   │ │  [Starten]   │  │
│  └──────────────┘ └──────────────┘  │
│  ┌──────────────┐ ┌──────────────┐  │
│  │  📥          │ │  🎲          │  │
│  │  Get Data    │ │   Simulate   │  │
│  │ (bald verf.) │ │ (bald verf.) │  │
│  └──────────────┘ └──────────────┘  │
│  ┌──────────────┐                   │
│  │  🧪          │                   │
│  │Testdata Gen. │                   │
│  │ (bald verf.) │                   │
│  └──────────────┘                   │
└────────────────────────────────────┘
```

## Module

| Modul | Status | Beschreibung |
|-------|--------|-------------|
| `build_reports` | verfügbar | Flow-Metriken und Reports |
| `transform_data` | verfügbar | Jira-Rohdaten aufbereiten |
| `get_data` | geplant | Daten aus Jira laden |
| `simulate` | geplant | Prognosen und Simulationen |
| `testdata_generator` | geplant | Synthetische Testdaten erstellen |

## Verhalten

- Ein Klick auf **Starten** öffnet das Modul als **eigenständigen Prozess** in einem separaten Fenster.
- Der Launcher bleibt offen — mehrere Module können gleichzeitig geöffnet sein.
- Geplante Module sind sichtbar, aber nicht klickbar.

## Sprache

Die Sprache wird über den Flag-Button oben rechts umgeschaltet (DE → EN → RO → PT → FR → DE …).
Die Einstellung wird in `~/.situation_report/prefs.json` gespeichert und gilt für alle Module gemeinsam.
