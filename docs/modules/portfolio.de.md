# portfolio

Fasst mehrere bereits konfigurierte ARTs zu einem kombinierten
**Large-Solution-** oder **Portfolio-**Report zusammen — als **Pooled** (die
Solution als ein System betrachtet) oder als **Vergleich** (Einheiten
nebeneinander). Nutzt die Metriken aus `build_reports`; die einzelnen
ART-Reports werden nur referenziert, nicht verändert.

**Status:** verfügbar (Alpha)

## Handbücher

| Sprache | Download |
|---------|----------|
| Deutsch (DE) | [Benutzerhandbuch](../portfolio_Benutzerhandbuch.pdf) |
| English (EN) | [User Manual](../portfolio_UserManual.pdf) |
| Română (RO) | [Manual de Utilizator](../portfolio_ManualUtilizator.pdf) |
| Português (PT) | [Manual do Utilizador](../portfolio_ManualUtilizador.pdf) |
| Français (FR) | [Manuel d'utilisation](../portfolio_ManuelUtilisateur.pdf) |

---

## Grundbegriffe

| Begriff | Bedeutung |
|---------|-----------|
| ART | Agile Release Train / Teamgruppe — die Ebene, auf der du in `build_reports` bereits berichtest. |
| Solution | Eine Gruppierung mehrerer ARTs (referenziert deren Projekt-Templates). |
| Portfolio | Eine Gruppierung mehrerer Solutions (Portfolio > Solutions > ARTs). |
| Pooled | Modus: Alle Issues werden zu **einem** Datensatz zusammengeführt — die Solution als ein System. |
| Vergleich | Modus: Jede Einheit (ART oder Solution) wird separat nebeneinander dargestellt. |

## Oberfläche

![Screenshot der Portfolio-GUI](../assets/Portfolio-GUI.png)

## Start

### GUI

```bash
python -m portfolio
```

Oder auf die Kachel **Solutions & Portfolios** links im SituationReport-Launcher
klicken.

### Kommandozeile

```bash
python -m portfolio solution.json --mode pooled --output report.html
# Vergleichsmodus / PDF-Ausgabe:
python -m portfolio solution.json --mode comparison --pdf report.pdf
```

Die Konfigurationsdatei (`solution.json`) listet die Mitglieder auf (ARTs bei
einer Solution, Solutions bei einem Portfolio) und wird in der GUI erstellt bzw.
bearbeitet.

## Report-Inhalte

Jeder Report beginnt mit der **Management-Summary** — eine Zeile je Einheit
(Pooled: die ganze Solution/das Portfolio): Items, abgeschlossen, offen (WIP),
Durchlaufzeit-Perzentile (Median/85./95.), der Ziel-CT-Anteil und die
**End-to-End-Lead-Time** (Created → Closed, Median/85.; im Pooled-Modus die
Solution-Lead-Time über alle ARTs).

Darunter zeigt die Tabelle **Data Quality per Source** je Quelle: Record-Zahl,
ihren **Anteil** am Gesamtvolumen, den Anteil ohne First Date, den offenen
Anteil, ob CFD-Daten geliefert wurden, den Datenstand — und eine
Ampel-**Konfidenz** (high/medium/low, Schwellen in `summary.py` dokumentiert).
Der Titel trägt den Abdeckungsgrad („x/y sources delivered data"). Im PDF ist
die Tabelle Seite 2.

Im **Comparison**-Modus werden Median-CT- und 95.-Perzentil-Zellen rot
hervorgehoben, wenn sie das 1,5-fache des Spalten-Medians übersteigen (ab drei
Zeilen) — die Frage „welche Einheit ist der Ausreißer?" beantwortet sich selbst.

## ROAM-Risk-Board (optional)

Eine Solution-Config kann über `"risks": "pfad/zu/risks.json"` auf ein
Risiko-Register verweisen; der Report rendert dann unter der Qualitätstabelle
ein **ROAM-Board** (PDF: eigene Seite). Ein Portfolio aggregiert die Register
aller Member-Solutions und ergänzt eine **Solution**-Spalte. Das Register:

```json
{
  "risks": [
    {
      "id": "R-1",
      "title": "Testumgebung noch nicht bestellt",
      "roam": "owned",
      "owner": "System Team",
      "impact": "high",
      "status_since": "2026-07-15",
      "notes": "optional"
    }
  ]
}
```

`roam` ist eine der Kategorien `resolved` / `owned` / `accepted` / `mitigated`,
`impact` eine von `high` / `medium` / `low`. Die Zeilen sind in R-O-A-M-Reihenfolge
gruppiert, Kategorie- und Impact-Zellen farbig. `status_since` (wann das Risiko
in seine aktuelle Kategorie kam) treibt das **Aging**: ein *Owned*-Risiko, das
älter als 30 Tage ist, bekommt eine rote „Since"-Zelle — Ownership ohne
Bewegung ist genau das, was das Board sichtbar machen soll. Der Titel zählt
Risiken gesamt, Owned und Aging. `owner` benennt ein **Team, keine Person**.
Eine fehlende oder defekte risks-Datei wird geloggt und übersprungen —
Governance-Daten brechen den Flow-Report nie.

## NFR-/Architecture-Runway-Dashboard (optional)

Eine Solution-Config kann über `"nfr": "pfad/zu/nfr.json"` auf ein NFR-Register
verweisen; der Report rendert dann unter dem ROAM-Board ein **NFR & Architecture
Runway**-Dashboard (PDF: eigene Seite, beide Tabellen gestapelt). Ein Portfolio
aggregiert die Register aller Member-Solutions und ergänzt eine
**Solution**-Spalte. Das Register:

```json
{
  "nfrs": [
    {
      "id": "N-1",
      "title": "API-Antwortzeit",
      "target": "p95 < 200 ms",
      "actual": "p95 = 340 ms",
      "status": "violated",
      "owner": "ART Beta-1"
    }
  ],
  "runway": [
    {
      "id": "RW-1",
      "title": "Automatisches Failover",
      "status": "gap",
      "needed_by": "2026-08-13",
      "owner": "ART Beta-2"
    }
  ]
}
```

Der NFR-`status` ist einer von `met` / `at_risk` / `violated`, der
Runway-`status` einer von `in_place` / `building` / `gap` — **von Menschen
bewertet** im PI-Planning/-Review; das Werkzeug rechnet Ziel gegen Ist bewusst
nicht selbst („das LLM textet, es rechnet nicht" gilt sinngemäß auch fürs
Werkzeug). Verletzte NFRs und Runway-Lücken sortieren nach oben, Status-Zellen
sind farbig; ein Runway-Element, dessen `needed_by` verstrichen ist, ohne dass
es `in_place` ist, erscheint als **überfällig** (rote Datumszelle). Der Titel
zählt NFRs (verletzt/at risk) und Runway-Elemente (Lücken/überfällig). `owner`
benennt ein **Team, keine Person**. Fehlende oder defekte Dateien werden
geloggt und übersprungen.

## Eigene Stage-Map (optional, Config-Schema 2)

Standardmäßig poolen unterschiedliche ART-Workflows in die drei kanonischen
Gruppen To Do / In Progress / Done. Eine Solution-Config kann stattdessen
eigene kanonische Stages definieren:

```json
"stage_map": {
  "stages": {
    "Backlog":   ["Funnel", "Analysis"],
    "In Arbeit": ["Implementing", "Review"],
    "Fertig":    ["Done", "Released"]
  },
  "first_stage": "In Arbeit",
  "closed_stage": "Fertig"
}
```

`first_stage`/`closed_stage` markieren die CFD-Grenzen. Nicht zugeordnete
Stages fallen mit protokollierter Warnung in `first_stage`. Configs ohne den
Block verhalten sich unverändert (v1-Dateien laden wie bisher).

## Architektur

```
portfolio/
├── __main__.py        Dispatcher: GUI ohne Argumente, CLI mit Argumenten
├── cli.py             run_solution_report() + argparse-CLI
├── solution_config.py Solution-/Portfolio-Konfiguration (Mitglieder, Modus, Terminologie)
├── risks_config.py    ROAM-Risiko-Register (B3): Schema, parse/load/save
├── nfr_config.py      NFR-/Runway-Register (B2): Schema, parse/load/save
├── aggregator.py      Zusammenführung auf Datensatz-Ebene + Rendering (HTML/PDF)
└── summary.py         Management-Summary + Datenqualität (A1/A2), Ausreißer (A3), ROAM-Board (B3), NFR-Dashboard (B2)
```

Nutzt `build_reports` (Loader, Metriken, Export) wieder. Die Aggregation erfolgt
per **Record-Pooling** — die ART-Issues werden auf Datensatz-Ebene
zusammengeführt und die bestehenden Metriken laufen unverändert darüber (ein
gepoolter Median ≠ der Mittelwert der Mediane).

## Tests

```bash
python -m pytest tests/portfolio/
```
