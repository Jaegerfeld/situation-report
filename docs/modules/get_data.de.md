# get_data

Zwei gleichwertige Erhebungswege für Jira-Daten — **REST-Abruf** und
**manueller Export** — die in derselben JSON-Datei münden, die
`transform_data` liest.

**Status:** umgesetzt (alpha)

Warum zwei Wege: In großen Organisationen kann die Freigabe für direkte
API-Zugriffe lange dauern. Der manuelle Export (Kapitel 1 des Handbuchs)
bleibt deshalb vollwertig; `get_data` ergänzt den automatischen Abruf und
eine Prüfung für Exporte — beides erzeugt/prüft das identische Artefakt,
die Pipeline dahinter bleibt unverändert.

## Handbücher

| Sprache | Download |
|---------|----------|
| Deutsch (DE) | [Benutzerhandbuch](../get_data_Benutzerhandbuch.pdf) |
| English (EN) | [User Manual](../get_data_UserManual.pdf) |
| Română (RO) | [Manual de Utilizator](../get_data_ManualUtilizator.pdf) |
| Português (PT) | [Manual do Utilizador](../get_data_ManualUtilizador.pdf) |
| Français (FR) | [Manuel d'utilisation](../get_data_ManuelUtilisateur.pdf) |

## Weg 1 — REST-Abruf

```bash
set JIRA_TOKEN=IhrAPIToken
python -m get_data fetch --url https://firma.atlassian.net --project ART_A --email name@firma.de --output ART_A.json
```

- **API-Versionen**: `--api v3` (Standard; `POST /rest/api/3/search/jql`,
  Cursor-Paginierung per `nextPageToken`) oder `--api v2`
  (`GET /rest/api/2/search`, Offset-Paginierung per `startAt`).
- **Anmeldung**: `--auth cloud` (Basic: E-Mail + API-Token, Jira Cloud)
  oder `--auth bearer` (PAT, Server/Data Center).
- **Sicherheit**: Das Token kommt ausschließlich aus einer
  Umgebungsvariable (`--token-env`, Standard `JIRA_TOKEN`) — nie als
  Kommandozeilen-Argument, nie gespeichert, nie geloggt.
- Seiten werden sequenziell mit `expand=changelog` geholt, Duplikate
  entfernt, das Ergebnis im Export-Envelope geschrieben
  (`{expand, startAt, maxResults, total, issues}`).
- Fehlermeldungen sind handlungsleitend: 401/403 zeigt auf Token/Anmeldung
  **oder die noch fehlende API-Freigabe** — und auf den manuellen Weg als
  Ausweichroute.

## Weg 2 — manueller Export (unverändert, plus Prüfung)

Der manuelle Export per curl/Browser (Handbuch Kapitel 1) funktioniert wie
bisher. Neu: die Datei vor der Pipeline prüfen:

```bash
python -m get_data check ART_A_merged.json
```

Die Prüfung erkennt die Klassiker: fehlende Pflichtfelder, fehlender
Changelog (`expand=changelog` vergessen), doppelte Keys — und vergessene
Folgeseiten (`total` größer als die Issues in der Datei). Exit-Code 0 =
verwendbar, 2 = nicht verwendbar.

## GUI

`python -m get_data` (oder die **Get-Data**-Karte im Launcher) öffnet ein
Fenster mit beiden Wegen als Umschalter: *Jira REST-Abruf* (URL, Projekt
oder JQL, API v3/v2, Anmeldung Cloud/Bearer, Token-Feld — nur im Speicher)
und *Vorhandener Export* (Datei wählen → Prüfen). Abruf und Prüfung laufen
im Hintergrund-Thread mit Log-Ausgabe; Texte DE/EN.

## Architektur

```
get_data/
├── __main__.py   Dispatcher: GUI ohne Argumente, CLI mit Argumenten
├── cli.py        Unterbefehle fetch (REST) und check (Export-Prüfung)
├── client.py     Jira-REST-Client: v3/v2-Paginierung, Auth, Fehler-Mapping
├── validate.py   Export-Prüfung (Felder, Changelog, Seiten, Duplikate)
└── gui.py        Zwei-Wege-Fenster (Modus-Umschalter), Thread-+Log-Muster
```

Nur Standardbibliothek (urllib) — keine neuen Abhängigkeiten. Ein
Contract-Test garantiert, dass eine abgerufene Datei und ein manueller
Export derselben Daten von `transform_data` identisch verarbeitet werden.
