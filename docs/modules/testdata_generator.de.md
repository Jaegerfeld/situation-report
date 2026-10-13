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
| `--realism 0–100` | `0` | Unordnung der Statuswege (Sprünge, Abbrüche, Parken, Schleifen, Wiedereröffnung); ca. 70 wie ein echter ART |
| `--continue OLD.json` | (keiner) | Früheren Abzug fortschreiben bis `--to-date` (seit 0.39.0); `--issues` = Zahl NEUER Vorgänge, `--rate-per-day` Alternative |
| `--rate-per-day FLOAT` | (Rate des ersten Fensters) | Mit `--continue`: neue Vorgänge je Tag |

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

**GUI:** Der Bereich *Demo-Portfolio* unten im Fenster erzeugt das komplette
Szenario in einen Ordner deiner Wahl (das Seed-Feld wird übernommen, Standard
42) — **Portfolio-Report öffnen** rendert den Portfolio-Report, **Delta-
Briefing öffnen** macht aus dem mitgelieferten Paar `snapshot_prev/now.json`
das „Was hat sich geändert?"-Briefing, **Konferenzmappe öffnen** den
VSC-Pre-Read; alles öffnet im Browser. Zwei Klicks
vom leeren Ordner zur vollständigen Portfolio-Evaluation, ganz ohne
Kommandozeile.

**Kommandozeile:**

```bash
python -m testdata_generator --scenario portfolio --output demo/ --seed 42
```

Erzeugt in einem Schritt ein vollständiges, konsistentes Demo-Portfolio: zwei
Solutions mit je drei ARTs, inklusive aller Artefakte der Verarbeitungskette —
Workflow-Dateien, Roh-Jira-JSON, `IssueTimes`/`CFD`/`Transitions`-Arbeitsmappen,
zwei Solution-Configs (Solution Beta mit eigener `stage_map`, Schema 2), je
Solution ein ROAM-Risiko-Register (`risks_alpha.json`/`risks_beta.json`),
ein NFR-/Runway-Register (`nfr_alpha.json`/`nfr_beta.json`) und eine
Capability-Map (`capabilities_alpha.json`/`capabilities_beta.json`) und ein
Dependency-Register (`dependencies_alpha.json`/`dependencies_beta.json`) und
ein Decision-/Assumption-Log (`decisions_alpha.json`/`decisions_beta.json`),
eine Portfolio-Config, eine PI-Config und ein README mit den eingebauten
Geschichten.
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
- **ROAM-Board**: beide Register zusammen enthalten neun Risiken; zwei
  Owned-Risiken sind bewusst alt (45/50 Tage) — die Aging-Hervorhebung
  springt an.
- **NFR & Runway**: sechs NFRs und vier Runway-Elemente; Betas API-NFR ist
  verletzt und ein Runway-Element eine überfällige Lücke — das Dashboard
  zeigt Rot.
- **Capability-Map**: sechs Capabilities; Betas Data-Insights-Capability ist
  kritisch (schwache Quelle) und eine Alpha-Capability hat keinen
  beitragenden ART — als uncovered markiert.
- **Dependency-Heatmap**: fünf Abhängigkeiten; Alpha-1 → Alpha-3 ist
  blockiert und überfällig (der Ausreißer liefert nicht), Beta-1 → Alpha-1
  ist eine Cross-Solution-Integration — im Portfolio-Report sichtbar.
- **Decision-Log**: drei Entscheidungen und zwei Annahmen; Alphas
  Stage-Map-Entscheidung ersetzt eine ältere (supersedes), Betas offene
  Annahme hat ihr Prüfdatum überschritten — rot als „review due" markiert.
- **Flussproblem-Backlog (B6, VSC)**: `flow_problems_alpha/beta.json` —
  FP-A1 und FP-B1 haben 3 bzw. 4 Konferenzen überlebt (das
  Workshop-Muster „geloggt, nie mitigiert" — rot markiert), FP-B1 ist
  Cross-VS; `--conference mappe.html` rendert die Konferenzmappe.
- **Strategic Themes & Roadmap (B7, VSC)**: `themes_alpha/beta.json` —
  Alphas Theme „Green operations" ist verwaist (declared & forgotten),
  EP-A9 ist eine Zombie-Initiative; die Matrix zeigt Trains ×
  P1·P2·Y1·Y2·Y3. Im Delta-Briefing: EP-A9 verlor sein Theme, EP-B2
  wurde von P2 nach P1 gezogen (*updated roadmaps*).
- **SLO & Error-Budgets**: `slo_alpha.json`/`slo_beta.json` — Betas
  „Order Sync API" reißt ihr SLO, Alphas „Checkout" hat sein Budget fast
  aufgebraucht (at risk).
- **DORA & Code-Qualität**: `dora_alpha.json`/`dora_beta.json` — ART
  Beta-3 ist auch im Delivery-Bild low (CFR 38 %, MTTR 30 h, Coverage
  31 %, Rating D); erzeugbar/austauschbar via `python -m sources fetch`
  (Provider: file, prometheus, github, gitlab, sonarqube — kombinierbar).
- **Delta-Briefing**: `snapshot_prev.json` (dieselbe Welt zwei Wochen
  früher) und `snapshot_now.json` liegen dem Szenario bei —
  `python -m portfolio --delta snapshot_prev.json snapshot_now.json` zeigt
  den Durchsatz seither, Beta-3s Konfidenz-Verfall medium → low, AD-1s
  Eskalation at_risk → blocked, das neue Risiko BR-2 sowie Runway-Lücke und
  Annahme AS-B1 als frisch überfällig.

Der Ordner ist direkt verwendbar: `python -m portfolio demo/portfolio.json`
erzeugt den Portfolio-Report; die Solution-Configs funktionieren auch einzeln.

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
├── generator.py         # Kernlogik: Issue-Simulation (Zeit auf den Pfad)
├── paths.py             # Stage-Pfade: Realismus-Störungen, Parkstufe (0.38.0)
├── continuation.py      # Fortschreibung: zweiter Abzug, Envelope-Metadaten (0.39.0)
├── scenario_continue.py # Szenario-Fortschreibung mit Snapshot-Rotation (0.40.0)
└── workflow_parser.py   Re-Export von transform_data.workflow
```

## Tests

```bash
python -m pytest tests/testdata_generator/
```

## Hinweis: Zufällige Cycle-Time-Verteilung

Der Generator stellt sicher, dass abgeschlossene Issues **vor** dem konfigurierten `to-date` abschließen. Das Erstellungsdatum wird dazu aus einem eingeschränkten Fenster `[from-date, latest_start]` gesampelt, wobei `latest_start` genug Puffer für die maximale Cycle-Time lässt. Dadurch entsteht im Flow Time Scatter-Plot eine gleichmäßig verteilte, zufällige Punktwolke statt einer absteigenden Geraden (Right-Censoring-Artefakt).
