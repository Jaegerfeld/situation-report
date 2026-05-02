# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.
Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

---

## [Unreleased]

### Added
- `testdata_generator`: Neues Modul — erzeugt synthetische Jira-Issue-JSON-Dateien
  im Jira-REST-API-Format. Konfigurierbar über GUI oder CLI (Workflow-Datei,
  Projekt-Key, Issue-Anzahl, Datum-Bereich, Completion-Rate, Backflow-Prob., Seed).
  Ausgabe ist direkt mit `transform_data` verarbeitbar.

### Fixed
- `flow_load`: WIP-Zählung auf aktuelle Stage-Position umgestellt — `open_count`
  stimmt jetzt mit Boxplot-Annotationen und IssueTimes überein (PR #62)

---

## [0.8.4] – 2026-04-30

### Added
- `launcher`: Benutzerhandbücher in Rumänisch (RO), Portugiesisch (PT) und
  Französisch (FR) — sprachspezifische PDF-URLs im Launcher (PR #55)

### Fixed
- `build_reports`: Templates konnten nicht mehr geladen werden — globaler
  MouseWheel-Handler durch Hover-basiertes Binding ersetzt;
  alle Dateidialoge mit `parent=self` versehen (PR #56)
- `flow_load`: Stage-Filter von `!= GROUP_DONE` auf explizite Allowlist
  `in (GROUP_TODO, GROUP_IN_PROGRESS)` umgestellt; Kommentare ergänzt (PR #61)

### Changed
- Docs: Feature-Übersicht und Prozess-PPTX auf v0.8.4 aktualisiert (PR #58)

---

## [0.8.3] – 2026-04-30

### Fixed
- `build_reports`: Scrollbares Formular damit der Log-Bereich auf FullHD
  immer sichtbar bleibt (PR #53)

---

## [0.8.2] – 2026-04-30

### Fixed
- Initiale Fensterhöhe wird auf Bildschirmgröße begrenzt (FullHD-Fix) (PR #52)

---

## [0.8.1] – 2026-04-30

### Added
- `launcher`: Hintergrund-Update-Check mit Benachrichtigungs-Banner (PR #51)

---

## [0.8.0] – 2026-04-30

### Added
- `launcher`: Zentrale Launcher-GUI (`python -m launcher`) zum Starten aller
  Module mit Sprachauswahl, ALPHA-Badge und Handbuch-Button (PR #48)
- Double-Click-Startskripte (`SituationReport.bat/.sh/.command`) im Projektstamm (PR #49)

### Fixed
- Reihenfolge Transform Data / Build Reports im Launcher korrigiert (PR #50)

---

## [0.7.0] – 2026-04-30

### Added
- `build_reports`: Process Flow: Time Metrik — gerichteter Graph mit
  durchschnittlicher Verweildauer je Übergang (PR #32)
- CI/CD: GitHub-Actions Release-Workflow mit portablem Python-Paket für
  Windows, macOS (ARM) und Linux; Flag-Sprachumschalter (PR #34)
- Sprachen RO, PT, FR in allen GUIs (PR #43)

### Fixed
- Flow Load: To-Do-Issues und Done-Stages aus Boxplot ausgeblendet (PR #46)
- CI: Portables Windows-Paket auf vollständige CI-Python-Kopie umgestellt (PR #41)
- CI: macOS-Builds (PyInstaller-Fehler, Chrome-Ausschluss) (PR #35 – #37)
- Startskripte umbenannt: `SituationReport.*` → `BuildReports.*` (PR #42)

---

## [0.5.1] – 2026-04-26

### Fixed
- `process_flow`: Created-Knoten in ersten Workflow-Stage zusammengeführt;
  Label-Überlauf behoben (PR #31)

---

## [0.5.0] – 2026-04-26

### Added
- `build_reports`: Process Flow Metrik — gerichteter Graph der Statusübergänge
  mit Transitions-Datei-Picker in der GUI (PR #29, #30)
- Coverage-Badge und pytest-cov eingerichtet (PR #27)

---

## [0.4.1] – 2026-04-26

### Fixed
- Versionsnummer in allen Manuals auf 0.4.1 korrigiert (PR #10)

---

## [0.4.0] – 2026-04-26

### Added
- DE/EN-Sprachauswahl in GUIs mit persistierter Präferenz (Flag-Menü)
- Zweisprachige PDF-Manuals (DE + EN)
- EN-Docs, Feature-Übersichts-PPTX und Prozess-Capability-Map

### Changed
- Pre-Commit-Hook aktualisiert automatisch die Versionsnummer im README-Badge

---

## [0.2.0] – 2026-04-25

### Added
- SemVer-Versionierung eingeführt (Start mit v0.2.0)
- `build_reports`: Flow Distribution (3 Diagramme + Stage Prominence)
- `build_reports`: Zero-Day-Issues ausschließen (konfigurierbarer Schwellwert)
- `build_reports`: Konfigurierbare Target Cycle Time für Flow Time
- `build_reports`: Kollisionsfreie Referenzlinien-Annotationen (Label Repulsion)
- `build_reports`: Issue-Anzahl pro Stage im Flow Load Diagramm
- `build_reports`: Legende für Flow Load Referenzlinien
- `build_reports`: CFD-Trendlinien an visuellen Stage-Grenzen
- `build_reports`: Button „Als PDF speichern" → „Reports exportieren"
- Hilfe-Menü mit Manual-Link in `build_reports` und `transform_data`
