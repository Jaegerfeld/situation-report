# testdata_generator

Erzeugt synthetische Jira-Issue-JSON-Dateien im Jira-REST-API-Format.
Die generierten Dateien sind direkt mit `transform_data` verarbeitbar und
eignen sich für Entwicklung, Tests und Demonstrationen ohne echte Jira-Daten.

## Start

### GUI

```bash
python -m testdata_generator
```

### Kommandozeile

```bash
python -m testdata_generator \
    --workflow workflow_ART_A.txt \
    --project ART_A_GEN \
    --issues 200 \
    --seed 42 \
    --output ART_A_generated.json
```

## Parameter

| Parameter | Standard | Beschreibung |
|-----------|---------|-------------|
| `--workflow FILE` | (Pflicht) | Workflow-Definitionsdatei |
| `--output FILE.json` | `<project>_generated.json` | Ausgabedatei |
| `--project KEY` | `TEST` | Jira-Projekt-Key |
| `--issues N` | `100` | Anzahl zu generierender Issues |
| `--from-date YYYY-MM-DD` | `2025-01-01` | Frühestes Erstellungsdatum |
| `--to-date YYYY-MM-DD` | `2025-12-31` | Spätestes Übergangsdatum |
| `--issue-types TYPE:W …` | `Feature:0.6 Bug:0.3 Enabler:0.1` | Issue-Typen mit Gewichtung |
| `--completion-rate FLOAT` | `0.7` | Anteil abgeschlossener Issues (0–1) |
| `--todo-rate FLOAT` | `0.15` | Anteil offener Issues in To-Do-Stages (0–1) |
| `--backflow-prob FLOAT` | `0.1` | Wahrscheinlichkeit für Rückschritte (0–1) |
| `--seed INT` | (zufällig) | Seed für reproduzierbare Ausgabe |
| `--mean-cycle-days FLOAT` | (keiner) | Mittlere Cycle-Time in Tagen (lognormal) |
| `--std-cycle-days FLOAT` | (30 % des Mittelwerts) | Standardabweichung der Cycle-Time |
| `--pattern MUSTER` | `none` | Flow-Antipattern: `none` / `triangle` / `flat_triangle` / `cluster` / `batch` |
| `--pi-duration-weeks INT` | `12` | PI-Zyklus-Länge in Wochen (für `cluster`/`batch`) |
| `--realism 0–100` | `0` | Unordnung der Statuswege (Sprünge, Abbrüche, Parken, Schleifen, Wiedereröffnung); ca. 70 wie ein echter ART |
| `--continue OLD.json` | (keiner) | Früheren Abzug fortschreiben bis `--to-date` (seit 0.39.0); `--issues` = Zahl NEUER Vorgänge, `--rate-per-day` Alternative |
| `--rate-per-day FLOAT` | (Rate des ersten Fensters) | Mit `--continue`: neue Vorgänge je Tag |

## Flow-Muster

Mit `--mean-cycle-days` und `--pattern` simulierbare Antipatterns:
`triangle` (CT steigt linear), `flat_triangle` (Anstieg flacht ab),
`cluster` (Lieferungen am PI-Ende häufen sich), `batch` (PI-Clustering + hohe CT-Varianz).

## Realistische Statuswege (seit 0.38.0)

Ein echter ART läuft nicht brav durch alle Stufen. Gemessen am echten ART_A (458 Vorgänge,
9 Stages): 40 verschiedene Übergangspaare, 12 % rückwärts, 7,5 % Selbstschleifen, 358
Sprünge über mindestens eine Stufe, 149 Eintritte in die Endstufe ohne Abschluss, Median
4 Übergänge je Vorgang. Der Generator vor 0.38.0 lieferte 11 Paare, 0 % Schleifen, Median 7.

`--realism` (0–100) skaliert acht Störungen des Pfads: Sprünge über Stufen, Abbrüche direkt
in die Endstufe, Parken in einer Nebenstage (erkannt am Namen: Blocker, Blocked, On Hold,
Waiting …), Selbstschleifen, Rückschritte über mehrere Stufen, Wiedereröffnung, Start nicht in
der ersten Arbeitsstufe und der Weg vom Abschluss in die Endstufe (Releasing → Done). **0 ist
das bisherige Verhalten** (nur `--backflow-prob`), **ca. 70 trifft den echten ART_A** — die
Kalibrierung ist per Test festgehalten. Pfad und Zeit sind getrennt: Die Störungen wirken in
jedem Modus, auch unter den Flow-Mustern, bei denen die Cycle-Time auf den längeren oder
kürzeren Pfad verteilt wird.

Das Portfolio-Szenario erzeugt seine sechs ARTs seit 0.38.0 mit Realismus 60 (Profilfeld
`realism`, je ART übersteuerbar). Seeds erzeugen seit 0.38.0 andere Daten als vorher — die
Würfelreihenfolge hat sich geändert.

## Fortschreibung — der zweite Abzug (seit 0.39.0)

Ein erzeugter Rohdatensatz ist ein Abzug zum Stichtag T1. `--continue` erzeugt den Abzug,
den man an T2 gezogen hätte — ganz so, wie wenn man zweimal manuell Daten abgezogen hätte:

```bash
python -m testdata_generator --workflow workflow.txt --continue ART_A.json --to-date 2026-03-01
```

- **Vergangenheit unantastbar:** Schlüssel, Anlagedatum und alle Übergänge bis T1 bleiben
  byteidentisch; geschlossene und abgebrochene Vorgänge werden gar nicht angefasst.
- **Offene Vorgänge laufen weiter:** ab T1 neue Übergänge nach demselben Pfad- und Zeitmodell
  (Realismus, Backflow, Cycle-Time), bis sie fertig sind oder T2 erreicht ist — was nach T2
  läge, bleibt offen.
- **Neue Vorgänge** kommen in (T1, T2] dazu, Schlüssel laufen weiter; Anzahl aus der Rate des
  ersten Fensters, oder `--issues N` bzw. `--rate-per-day X`.
- **Reproduzierbar:** derselbe Seed und dasselbe T2 ergeben denselben Abzug; eine Kette
  T1 → T2 → T3 behält jeden früheren Stand vollständig.

Dafür schreibt der Generator seit 0.39.0 einen Eintrag `generator` in den JSON-Envelope
(Stichtage, Seed, Regler, Stages); `transform_data` liest nur `issues` und bleibt unberührt.
Ein Datensatz ohne den Eintrag (älter oder ein echter Export) lässt sich fortschreiben, wenn
die Regler mitgegeben werden — T1 ist dann der jüngste Zeitstempel. Ausgabe:
`<name>_<T2>.json` neben der Quelle, oder `--output`. GUI: Knopf **Fortschreiben…** neben
**Generieren** (Bis-Datum und Realismus aus dem Formular).

**Ganzer Datenraum (seit 0.40.0):** `--scenario portfolio --continue demo/ --to-date T2`
schreibt das Demo-Portfolio an Ort und Stelle fort: jeder Roh-Abzug unter `raw/` läuft weiter
(eine veraltete Quelle wie Beta-3 bleibt genau so veraltet), transform_data schreibt
IssueTimes/Transitions/CFD neu, Solution-, Portfolio- und PI-Config wandern mit gleicher
Fensterlänge auf T2, und die Snapshots rotieren: das bisherige `snapshot_now.json` wird
`snapshot_prev.json`, ein neues `snapshot_now.json` wird eingefroren — das Delta-Briefing zeigt
dann echte vergangene Zeit statt der gestellten Zwei-Wochen-Story. Register bleiben unverändert.
GUI: **Szenario fortschreiben…** (Bis-Datum aus dem Formular).

## Workflow-Datei

Dasselbe Format wie in `transform_data`:

```
CanonicalStageName:Alias1:Alias2
<First>StageName
<Closed>StageName
```

## Ausgabe und Weiterverarbeitung

```bash
# Generieren
python -m testdata_generator --workflow workflow.txt --project ART_TEST --seed 1

# Direkt mit transform_data verarbeiten
python -m transform_data ART_TEST_generated.json workflow.txt
```

Die generierte JSON-Datei enthält Jira-Changelog-Historien mit Status-Übergängen
entlang des definierten Workflows. `transform_data` verarbeitet sie zu
`IssueTimes.xlsx`, `CFD.xlsx` und `Transitions.xlsx`.

## Architektur

```
testdata_generator/
├── __main__.py          # Dispatcher: GUI ohne Argumente, CLI mit Argumenten
├── cli.py               # run_generate() + argparse CLI
├── generator.py         # Kernlogik: Issue-Simulation (Zeit auf den Pfad)
├── paths.py             # Stage-Pfade: Realismus-Störungen, Parkstufe (0.38.0)
├── continuation.py      # Fortschreibung: zweiter Abzug, Envelope-Metadaten (0.39.0)
├── scenario_continue.py # Szenario-Fortschreibung mit Snapshot-Rotation (0.40.0)
└── workflow_parser.py   # Re-Export von transform_data.workflow
```

## Tests

```bash
python -m pytest tests/testdata_generator/
```
