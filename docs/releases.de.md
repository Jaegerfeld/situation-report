# Releases & Installation

SituationReport wird als portables Paket ausgeliefert – alle Quelldateien, Skripte und Konfigurationsmöglichkeiten sind enthalten.
Herunterladen, entpacken und starten.

---

## Download

Alle verfügbaren Releases sind auf der [GitHub-Releases-Seite](https://github.com/Jaegerfeld/situation-report/releases) zu finden.

| Release-Typ | Beschreibung | Wann verfügbar |
|-------------|-------------|----------------|
| **Stabile Version** (z. B. `v0.6.0`) | Getesteter, produktionsreifer Stand | Nach jedem Versions-Tag |
| **Dev Build** (`dev-latest`) | Aktuellster Entwicklungsstand von `main` | Nach jedem Merge auf `main` |

!!! tip "Welche Version nehmen?"
    Für den normalen Einsatz immer die **neueste stabile Version** verwenden.
    Dev Builds sind für das Testen neuer Features gedacht und können unfertige Funktionen enthalten.

---

## Installation

### Windows

1. `SituationReport-Windows.zip` herunterladen
2. Zip-Datei entpacken (Rechtsklick → *Alle extrahieren*)
3. Im entpackten Ordner:
   - `SituationReport.bat` doppelklicken → Launcher (alle Module)
   - `BuildReports.bat` doppelklicken → Build Reports GUI
   - `TransformData.bat` doppelklicken → Transform Data GUI
   - `TestdataGenerator.bat` doppelklicken → Testdata Generator GUI
   - `Helper.bat` doppelklicken → Helper (JSON Merger) GUI

!!! note "Windows SmartScreen"
    Beim ersten Start erscheint möglicherweise ein SmartScreen-Hinweis, da die enthaltenen Dateien nicht signiert sind.
    Auf **Weitere Informationen** → **Trotzdem ausführen** klicken.

!!! info "Enthält Python und Chrome"
    Das Windows-Paket enthält Python 3.11 und Chrome (für PDF-Export) – kein Internet oder separate Installation notwendig.

---

### macOS (Apple Silicon)

1. `SituationReport-macOS-ARM.zip` herunterladen
2. Zip-Datei entpacken
3. Rechtsklick auf `SituationReport.command` → *Öffnen* → im Dialog erneut *Öffnen* bestätigen (einmalig, für weitere Launcher gilt das gleiche Vorgehen)

!!! note "macOS Gatekeeper"
    Da die Skripte nicht notarisiert sind, blockiert macOS den ersten Start per Doppelklick.
    Der Rechtsklick-Weg umgeht diesen Schutz einmalig.

!!! warning "Einmalige Einrichtung (erster Start)"
    Beim ersten Start wird automatisch eine Python-Umgebung eingerichtet (~1 Minute).
    **Internet erforderlich.** Danach funktioniert die App offline.

---

### Linux (x64)

1. `SituationReport-Linux.zip` herunterladen
2. Zip-Datei entpacken
3. Voraussetzung prüfen:
   ```bash
   python3 --version           # 3.11 oder neuer
   python3 -c "import tkinter" # muss ohne Fehler laufen
   ```
   Falls tkinter fehlt: `sudo apt install python3-tk` (Ubuntu/Debian) oder `sudo dnf install python3-tkinter` (Fedora)
4. Im entpackten Ordner starten:
   ```bash
   ./SituationReport.sh        # Launcher (alle Module)
   ./BuildReports.sh           # Build Reports GUI
   ./TransformData.sh          # Transform Data GUI
   ./TestdataGenerator.sh      # Testdata Generator GUI
   ./Helper.sh                 # Helper (JSON Merger) GUI
   ```

!!! warning "Einmalige Einrichtung (erster Start)"
    Beim ersten Start wird automatisch eine Python-Umgebung eingerichtet (~1 Minute).
    **Internet erforderlich.** Danach funktioniert die App offline.

---

## Paketinhalt

Das Paket enthält das gesamte Repository – Quelldateien, Konfigurationen und Beispiele:

| Datei / Ordner | Inhalt |
|----------------|--------|
| `build_reports/` | Metriken, GUI, CLI und Plugin-Mechanismus |
| `transform_data/` | Datenaufbereitung (Jira-Export → XLSX) |
| `get_data/` | Datenzugriff |
| `simulate/` | Simulation und Testdaten-Generierung |
| `testdata_generator/` | Beispiel-Workflows und Testdaten |
| `build_reports/pi_config_example.json` | Vorlage für PI-Konfiguration |
| `SituationReport.bat/.command/.sh` | Launcher (alle Module) |
| `BuildReports.bat/.command/.sh` | Starter für Build Reports |
| `TransformData.bat/.command/.sh` | Starter für Transform Data |
| `TestdataGenerator.bat/.command/.sh` | Starter für Testdata Generator |
| `Helper.bat/.command/.sh` | Starter für Helper (JSON Merger) |

---

## Release-Prozess (für Entwickler)

### Stabiles Release veröffentlichen

Ein stabiles Release wird durch einen **Version-Tag** auf `main` ausgelöst:

```bash
# Version in version.py aktualisieren, committen und pushen
git tag v0.6.0
git push origin v0.6.0
```

GitHub Actions baut daraufhin automatisch alle drei Plattformen und veröffentlicht das Release mit den ZIP-Dateien als Anhang.

Namensschema: `vMAJOR.MINOR.PATCH` gemäß [SemVer](https://semver.org/lang/de/).

| Versionssprung | Wann |
|----------------|------|
| `PATCH` (`v0.5.0` → `v0.5.1`) | Bugfix |
| `MINOR` (`v0.5.1` → `v0.6.0`) | Neues Feature |
| `MAJOR` (`v0.6.0` → `v1.0.0`) | Brechende Änderung (neues Dateiformat o. Ä.) |

### Dev Build

Der Dev Build wird **automatisch** nach jedem Merge auf `main` ausgelöst – kein manuelles Eingreifen notwendig.
Das bestehende `dev-latest`-Release auf GitHub wird dabei überschrieben.

---

## GitHub Actions Workflows

| Workflow | Datei | Trigger |
|----------|-------|---------|
| Build & Release | `.github/workflows/release.yml` | Push eines `v*`-Tags |
| Dev Build | `.github/workflows/dev-build.yml` | Merge auf `main` |
| Deploy Docs | `.github/workflows/docs.yml` | Änderungen in `docs/` oder `mkdocs.yml` |

### Unterstützte Plattformen

| Plattform | Runner | Ausgabe | Python |
|-----------|--------|---------|--------|
| Windows | `windows-latest` | `SituationReport-Windows.zip` | Embeddable 3.11 (im Paket) |
| macOS (Apple Silicon) | `macos-latest` | `SituationReport-macOS-ARM.zip` | System-Python + venv (beim 1. Start) |
| Linux x64 | `ubuntu-latest` | `SituationReport-Linux.zip` | System-Python + venv (beim 1. Start) |
