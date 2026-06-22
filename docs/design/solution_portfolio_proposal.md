# Entwurf: Large-Solution- & Portfolio-Reports

> **Status:** Vorschlag / in Arbeit · **Branch:** `feature/solution-portfolio`
> **Nicht für `main`**, bis Robert die Übernahme ausdrücklich befiehlt (so in der Idee festgelegt).
> Dieses Dokument ist zugleich der spätere *Überlegungen*-Beleg für die `Ideen/Archiv`-Ablage,
> falls/sobald die Idee umgesetzt ist.

Quelle der Idee: `feedback/Ideen/Portfolio und solution eben.txt`.

---

## 1. Ziel

Bisher betrachtet SituationReport immer **genau einen** Team-Verbund / ART. Neu: aggregierte
Reports für **ganze Large Solutions** (einige ARTs) und **ganze Portfolien** (viele ARTs)
erzeugen und bereitstellen.

---

## 2. Bereits festgelegt vs. offen

Die Idee legt das meiste schon fest — das ist **kein** Diskussionspunkt mehr, sondern Vorgabe:

| Aspekt | Vorgabe aus der Idee |
|---|---|
| Einstiegs-UI | Geteilt: **links** Verwaltung + Reports von Large Solutions / Portfolien (neu), **rechts** das Bestehende (ART / Team-Verbünde in LeSS, Nexus). |
| Gruppierung | Solutions fassen **bereits fertig konfigurierte ARTs** zusammen — „durch die schon eingeführten Templates". |
| Verwaltung | Man gibt an, welche ARTs zu welcher Solution gehören. |
| Vorgehen | Eigener **Langzeit-Branch**, bleibt bis zum ausdrücklichen Merge-Befehl bestehen. |

**Ausdrücklich offen** (Zitat: „Dafür müssten wir mal vorschläge erarbeiten"):
die **Reports auf Solution-/Portfolio-Ebene** — welche, und wie aggregiert. Darauf liegt der
Fokus dieses Entwurfs (Abschnitt 5–6).

---

## 3. Architektur-Überblick

```
                 ┌─────────────────────────────────────────────┐
                 │  Neue Einstiegs-UI (Launcher, geteilt)       │
                 │                                              │
   NEU  ◄────────┤  Large Solutions / Portfolien │  ART /       │────► BESTEHEND
                 │  (Verwaltung + agg. Reports)  │  Team-Verbund │
                 └─────────────────────────────────────────────┘
                              │                        │
                              ▼                        ▼
                   Solution-Konfig (neu)        Project-Template (bestehend)
                   = Liste von ART-Templates     = ein konfigurierter ART-Report
                              │
                              ▼
                   Aggregator  ──►  bestehende build_reports-Metriken (wiederverwendet)
                              │
                              ▼
                   Solution-/Portfolio-Report (HTML/PDF)
```

**Modul-Platzierung — Empfehlung:** ein **neues Modul `portfolio`** (Geschwister von
`build_reports`), mit eigenem GUI/CLI. Begründung: build_reports bleibt schlank und auf
„ein Datensatz → ein Report" fokussiert; das neue Modul orchestriert *mehrere* ART-Datensätze
und ruft die build_reports-Metriken als Bibliothek auf. Es fügt sich als weitere Karte in die
Launcher-Registry ein.

*Alternative (verworfen für den Start):* build_reports um einen „Solution-Modus" erweitern —
vermischt Verantwortlichkeiten und erschwert die getrennte Verwaltungs-UI.

---

## 4. Datenmodell & Solution-Template-Mechanismus

Eine **Solution-Konfiguration** ist eine **eigene** JSON-Datei (eigenes `schema`/`app`,
`portfolio.solution_config`) — bewusst **nicht** in die `project_template`-Hülle gefaltet:
Die Hülle existiert, um die *Modul-Pipeline-Configs eines einzelnen ARTs* (build_reports,
transform_data …) in einer Datei zu mergen und Geschwister-Abschnitte zu erhalten. Eine Solution
spannt dagegen *mehrere* ARTs — der Merge-Zweck der Hülle trägt hier nicht, und ein Solution-File
in ein ART-GUI zu laden würde nur Murks ergeben. Die Solution-Konfig *referenziert* ART-Templates
genauso, wie ein Portfolio Solution-Konfigs referenziert.

**Solution-Template-Mechanismus:** Die Solution-Konfig **ist** das Solution-Template — sie hat
dieselben Bausteine wie das ART-Template (laden/speichern/`to_dict`, GUI Save/Load) und ist damit
ein *wiederverwendbares, referenzierbares* Artefakt. Ein Portfolio bindet Solutions exakt so ein,
wie eine Solution ihre ARTs einbindet (`members[].template`). So gilt derselbe Template-/Referenz-
Mechanismus auf ART- **und** Solution-Ebene.

```jsonc
{
  "schema": 1,
  "app": "situation_report",
  "kind": "solution",            // "solution" | "portfolio"
  "name": "Payments Solution",
  "framework": "SAFe",           // SAFe | LeSS | Nexus  (Terminologie, s. §7)
  "members": [                    // Verweise auf bestehende ART-Templates
    { "name": "ART Alpha", "template": "C:/…/ART_Alpha.json" },
    { "name": "ART Beta",  "template": "C:/…/ART_Beta.json"  }
  ],
  "report": {                    // gemeinsamer Zeitraum/Optionen für den agg. Report
    "from_date": "2025-01-01",
    "to_date":   "2025-12-31",
    "modes": ["pooled", "comparison"]
  }
}
```

- **Portfolio** = dieselbe Struktur mit `kind: "portfolio"`, dessen `members` auf
  Solution-Konfigs (statt direkt auf ART-Templates) zeigen → natürliche Schachtelung
  Portfolio ▸ Solutions ▸ ARTs.
- Jeder Member zeigt auf ein **unverändertes** ART-Project-Template. Die Solution-Konfig
  fügt nichts an den ARTs hinzu, sie *referenziert* nur — Single Source of Truth bleibt
  das ART-Template.

---

## 5. Aggregations-Design (der Kern)

Es gibt **zwei fachlich verschiedene Bedürfnisse**. Vorschlag: beide als getrennte
**Report-Modi** anbieten.

### 5a. Modus „Pooled / Roll-up" — *„Die Solution als ein System"*
Alle Issues aller ARTs werden zu **einem** Datensatz zusammengeführt und die bestehenden
Metriken laufen unverändert darüber. Ergebnis: Gesamt-Throughput, Gesamt-Flow-Time-Verteilung
usw. der ganzen Solution.

**Umsetzung (günstig & wiederverwendend, am Code verifiziert):**
`ReportData.issues` der einzelnen ARTs **auf Record-Ebene konkatenieren** (jeder
`IssueRecord` trägt bereits `project` und `Group`), dann die vorhandenen Metrik-Plugins
darauf anwenden. Die Metrik-Schicht ist dafür gebaut: `source_prefix` ist bereits
mehr-projekt-fähig, und z. B. `flow_velocity` zählt rein record-/datumsbasiert → poolt korrekt.

> **Zwingende Regel:** Immer auf **Record-Ebene** poolen, **nie** Pro-ART-Statistiken mitteln.
> Pooled-Median ≠ Mittel-der-Mediane. Additive Metriken (Velocity, WIP/Flow Load, Throughput)
> liefern beidseitig dasselbe; **verteilungsbasierte** (Flow Time, Flow Distribution) stimmen
> nur bei Pooling der Roh-Issues.

> **Workflow-Kompatibilität (wichtige Einschränkung):** Datums-getriebene Metriken
> (**Flow Time**, **Flow Velocity**) poolen unabhängig vom Workflow sauber. **Stage-abhängige**
> Metriken (**CFD**, **Flow Distribution**, **Flow Load**) hängen an der `stages`-Liste; haben
> zwei ARTs unterschiedliche Workflows, ist ein Pooling nur mit gemeinsamem Stage-Mapping
> sinnvoll (siehe `stage_groups`). → Deshalb startet Phase 1 mit den datums-getriebenen Metriken.

### 5b. Modus „Comparison / Per-ART" — *„Welcher ART ist der Ausreißer?"*
Pro ART wird der Report **getrennt** berechnet und die Ergebnisse **nebeneinander**
dargestellt (Small Multiples / gemeinsame Achsen / Vergleichstabelle). Kein Pooling —
hier ist gerade der Unterschied zwischen den ARTs die Aussage.

---

## 6. Vorgeschlagene Reports je Metrik

| Metrik | Pooled (5a) | Comparison (5b) |
|---|---|---|
| **Flow Velocity / Throughput** | Summe abgeschlossener Items pro PI/Woche über die ganze Solution | Items pro PI je ART, gruppierte Balken |
| **Flow Time** | gepoolte Verteilung (Median/85./95. Perzentil der Solution) | Boxplot/Scatter je ART nebeneinander, gemeinsame Achse |
| **Flow Load (WIP)** | Gesamt-WIP der Solution über Zeit | WIP-Linie je ART übereinander |
| **Flow Distribution** | gepoolter Anteil je Issue-Typ (Workflow-kompatibel) | Anteile je ART, gestapelt |
| **CFD** | nur bei gemeinsamem Stage-Mapping; sonst Comparison | CFD je ART (Kachel-Grid) |

Zusätzlich denkbar (Phase ≥3): eine **Solution-Übersichtskachel** (Velocity-Trend,
Flow-Time-Perzentile, ART-Anzahl) als Management-Summary; Portfolio = Roll-up der Solutions.

---

## 7. UI & i18n

- **Einstiegs-UI:** Launcher um die geteilte Ansicht erweitern (links neu, rechts bestehend),
  oder als eigene `portfolio`-Karte starten. Konkrete Variante in Phase 2.
- **i18n:** alle neuen Strings über das bestehende 5-Sprachen-Schema (DE/EN/RO/PT/FR) wie im
  übrigen Launcher.
- **Terminologie:** das bestehende `terminology`-Modul (SAFe/Global) respektieren. SAFe spricht
  von *Large Solution* / *Portfolio*; bei LeSS/Nexus sind es *Verbünde* mehrerer Teams.
  Framework-Feld (§4) steuert die Beschriftung.

---

## 8. Phasen-Roadmap

**Phase 1 — dünner vertikaler Durchstich — ✅ UMGESETZT (Modul `portfolio`):**
eine Beispiel-Solution aus 2 vorhandenen ART-Templates → Modus *Pooled* → die zwei
datums-getriebenen Metriken **Flow Velocity + Flow Time** → fertiger HTML-Report. Reuse von
build_reports. Noch keine Verwaltungs-UI (Solution-Konfig als Datei/CLI).

- `portfolio/solution_config.py` — Solution-Konfig (Schema v1) laden/validieren; referenziert
  bestehende ART-Templates (oder direkt IssueTimes).
- `portfolio/aggregator.py` — `build_pooled_report_data()` führt die ART-Records zu einem
  `ReportData` zusammen; `render_pooled_html()` lässt die bestehenden Metriken darüber laufen.
- `portfolio/cli.py` / `__main__.py` — `python -m portfolio <config.json> --output report.html`.
- Beispiel: `docs/design/solution_config.example.json`.
- **Verifiziert (echte Daten):** 2 ARTs mit unterschiedlichen Workflows (9 bzw. 8 Stages),
  861 gepoolte Issues, beide Metriken, gültiger HTML-Report — bestätigt, dass datums-getriebene
  Metriken workflow-übergreifend sauber poolen.

**Phase 2 — Verwaltungs-UI & Comparison-Modus:** geteilte Einstiegs-UI, Solutions anlegen/ARTs
zuordnen, Comparison-Modus (Small Multiples), restliche poolbare Metriken.

- **Comparison-Modus — ✅ UMGESETZT:** `render_comparison_html()` lädt jeden ART getrennt und
  gruppiert die Figures pro Metrik (jede Figure mit ART-Name via `source_prefix`).
  CLI: `python -m portfolio <config.json> --mode comparison`.
- **Erweiterte Metriken — ✅ UMGESETZT:** Default-Metriksätze pro Modus.
  - *Pooled:* Flow Velocity, Flow Time, **Flow Distribution** (alle record-basiert, poolen sauber).
    Flow Load ist hier bewusst **nicht** Default — es gruppiert offene Issues nach aktueller
    Stage, sodass Pooling verschiedener Workflows unvergleichbare Stage-Spalten mischt;
    nur per `--metrics flow_load` und nur bei gemeinsamem Workflow sinnvoll.
  - *Comparison:* zusätzlich **Flow Load** (je ART getrennt → unproblematisch).
  - Verifiziert (echte Daten, 2 ARTs): Pooled = 3 Metrik-Gruppen, Comparison = 4 Gruppen / 15 Figures.
- **Verwaltungs-GUI — ✅ UMGESETZT:** `portfolio/gui.py` — Fenster „Solutions & Portfolios":
  Name/Framework/Zeitraum, ARTs zuordnen (Template `.json` oder direkt `IssueTimes.xlsx`,
  Datei-Browser), Modus pooled/comparison, Konfig speichern/laden, Report erzeugen → HTML im
  Browser. 5-Sprachen-`_T`, display-unabhängige Logik (`build_config_from_fields`, `_T`)
  unit-getestet. Start: `python -m portfolio` (ohne Argumente).
- **Launcher-Integration — ✅ UMGESETZT:** neue Karte „Solutions & Portfolios" (alpha) in der
  Modul-Registry, in allen 5 Sprachen.
- **Geteiltes Einstiegs-Layout — ✅ UMGESETZT:** Launcher zeigt jetzt die Split-View gemäß
  Idee-Skizze — **links** „Large Solutions & Portfolien" (die `portfolio`-Karte), **rechts**
  „ARTs & Team-Verbünde" (die bestehenden Modul-Karten), getrennt durch einen vertikalen
  Trenner. Section-Header in allen 5 Sprachen; `_ModuleEntry.section` steuert die Seite.
  Real verifiziert (App-Aufbau + Sprachwechsel).

Damit ist **Phase 2 vollständig abgeschlossen.**

**Phase 3 — Portfolio-Schachtelung & stage-abhängige Metriken:** Portfolio ▸ Solutions ▸ ARTs,
gemeinsames Stage-Mapping für CFD/Distribution, Management-Summary, PDF-Export.

- **Portfolio-Schachtelung — ✅ UMGESETZT:** `kind="portfolio"`; `members[].template` referenziert
  Solution-Templates. `_iter_art_members()` flacht rekursiv (mit Zyklusschutz) auf ARTs ab.
  - *Pooled:* alle ARTs aller Solutions in einem Datensatz (Label = Portfolio-Name).
  - *Comparison:* eine Einheit **pro Solution** (deren ARTs gepoolt, Label = Solution-Name) —
    Vergleich auf Solution-Ebene, nicht zu ART flachgemacht. Default-Metriken hier ohne Flow Load
    (jede Einheit ist selbst ein Pool über ggf. verschiedene Workflows).
  - CLI: `python -m portfolio <portfolio.json> --mode {pooled,comparison}`.
    Beispiel: `docs/design/portfolio_config.example.json`. Verifiziert (echte Daten: Portfolio aus
    2 Solutions / 4 ARTs → 1854 Issues pooled; Comparison gruppiert Alpha 861 / Beta 913).
- **Portfolio-Bearbeitung in der GUI — ✅ UMGESETZT:** Kind-Selektor (Solution/Portfolio) im
  Manager-Fenster; bei „portfolio" referenzieren die Mitglieder Solution-Templates (Spaltenkopf
  und Datei-Browser passen sich an, `.json`-Filter). Save/Load/Generate funktionieren für beide
  Kinds. `SolutionManagerApp` ist jetzt auf Modulebene (wie Launcher/build_reports). Verifiziert
  (App-Aufbau + Kind-Umschaltung + Sprachwechsel).
- Offen in Phase 3: stage-abhängige Metriken (CFD) mit gemeinsamem Stage-Mapping, Management-Summary,
  PDF-Export.

---

## 9. Offene Entscheidungen (für Robert)

1. **Aggregations-Modell zuerst:** mit *Pooled* starten (Empfehlung), oder gleich *Pooled +
   Comparison* parallel?
2. **Phase-1-Metrik(en):** Flow Velocity (klar additiv, einfachster Durchstich) — nur die,
   oder direkt Flow Velocity **und** Flow Time?

(Architektur, UI-Split und Template-basierte Gruppierung sind durch die Idee bereits gesetzt
und stehen nicht zur Debatte.)

---

## 10. Überlegungs-Log

- Aggregation per Record-Konkatenation in ein `ReportData` statt neuer Aggregationsmathematik —
  am Code verifiziert (`flow_velocity` zählt record-/datumsbasiert; `IssueRecord` trägt
  `project`+`Group`; `source_prefix` ist mehr-projekt-fähig).
- Stage-Inkompatibilität verschiedener Workflows als Hauptrisiko für stage-abhängige Metriken
  identifiziert → datums-getriebene Metriken zuerst.
- Neues Modul `portfolio` statt build_reports-Erweiterung, um Verantwortlichkeiten zu trennen.
- Solution-Konfig referenziert ART-Templates (Single Source of Truth), keine Duplikation.
