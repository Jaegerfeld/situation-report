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

## Capability-Map & -Health (optional)

Eine Solution-Config kann über `"capabilities": "pfad/zu/capabilities.json"`
auf eine Capability-Map verweisen; der Report rendert dann unter der
Qualitätstabelle eine **Capability Map & Health**-Tabelle (PDF: eigene Seite).
Ein Portfolio aggregiert die Maps aller Member-Solutions und ergänzt eine
**Solution**-Spalte. Die Map:

```json
{
  "capabilities": [
    {
      "id": "C-1",
      "title": "Data Insights & Reporting",
      "health": "critical",
      "arts": ["ART Beta-3"],
      "owner": "ART Beta-3",
      "assessed_on": "2026-08-26",
      "notes": "optional"
    }
  ]
}
```

`health` ist einer von `healthy` / `at_risk` / `critical` — **von Menschen
bewertet** im PI-Planning/-Review (`assessed_on` hält fest, wann). `arts`
benennt die beitragenden Member-ARTs; eine Capability ohne beitragenden ART
wird als **uncovered** markiert (Geschäftswert, den niemand liefert), und ein
ART-Name, der nicht unter den Members der Solution ist, erzeugt eine
Drift-Warnung im Log. Kritische Capabilities sortieren nach oben,
Health-Zellen sind farbig; der Titel zählt critical/at risk/uncovered. `owner`
benennt ein **Team, keine Person**. Die Capability-Map (Geschäftsfähigkeiten)
ist bewusst **nicht** die `stage_map` (Workflow-Status) — andere Dimension,
andere Quelle. Fehlende oder defekte Dateien werden geloggt und übersprungen.

## ROAM-Risk-Board (optional)

Eine Solution-Config kann über `"risks": "pfad/zu/risks.json"` auf ein
Risiko-Register verweisen; der Report rendert dann unter Qualitätstabelle und
Capability-Map ein **ROAM-Board** (PDF: eigene Seite). Ein Portfolio aggregiert die Register
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

## Dependency-/Integrations-Heatmap (optional)

Eine Solution-Config kann über `"dependencies": "pfad/zu/dependencies.json"`
auf ein Dependency-Register verweisen; der Report rendert dann unter dem
NFR-Dashboard eine **Dependency & Integration Heatmap** (PDF: eigene Seite).
Ein Portfolio aggregiert die Register aller Member-Solutions und ergänzt in
der Detail-Tabelle eine **Solution**-Spalte. Das Register:

```json
{
  "dependencies": [
    {
      "id": "D-1",
      "title": "Billing-API-Contract",
      "from": "ART Alpha-1",
      "to": "ART Alpha-3",
      "status": "blocked",
      "due": "2026-08-18",
      "notes": "optional"
    }
  ]
}
```

`from` braucht etwas, das `to` liefert; `status` ist einer von `blocked` /
`at_risk` / `on_track` / `done`. Die **Heatmap** zählt offene Abhängigkeiten
(Status ≠ done) je from/to-Paar — jede Zelle trägt die Farbe ihres
dringlichsten Status. Darunter listet die Detail-Tabelle jede Abhängigkeit
(blocked zuerst); eine Abhängigkeit mit verstrichenem `due`, die nicht done
ist, erscheint **überfällig** (rote Datumszelle). Der Titel zählt
blocked/at risk/überfällig. `to` wird bewusst **nicht** gegen die
Member-Liste validiert — Integrationspunkte dürfen auf den ART einer anderen
Solution, einen Lieferanten oder ein Fremdsystem zeigen
(Cross-Solution-Abhängigkeiten werden im Portfolio-Report sichtbar).
Fehlende oder defekte Dateien werden geloggt und übersprungen.

## Decision-/Assumption-Log (optional)

Eine Solution-Config kann über `"decisions": "pfad/zu/decisions.json"` auf ein
Entscheidungs-Log verweisen; der Report rendert dann unter der
Dependency-Heatmap eine **Decision & Assumption Log**-Tabelle (PDF: eigene
Seite). Ein Portfolio aggregiert die Logs aller Member-Solutions und ergänzt
eine **Solution**-Spalte. Das Log — leichtgewichtig, ADR-artig:

```json
{
  "entries": [
    {
      "id": "ADR-1",
      "kind": "decision",
      "title": "Vendor-Sync-Service kaufen statt bauen",
      "status": "accepted",
      "owner": "ART Beta-1",
      "logged_on": "2026-04-05",
      "supersedes": "ADR-0",
      "notes": "optional"
    },
    {
      "id": "AS-1",
      "kind": "assumption",
      "title": "Datenqualität bessert sich mit dem nächsten Rollout",
      "status": "open",
      "review_by": "2026-08-23"
    }
  ]
}
```

`kind` ist `decision` (Status `proposed` / `accepted` / `superseded`) oder
`assumption` (Status `open` / `confirmed` / `invalidated`) — der Parser
erzwingt das passende Status-Set. `supersedes` muss einen Eintrag desselben
Logs benennen; so bleibt die Trade-off-Spur intakt. `review_by` gibt einer
Annahme ihr Verfallsdatum: eine **offene Annahme mit überschrittenem
Prüfdatum** sortiert nach oben und bekommt eine rote „review due"-Zelle — der
Anschlusspunkt für Red-Team-/Premortem-Sitzungen. `owner` benennt ein **Team,
keine Person**. Fehlende oder defekte Dateien werden geloggt und übersprungen.

## Delta-Briefing (D2, deterministischer Kern)

Zwei Befehle machen aus Report-Ständen ein „Was hat sich geändert?"-Briefing:

```bash
python -m portfolio portfolio.json --snapshot stand_jetzt.json
python -m portfolio --delta stand_vorher.json stand_jetzt.json --output delta.html
```

`--snapshot` friert den berechneten Report-Zustand (Kennzahlen je Einheit und
gepoolt, Quell-Qualität inkl. Konfidenz, alle fünf Governance-Register) als
kleines Schema-v1-JSON ein; `--as-of YYYY-MM-DD` setzt das Beobachtungsdatum
(Standard: heute). Ohne `--output`/`--pdf` wird nur der Snapshot geschrieben.

`--delta PREV NOW` braucht keine Config: Es vergleicht zwei Snapshots und
liefert das Briefing — Kennzahl-Deltas auf Anzeigegenauigkeit (unsichtbare
Float-Änderungen entfallen), Durchsatz im Zeitraum, Konfidenz-Wechsel je
Quelle und je Governance-Register neue/entfallene Einträge, Statusübergänge
(Verschlechterungen zuerst, rot; Verbesserungen grün) sowie **frisch
überfällige** Einträge (gegen das as-of-Datum beider Snapshots beurteilt —
nur echte Kipp-Punkte zählen). `--output *.md` schreibt Markdown, jede andere
Endung die eigenständige HTML-Seite, ohne `--output` geht Markdown nach
stdout. Ein Delta ohne Änderungen sagt das ausdrücklich — Stille ist
Information.

Das Markdown ist bewusst der Eingabe-Contract der optionalen LLM-Narration
(D2 Teil 2, noch nicht gebaut): Das LLM darf umformulieren, nie Zahlen
hinzufügen — die Zahlen entstehen hier, deterministisch.

**In der GUI:** Das Manager-Fenster trägt zwei passende Knöpfe — **Snapshot
speichern …** friert die aktuell konfigurierte Solution/das Portfolio in
eine JSON-Datei ein (Namensvorschlag mit Tagesdatum), und **Delta-Briefing
…** fragt nach Vorher- und Nachher-Snapshot und öffnet das Briefing im
Browser. Der Demo-Weg ist noch kürzer: Der Demo-Portfolio-Bereich des
Testdaten-Generators bekommt **Delta-Briefing öffnen** und rendert direkt
das mitgelieferte Paar `snapshot_prev/now.json`.

## Flussproblem-Backlog & Konferenzmappe (optional, B6)

`"flow_problems": "flow_problems.json"` rendert den **Flussproblem-
Backlog** — den wichtigsten Input der Value-Stream-Konferenz. Jedes
Problem trägt id, Titel, Status (`open`/`committed`/`resolved`/
`dropped`), die betroffenen `value_streams` (Cross-VS wird *abgeleitet*:
mehr als ein Stream), Einbringer, Owner-Team, `raised_on`, einen
`conferences`-Zähler (in wie vielen Konferenzen es auf dem Tisch war —
von Menschen gepflegt), `resolution_commitment` und `follow_up_pi`. Das
Workshop-Muster „geloggt, nie mitigiert, taucht nächstes PI wieder auf"
wird messbar: Ein ungelöstes Problem mit **≥ 3 Konferenzen** sortiert
nach oben und trägt einen roten Zähler.

Die **Konferenzmappe** bündelt die Sitzungs-Inputs zu einer leichten,
druckbaren Seite:

```bash
python -m portfolio portfolio.json --conference mappe.html --conference-date 2026-09-10
```

Input 1 · Aktuelle Daten (Summary + Quell-Qualität), Input 2 ·
Impediment-Backlog & Governance (Flussprobleme zuerst, dann ROAM und
Dependencies), Input 3 · Business Objectives (Capability-Map + SLOs),
Input 4 · Integrierte Roadmap & Strategic Themes (B7). Der vollständige
interaktive Report bleibt die Detailquelle. **In der GUI:** Der Knopf
*Konferenzmappe …* im Manager-Fenster schreibt dieselbe Seite für die
aktuell konfigurierte Solution (Dateiname schlägt das Tagesdatum vor)
und öffnet sie im Browser — von dort als PDF drucken; im
Demo-Portfolio-Bereich des Testdaten-Generators öffnet *Konferenzmappe
öffnen* die Demo-Mappe mit einem Klick.

## Strategic Themes & integrierte Roadmap (optional, B7)

`"themes": "themes.json"` gibt strategischen Themen ein strukturiertes
Zuhause und der Solution-Ebene ihre integrierte Roadmap:

```json
{
  "themes": [{"id": "T-1", "title": "Digital ordering end-to-end"}],
  "epics": [
    {"id": "EP-1", "title": "Self-service portal", "train": "ART A",
     "horizon": "P1", "theme": "T-1", "status": "in_progress"},
    {"id": "EP-9", "title": "Legacy rewrite", "train": "ART C",
     "horizon": "Y1"}
  ]
}
```

Horizonte folgen *nah granular, fern grob*: `P1 · P2 · Y1 · Y2 · Y3`.
**Orphan-Detection wirkt in beide Richtungen**: Ein Theme, auf das kein
Epic einzahlt, wird rot als *declared & forgotten* markiert (portfolioweit
beurteilt — ein Epic einer anderen Solution zählt), und ein Epic mit
**leerem** `theme` ist eine *Zombie-Initiative* (ein Tippfehler in der
Referenz ist ein Validierungsfehler, kein Zombie). Der Report rendert
Theme-Tabelle, Roadmap-Matrix (Zeilen = Trains, Spalten = Horizonte,
Zombies rot) und Zombie-Liste; die Konferenzmappe trägt sie als Input 4.
Roadmap-Epics fließen außerdem in D2-Snapshots — das Delta-Briefing
dokumentiert so die *updated roadmaps* je Konferenz (Horizont-
Verschiebungen, Statuswechsel; ein verlorenes Theme liest sich als
`→ zombie`).

## SLO- & DORA-Register (optional, C1/C2)

Eine Solution-Config kann zwei weitere Register referenzieren, beide vom
steckbaren `sources`-Framework erzeugt (Provider und das 30-Zeilen-Rezept
für neue Quellen: siehe dessen Modulseite):

- `"slo": "slo.json"` rendert **Service Levels & Error Budgets**: je SLO
  Ziel, aktueller SLI, Rest-Error-Budget (zentrale Regel: verbraucht =
  (100−SLI)/(100−Ziel)) und Status — met / at risk (< 25 % Restbudget) /
  breached / unknown, breached zuerst. Jede Datenquelle wird nach
  derselben Regel beurteilt.
- `"dora": "dora.json"` rendert **Delivery Performance (DORA) & Code
  Quality**: die vier DORA-Kennzahlen je Einheit, jede Zelle an den
  veröffentlichten Schwellen eingestuft (elite/high/medium/low),
  Gesamt-Tier = schwächste Kennzahl; darunter die Qualitätstabelle
  (Coverage, Maintainability-Rating, kritische Verstöße).

Jede Zeile behält ihre Datenquelle (kombinierbare Quellen); ein Portfolio
aggregiert Member-Register mit Solution-Spalte; defekte Dateien werden
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
├── capability_config.py Capability-Map (B1): Schema, parse/load/save
├── dependency_config.py Dependency-Register (B5): Schema, parse/load/save
├── decision_config.py Decision-/Assumption-Log (B4): Schema, parse/load/save
├── flow_problems_config.py Flussproblem-Backlog (B6): Schema, Survivor-Regel
├── themes_config.py   Strategic Themes/Roadmap (B7): Orphan-/Zombie-Regeln
├── slo_config.py      SLO-Register (C1): zentrale Budget-/Status-Regel
├── dora_config.py     Delivery-Register (C2): DORA-Tiers + Qualität
├── snapshot.py        Report-Snapshot (D2): Kennzahlen/Qualität/Governance einfrieren
├── delta.py           Delta-Briefing (D2): zwei Snapshots vergleichen, HTML/Markdown
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
