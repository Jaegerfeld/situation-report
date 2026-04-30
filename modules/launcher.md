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
┌──────────────────────────────────────────┐
│  SituationReport  v0.8.1  ALPHA    ?  🌐 │
├──────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐       │
│  │  🔄          │ │  📊          │       │
│  │Transform Data│ │ Build Reports│       │
│  │Jira aufberei.│ │Flow-Metriken │       │
│  │  [Starten]   │ │  [Starten]   │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────┐ ┌──────────────┐       │
│  │  📥          │ │  🎲          │       │
│  │  Get Data    │ │   Simulate   │       │
│  │ (bald verf.) │ │ (bald verf.) │       │
│  └──────────────┘ └──────────────┘       │
│  ┌──────────────┐                        │
│  │  🧪          │                        │
│  │Testdata Gen. │                        │
│  │ (bald verf.) │                        │
│  └──────────────┘                        │
└──────────────────────────────────────────┘
```

## Module

| Modul | Status | Beschreibung |
|-------|--------|-------------|
| `transform_data` | verfügbar | Jira-Rohdaten aufbereiten |
| `build_reports` | verfügbar | Flow-Metriken und Reports |
| `get_data` | geplant | Daten aus Jira laden |
| `simulate` | geplant | Prognosen und Simulationen |
| `testdata_generator` | geplant | Synthetische Testdaten erstellen |

## Verhalten

- Ein Klick auf **Starten** öffnet das Modul als **eigenständigen Prozess** in einem separaten Fenster.
- Der Launcher bleibt offen — mehrere Module können gleichzeitig geöffnet sein.
- Geplante Module sind sichtbar, aber nicht klickbar.

## ALPHA-Kennzeichnung

Der Launcher zeigt ein rotes **ALPHA**-Badge in der Titelleiste, solange sich das Projekt in der Alpha-Phase befindet. Dies signalisiert, dass Funktionsumfang und Stabilität noch nicht dem finalen Stand entsprechen.

## Update-Prüfung

Beim Start prüft der Launcher im Hintergrund, ob auf GitHub eine neuere Version verfügbar ist. Ist das der Fall, erscheint ein gelbes Banner oberhalb des Modul-Grids:

```
Update verfügbar: v0.9.0   [Herunterladen]
```

Ein Klick auf **Herunterladen** öffnet die GitHub-Release-Seite im Browser. Die Prüfung läuft ohne Netz-Anforderung — bei fehlendem Internet erscheint kein Fehler.

## Sprache

Die Sprache wird über den Flag-Button oben rechts umgeschaltet (DE → EN → RO → PT → FR → DE …).
Die Einstellung wird in `~/.situation_report/prefs.json` gespeichert und gilt für alle Module gemeinsam.

## Benutzerhandbuch

Der **?**-Button in der Titelleiste öffnet das Benutzerhandbuch als PDF im Browser (sprachabhängig: Deutsch oder Englisch).
