# Releases & Installation

SituationReport wird als eigenständige Desktop-App ausgeliefert – **kein Python, keine Installation notwendig**.
Einfach herunterladen, entpacken und starten.

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
3. Im entpackten Ordner `SituationReport.exe` doppelklicken

!!! note "Windows SmartScreen"
    Beim ersten Start erscheint möglicherweise ein SmartScreen-Hinweis, da die App nicht signiert ist.
    Auf **Weitere Informationen** → **Trotzdem ausführen** klicken.

---

### macOS (Apple Silicon)

1. `SituationReport-macOS-ARM.zip` herunterladen
2. Zip-Datei entpacken
3. `SituationReport.app` in den Ordner *Programme* ziehen (optional)
4. **Ersten Start**: Rechtsklick auf die App → *Öffnen* → im Dialog erneut *Öffnen* bestätigen

!!! note "macOS Gatekeeper"
    Da die App nicht notarisiert ist, blockiert macOS den ersten Start per Doppelklick.
    Der Rechtsklick-Weg umgeht diesen Schutz einmalig.

---

### Linux (x64)

1. `SituationReport-Linux.zip` herunterladen
2. Zip-Datei entpacken
3. Terminal öffnen, in den entpackten Ordner wechseln und starten:

```bash
chmod +x SituationReport   # einmalig
./SituationReport
```

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

| Plattform | Runner | Ausgabe |
|-----------|--------|---------|
| Windows | `windows-latest` | `SituationReport-Windows.zip` |
| macOS (Apple Silicon) | `macos-latest` | `SituationReport-macOS-ARM.zip` |
| Linux x64 | `ubuntu-latest` | `SituationReport-Linux.zip` |
