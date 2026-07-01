# Module

| Modul | Beschreibung | Status |
|-------|-------------|--------|
| [launcher](launcher.md) | Zentraler Einstiegspunkt – startet alle Module | verfügbar |
| [transform_data](transform_data.md) | Transformation von Jira-Rohdaten in Stage-Time-Metriken | verfügbar |
| [build_reports](build_reports.md) | Erzeugung von Metriken und Reports | verfügbar |
| [portfolio](portfolio.md) | Aggregierte Large-Solution- & Portfolio-Reports über mehrere ARTs | verfügbar (Alpha) |
| [helper](helper.md) | JSON-Dateien zusammenführen (Jira-Paginierung) | verfügbar (Alpha) |
| [testdata_generator](testdata_generator.md) | Generierung synthetischer Testdaten | verfügbar (Beta) |
| [get_data](get_data.md) | Datenabruf aus Jira via REST API | geplant |
| [simulate](simulate.md) | Simulationen und Vorhersagemodelle | verfügbar (Alpha) |

## Gemeinsames Projekt-Template

`transform_data`, `build_reports`, `testdata_generator` und `helper` teilen sich
ein gemeinsames Projekt-Template: eine einzige JSON-Datei mit je einem Abschnitt
pro Modul. Über das Menü **Templates → Speichern / Laden** kann die
Pipeline-Konfiguration (Workflow, Pfade, Projekt-Key, Zeitraum) einmal
gespeichert und in jedem Modul-GUI wieder geladen werden. Beim Speichern aus
einem Modul bleiben die Abschnitte der übrigen Module erhalten. Ältere
`build_reports`-Templates (Schema v4) werden weiterhin gelesen.
