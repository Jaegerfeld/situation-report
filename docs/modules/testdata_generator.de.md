# testdata_generator

Erzeugt synthetische Jira-Issue-JSON-Dateien im Jira-REST-API-Format.
Die generierten Dateien sind direkt mit `transform_data` verarbeitbar und
eignen sich für Entwicklung, Tests und Demonstrationen ohne echte Jira-Daten.

**Status:** verfügbar (Beta)

## Handbücher

| Sprache | Download |
|---------|----------|
| Deutsch (DE) | [Benutzerhandbuch](../testdata_generator_Benutzerhandbuch.pdf) |
| English (EN) | [User Manual](../testdata_generator_UserManual.pdf) |
| Română (RO) | [Manual de Utilizator](../testdata_generator_ManualUtilizator.pdf) |
| Português (PT) | [Manual do Utilizador](../testdata_generator_ManualUtilizador.pdf) |
| Français (FR) | [Manuel d'utilisation](../testdata_generator_ManuelUtilisateur.pdf) |

---

## Oberfläche

![Screenshot des Testdata Generator](../assets/Testdata-Generator-GUI.png)

## Start

### GUI

```bash
python -m testdata_generator
```

Oder über die Startdatei im portablen Paket:

- **Windows:** `TestdataGenerator.bat`
- **macOS:** `TestdataGenerator.command`
- **Linux:** `TestdataGenerator.sh`

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
| `--scenario portfolio` | (keiner) | Erzeugt das komplette Demo-Portfolio statt einer einzelnen JSON (siehe unten) |
| `--workflow FILE` | (Pflicht ohne `--scenario`) | Workflow-Definitionsdatei |
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

## Flow-Muster

Mit `--mean-cycle-days` und `--pattern` lassen sich typische Flow-Antipatterns simulieren:

| Muster | Beschreibung |
|--------|-------------|
| `none` | Zufällige Cycle-Time ohne Muster (Standard) |
| `triangle` | Cycle-Time steigt linear über die Zeit — Dreieck im Scatterplot |
| `flat_triangle` | Wie `triangle`, aber der Anstieg flacht am Ende ab (tanh) |
| `cluster` | Lieferungen häufen sich in den letzten 2 Wochen jedes PI (Beta-Verteilung) |
| `batch` | PI-Clustering mit stark variierender Cycle-Time (0,1× bis 3× Mittelwert) |

```bash
# Triangle-Muster mit mittlerer Cycle-Time von 30 Tagen
python -m testdata_generator \
    --workflow workflow.txt \
    --pattern triangle \
    --mean-cycle-days 30 \
    --std-cycle-days 10 \
    --output triangle.json
```

## Portfolio-Szenario

```bash
python -m testdata_generator --scenario portfolio --output demo/ --seed 42
```

Erzeugt in einem Schritt ein vollständiges, konsistentes Demo-Portfolio: zwei
Solutions mit je drei ARTs, inklusive aller Artefakte der Verarbeitungskette —
Workflow-Dateien, Roh-Jira-JSON, `IssueTimes`/`CFD`/`Transitions`-Arbeitsmappen,
zwei Solution-Configs (Solution Beta mit eigener `stage_map`, Schema 2), eine
Portfolio-Config, eine PI-Config und ein README mit den eingebauten Geschichten.
Das Datenfenster liegt relativ zum Erzeugungsdatum, damit die Qualitäts-Ampel
des Portfolio-Reports die Quellen als aktuell einstuft.

Eingebaute Geschichten (deterministisch je Seed):

- **ART Alpha-3** ist der Ausreißer (ca. 3× Cycle Time) — im Comparison-Report
  der Solution Alpha rot hervorgehoben.
- **ART Beta-3** liefert schwache Daten (kein CFD, kaum begonnene Issues,
  Datenstand 60 Tage alt) — Konfidenz `low` in der Qualitätstabelle,
  Abdeckung unter 100 %.
- **Solution Beta** poolt über eine eigene `stage_map`; Solution Alpha nutzt
  den Default-Klassifikationspfad.

Der Ordner ist direkt verwendbar: `python -m portfolio demo/portfolio.json`
erzeugt den Portfolio-Report; die Solution-Configs funktionieren auch einzeln.

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

### Direkt-Report (GUI)

Nach erfolgreicher Generierung wird in der GUI der Button **„Report erstellen"**
aktiv. Ein Klick führt `transform_data` und `build_reports` direkt aus und
öffnet einen kombinierten Report (eine HTML-Seite mit allen Metriken) im
Browser. Der Report deckt den **gesamten generierten Zeitraum** ab — ohne
Datumsfilter.

## Architektur

```
testdata_generator/
├── __main__.py          Dispatcher: GUI ohne Argumente, CLI mit Argumenten
├── cli.py               run_generate() + argparse CLI
├── generator.py         Kernlogik: Issue-Simulation
├── scenario.py          Portfolio-Szenario (2 Solutions × 3 ARTs, alle Artefakte)
└── workflow_parser.py   Re-Export von transform_data.workflow
```

## Tests

```bash
python -m pytest tests/testdata_generator/
```

## Hinweis: Zufällige Cycle-Time-Verteilung

Der Generator stellt sicher, dass abgeschlossene Issues **vor** dem konfigurierten `to-date` abschließen. Das Erstellungsdatum wird dazu aus einem eingeschränkten Fenster `[from-date, latest_start]` gesampelt, wobei `latest_start` genug Puffer für die maximale Cycle-Time lässt. Dadurch entsteht im Flow Time Scatter-Plot eine gleichmäßig verteilte, zufällige Punktwolke statt einer absteigenden Geraden (Right-Censoring-Artefakt).
