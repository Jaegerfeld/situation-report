# simulate

Throughput-basierter Monte-Carlo-Forecast auf historischen Jira-Daten. Beantwortet
zwei Fragen probabilistisch — **ohne Story-Point-Schätzung** — und leitet daraus
eine Scope-Konfidenz-Sicht aus denselben Läufen ab.

**Status:** verfügbar (Alpha)

## Handbücher

| Sprache | Download |
|----------|----------|
| Deutsch (DE) | [Benutzerhandbuch](../simulate_Benutzerhandbuch.pdf) |
| English (EN) | [User Manual](../simulate_UserManual.pdf) |
| Română (RO) | [Manual de Utilizator](../simulate_ManualUtilizator.pdf) |
| Português (PT) | [Manual do Utilizador](../simulate_ManualUtilizador.pdf) |
| Français (FR) | [Manuel d'utilisation](../simulate_ManuelUtilisateur.pdf) |

---

## Was es beantwortet

- **Wie viele Items** schaffen wir in einem Zeitraum? (Kapazitäts-Forecast)
- **Wann ist** ein Backlog von N Items **fertig**? (Termin-Forecast, optional mit
  Scope-Wachstum über eine Split-Rate)
- **Schaffen wir den Scope bis Datum X?** — eine Konfidenz-Gauge aus denselben
  Läufen (der Punkt der Exceedance-Kurve an der Stelle „Backlog").

Die Ergebnisse werden als **Exceedance-Perzentile** mit Referenzlinien bei
85 / 75 / 50 % dargestellt, z. B. „mit 85 % Konfidenz mindestens X Items" oder
„spätestens an Tag Y fertig".

## Oberfläche

![Simulate-GUI-Screenshot](../assets/Simulate-GUI.png)

## Start

### GUI

```bash
python -m simulate
```

Oder die **Simulate**-Kachel im SituationReport-Launcher anklicken.

### Kommandozeile

```bash
python -m simulate ART_A_IssueTimes.xlsx \
    --horizon 84 --backlog 125 --split-rate 0.1 \
    --runs 25000 --seed 11 --output forecast.html
```

## Parameter

| Parameter | Standard | Beschreibung |
|-----------|---------|-------------|
| `issue_times` | (Pflicht) | Pfad zur `IssueTimes.xlsx` |
| `--cfd FILE` | (keine) | Optionale `CFD.xlsx` |
| `--history-days N` | `180` | Länge des History-Fensters in Tagen |
| `--history-end YYYY-MM-DD` | heute | Exklusives Enddatum des History-Fensters |
| `--horizon DAYS` | `84` | Vorhersagehorizont (Kapazitäts-Forecast) |
| `--backlog N` | (keine) | Aktiviert zusätzlich Termin- + Scope-Konfidenz-Forecast |
| `--runs N` | `25000` | Anzahl Monte-Carlo-Läufe |
| `--split-rate R` | `0.0` | Erwartete neue Items je erledigtem Item (Scope-Wachstum) |
| `--seed N` | (zufällig) | Seed für reproduzierbare Läufe |
| `--output FILE` | (keine) | HTML-Report in diese Datei schreiben |
| `--browser` | aus | Geschriebenen Report im Browser öffnen |

## Methode

Reine Standardbibliothek (kein numpy/pandas) für maximale Portabilität. Aus dem
History-Fenster — **inklusive Null-Tage**, damit der Forecast nicht überschätzt
wird — wird die empirische Tagesdurchsatz-Verteilung gebildet und über `runs`
Läufe neu gezogen (`random.choices`, reproduzierbar via Seed). Der Termin-Forecast
lässt den Rest-Scope optional um `split_rate` je erledigtem Item wachsen; seine
Perzentile werden über **alle** Läufe gebildet, sodass eine Konfidenz oberhalb der
Fertigstellungsrate „≥ Cap" statt eines zu optimistischen Tages liest. Inspiriert
vom R-Prototyp des Teams und von Daniel Vacanti, *Actionable Agile Metrics for
Predictability*.

## Architektur

```
simulate/
├── __main__.py     Dispatcher: GUI ohne Argumente, CLI mit Argumenten
├── cli.py          run_simulation() + argparse-CLI
├── forecast.py     Monte-Carlo-Engine (how_many / when_done / probability_at_least)
├── throughput.py   ReportData -> Tagesdurchsatz-Reihe (inkl. Null-Tage)
├── charts.py       Plotly: Exceedance-Kurve, Ziel-Marker, Gauge, Verteilung
└── gui.py          tkinter-GUI (de/en)
```

Die Engine nutzt `build_reports.loader.ReportData`; der Throughput-Adapter macht
aus den geladenen Issues die Tagesreihe, aus der die Engine zieht.

## Tests

```bash
python -m pytest tests/simulate/
```
