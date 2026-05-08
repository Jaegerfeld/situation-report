# get_data

!!! note "Geplant"
    Dieses Modul ist noch nicht implementiert. Bis es verfügbar ist, können Jira-Daten manuell über die REST API exportiert werden.

Datenabruf aus Jira via REST API. Erzeugt den JSON-Export, der von `transform_data` weiterverarbeitet wird.

## Manueller Workaround

Solange `get_data` noch nicht verfügbar ist, können Daten manuell exportiert werden:

1. **Jira-JSON exportieren** — Issues über die Jira REST API als JSON exportieren (`expand=changelog` ist Pflicht).
2. **Dateien zusammenführen** — Bei mehr als 1.000 Issues: `helper` zum Zusammenführen der paginierten Exporte verwenden.
3. **Daten aufbereiten** — `transform_data` mit der JSON-Datei starten.

Der vollständige Export-Prozess (API-Token, curl-Beispiele, Paginierung, Workflow-Datei erstellen) ist im Benutzerhandbuch dokumentiert.

## Benutzerhandbuch

- [get_data Benutzerhandbuch (DE)](../get_data_Benutzerhandbuch.pdf)
- [get_data User Manual (EN)](../get_data_UserManual.pdf)
