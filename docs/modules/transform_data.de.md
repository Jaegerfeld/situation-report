# transform_data

Transformiert Jira-Rohdaten (Issue-Export) in Stage-Time-Metriken (IssueTimes.xlsx, CFD.xlsx, Transitions.xlsx).

**Status:** verfügbar

## Handbücher

| Sprache | Download |
|---------|----------|
| Deutsch (DE) | [Benutzerhandbuch](../transform_data_Benutzerhandbuch.pdf) |
| English (EN) | [User Manual](../transform_data_UserManual.pdf) |
| Română (RO) | [Manual de Utilizator](../transform_data_ManualUtilizator.pdf) |
| Português (PT) | [Manual do Utilizador](../transform_data_ManualUtilizador.pdf) |
| Français (FR) | [Manuel d'utilisation](../transform_data_ManuelUtilisateur.pdf) |

## Datenübergabe an build_reports

Nach einer erfolgreichen Transformation übergibt der Button **In build_reports
öffnen** die drei erzeugten XLSX-Dateien und die Workflow-Datei direkt an
`build_reports`. Die Reports-GUI startet mit bereits ausgefüllten Datei-Feldern
— die Dateien müssen nicht erneut ausgewählt werden.

Ist ein Projekt-Template geladen (Templates → Laden), werden auch dessen
build_reports-Einstellungen — PI-Konfiguration, Filter, Metrik-Auswahl — in die
Übergabe mitgenommen, sodass `build_reports` vollständig konfiguriert startet.
Ohne geladenes Template wählen Sie PI-Konfiguration und Filter weiterhin selbst.
