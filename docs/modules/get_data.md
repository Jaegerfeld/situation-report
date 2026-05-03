# get_data

Datenabruf aus Jira via REST API.

**Status:** geplant

---

## Workaround (bis zur Verfügbarkeit)

Solange `get_data` noch nicht verfügbar ist, können Jira-Daten manuell beschafft werden.
Der Launcher zeigt dazu einen **Anleitung**-Button auf der Get-Data-Karte.

### Schritt 1 — Jira-JSON exportieren

Issues über die **Jira REST API** als JSON exportieren:

```
https://<jira-host>/rest/api/2/search?jql=project=MEINPROJEKT&expand=changelog&maxResults=1000
```

!!! info "Paginierung"
    Jira liefert maximal **1.000 Issues pro Abfrage**. Bei größeren Projekten entstehen mehrere Seiten — dann weiter mit Schritt 2.

### Schritt 2 — Dateien zusammenführen (nur bei mehreren Dateien)

`helper` starten → alle JSON-Dateien in einer Listbox auswählen → **Zusammenführen**.

Ergebnis: eine einzige `merged.json`, direkt von `transform_data` verarbeitbar.

→ [helper](helper.md)

### Schritt 3 — Daten aufbereiten

`transform_data` starten → zusammengeführte (oder einzelne) JSON-Datei laden → Workflow-Datei angeben → Verarbeiten.

→ [transform_data](transform_data.md)
