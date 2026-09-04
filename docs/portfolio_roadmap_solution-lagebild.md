# Roadmap: `portfolio`-Modul → EA-informiertes Solution-Lagebild

*Technisches, lebendes Dokument. Verortet im getrackten `docs/` (versioniert mit dem Code). Fachlicher Rahmen: die [Denkschriften-Reihe](https://jaegerfeld.github.io/situation-report/de/denkschriften/) — EA-Denkschrift (EA-Dimensionen, Phasen A–C) und KI-Denkschrift (Phase D; ab v2.0 mit Zuordnung der D-Funktionen zu Entscheidungsbestandteilen). Stand 2026-09-02 — Phase A vollständig umgesetzt (A1–A4, v0.17.2 + Unreleased).*

## Wie diese Roadmap gegliedert ist

Nicht nach „Feature-Wunschliste", sondern nach **Datenherkunft** (das BGS-Prinzip aus der Agile-Metriken-Arbeit) — denn *woher die Daten kommen*, entscheidet über Aufwand und Machbarkeit:

- **Phase A — aus bereits vorhandenen Daten berechenbar (S).** Erweitert nur bestehenden Code; keine neue Eingabe.
- **Phase B — braucht einen neuen lokalen Eingabe-Contract (G/B).** Neues JSON-Artefakt, analog zu `solution_config.py`, in den Report gerendert.
- **Phase C — braucht eine externe Integration (S aus Fremdsystemen).** Monitoring/CI/CD/Git/SonarQube; größter Aufwand, externe Abhängigkeiten.
- **Phase D — KI-Assistenz hinter dem deterministischen Kern.** Veredelt Ausgaben der Phasen A–C (Formulierung, Lesarten, Q&A, Alarm-Kontext); optional und austauschbar, nie Voraussetzung einer Kernfunktion.

> **Wichtige Unterscheidung:** Die EA-Dimensionen (Capability, NFR, ROAM, Dependencies) haben **heute keine Quelle im Datenstrom**. Sie sind *keine* Flow-Metrik-Erweiterungen, sondern brauchen eigene Eingaben (Phase B). Genau das zu benennen macht aus der Liste einen Plan.

---

## Ausgangslage (Ist-Stand, code-verankert)

| Vorhanden | Wo |
|---|---|
| Solution-/Portfolio-Config, Members referenzieren ARTs via Templates (Schema v1) | `portfolio/solution_config.py` |
| **Pooled**- und **Comparison**-Modus, beide end-to-end verdrahtet (CLI + GUI) | `aggregator.py`, `cli.py`, `gui.py` |
| **Kanonische STAGE-Map** (To Do / In Progress / Done) für ART-übergreifendes CFD-Pooling trotz unterschiedlicher Workflows | `aggregator.py` → `build_reports.stage_groups` |
| Flow-Metriken (Velocity, Time, Load, Distribution) + Management-Summary (Items, Completed, WIP, Median/P85/P95 CT, ≤Ziel-%) | `aggregator.py`, `summary.py` |
| **A1 · Konfidenz-Flag je Quelle** (Ampel high/medium/low, Qualitätstabelle in HTML + PDF) | `summary.py` (SourceQuality/assess_quality), `aggregator.py` (quality_sink) |
| **A2 · Summary-Erweiterung** (E2E-Lead-Time Median/P85, Member-Share, Abdeckungsgrad) | `summary.py` |
| **A3 · Ausreißer-Hervorhebung** im Comparison (Median/P95 > 1,5 × Spalten-Median, ab 3 Zeilen) | `summary.py` (_outlier_cells) |
| **A4 · Kanonische Stage-Map konfigurierbar** (optionaler `stage_map`-Block, Schema v2) | `solution_config.py` (StageMap), `aggregator.py` (_pool_cfd) |

> Und: Die vorhandene kanonische **Stage**-Map (Workflow-Status) ist **nicht** die EA-**Capability**-Map (Geschäftsfähigkeiten). Letztere kommt in Phase B — andere Dimension, andere Quelle.

---

## Phase A — aus vorhandenen Daten (S) · erweitert bestehenden Code · ✅ **komplett umgesetzt (02.09.2026, PRs #150–#160)**

*Geringer Aufwand, sofort wertstiftend, keine neuen Eingaben. Berührt nur `aggregator.py` / `summary.py` / `gui.py`.*

### A1 · Datenqualitäts-/Konfidenz-Flag je Quelle · ✅ umgesetzt (PR #154)
- **Was:** Beim Poolen je Member erfassen: Datenstand/Alter, Record-Zahl, Anteil Issues ohne `first_date`/`closed_date`, fehlende CFD-Daten. Als **Ampel/Confidence je Quelle** in die Summary und (Comparison) je ART.
- **Warum (EA-Bezug):** Solution-Entscheidungen auf gepoolten Zahlen ohne Herkunfts-Vertrauen sind blind. Systemdenken verlangt: „wie belastbar ist diese Zahl?" (Kernpunkt der Denkschrift & Abschnitt 5 des Solution-Ebene-Papiers).
- **Wo:** `_load_member`/`build_pooled_report_data` liefern die Rohzahlen bereits; neue Felder in `Summary`, Spalte in `_summary_headers`/`_summary_cells`, farbige Zelle in `render_summary_html`.
- **Aufwand:** S–M.

### A2 · Management-Summary erweitern · ✅ umgesetzt (PR #156)
- **Was:** End-to-End **Solution-Lead-Time** über alle ARTs (aus gepoolten Daten), **Member-Beitrag** (Anteil Items je ART), **Abdeckungsgrad** (wie viele geplante ARTs haben Daten geliefert).
- **Warum:** „Ein konsistenter Beitrag je ART, sauber zu einem Gesamtbild gepoolt" (Ebene 3 – A der Lagebild-Liste).
- **Wo:** `compute_summary`, `Summary`-Felder, Tabelle in `summary.py`.
- **Aufwand:** S.

### A3 · Comparison-Modus abrunden · ✅ umgesetzt (PR #158)
- **Was:** Ausreißer-Hervorhebung (welcher ART reißt Median/P95?), Datenqualitäts-Flag je ART auch im Comparison-Report; veralteten `summary.py`-Kommentar entfernen.
- **Warum:** „Comparison-Modus: ARTs nebeneinander statt nur gepoolt" (Ebene 3 – D) ist da — hier nur schärfen.
- **Wo:** `render_comparison_html`, `load_comparison_units`.
- **Aufwand:** S.

### A4 · Kanonische Stage-Map konfigurierbar · ✅ umgesetzt (PR #160)
- **Was:** Die feste 3-Gruppen-Map (To Do/In Progress/Done) optional feiner konfigurierbar machen (z. B. gemeinsame kanonische Stages je Solution), damit heterogene ART-Workflows differenzierter, aber konsistent poolen.
- **Warum:** „Stage-abhängige Metriken über eine gemeinsame, kanonische Stage-Map" (Ebene 3 – D).
- **Wo:** `build_reports.stage_groups` + Verweis in `solution_config` (neuer optionaler Block); Schema-Bump beachten.
- **Aufwand:** M.

### A5 · ART-Tiefe: Auswertung optional bis auf ART-Ebene · ✅ umgesetzt (04.09.2026)
- **Was:** Ein Schalter (GUI-Haken *Bis auf ART-Ebene auswerten*, CLI `--art-depth`, Konfigurationsfeld `report.art_depth`), der die Report-Einheiten bis zum einzelnen ART auflöst — im Vergleichsmodus als Figuren *und* Tabellen je ART, im Pooled-Modus als zusätzliche Tabelle *ART Detail*, und in der Konferenzmappe als Teil von Input 1. Erst damit sind die beiden workflow-gebundenen Analysen aus *ART & Teams* (`process_flow`, `process_flow_time`) auf Portfolio-Ebene überhaupt verfügbar.
- **Warum:** A3 hat den Comparison-Modus geschärft, aber die Vergleichstiefe blieb an die Ebene gebunden: ein Portfolio verglich Solutions, deren gepoolte Daten die ART-Übergänge nicht mehr enthalten. Wer wissen will, *welcher ART* der Ausreißer ist — und wer die Prozessfluss-Analysen für die Value-Stream-Conference braucht —, musste bisher jede Solution einzeln öffnen.
- **Wo:** `load_art_units`/`_iter_labelled_arts`/`_art_detail_units` in `aggregator.py`, durchgereicht bis `render_html`/`render_pdf`/`render_conference_html`; `DEFAULT_ART_METRICS`; GUI-Haken in fünf Sprachen.
- **Bewusst nicht:** Snapshots und Delta-Briefing (D2) bleiben flach — ein Snapshot hält den Report-Stand fest, und ein Vergleich über wechselnde Beschriftungen hinweg erzeugte genau das Driftrauschen, das Phase 3 beseitigt hat. Ebenso bleiben die Pooled-Figuren gepoolt; ART-Figuren gibt es im Vergleichsmodus.
- **Aufwand:** M.

---

## Phase B — neuer lokaler Input-Contract (G/B) · analog `solution_config`

*Jede Dimension = ein neues, versioniertes JSON-Artefakt (geschätzt/beobachtet im PI-Planning/Review erhoben), geladen & validiert wie die Solution-Config, in den Report gerendert. Mittlerer Aufwand. **Hier entsteht der eigentliche EA-Mehrwert.***

**Gemeinsames Muster je Item:** `portfolio/<name>_config.py` (Dataclass + `parse_*`/`load_*`, `SCHEMA_VERSION`) → Render-Funktion in `summary.py`/`aggregator.py` → GUI-Feld zum Verweisen auf die Datei.

**Definition of Done (Testdaten, seit dem Portfolio-Szenario):** Jedes B-Feature liefert im selben Branch seine Testdaten-Erzeugung mit — Schema + Renderer + Tests + Erweiterung des Portfolio-Szenarios (`testdata_generator --scenario portfolio`) inkl. Roundtrip-Test (erzeugte Datei lädt fehlerfrei durch den eigenen Parser) + Manual-Abschnitt. Ein B-Feature ohne erzeugbare Testdaten gilt als unfertig; so bleibt das Demo-Portfolio automatisch vollständig.

### B1 · Capability-Map & -Health ✅ (umgesetzt 02.09.2026)
- **Was:** JSON, das Solution-**Capabilities** (Geschäftsfähigkeiten) definiert und ARTs/Members auf Capabilities mappt; Report zeigt **Capability-Status/-Health** statt nur Ticket-Zahlen.
- **Warum:** Capabilities sind die *Sprache* der EA (alle vier EA-Bücher). Bindet Solution-Fortschritt an Strategie/Wert (Abschnitt 5 „Capability-Denken → Capability-Health").
- **Aufwand:** M.
- **Ist-Stand:** `portfolio/capability_config.py` (Schema v1: id/title/health healthy|at_risk|critical, arts, owner, assessed_on), Tabelle unter der Qualitätstabelle (PDF: eigene Seite), kritisch zuerst, **Uncovered-Markierung** für Capabilities ohne beitragenden ART, **Drift-Warnung** bei ART-Namen außerhalb der Member-Liste, Health von Menschen bewertet, Portfolio aggregiert Member-Maps mit Solution-Spalte; Capability-Map ≠ stage_map (bewusst getrennte Dimensionen); Szenario liefert je Solution eine Map mit (DoD erfüllt). **Damit sind B1/B2/B3 komplett — der lokale Input-Contract der Phase B steht.**

### B2 · NFR-/Architecture-Runway-Register ✅ (umgesetzt 02.09.2026)
- **Was:** JSON mit NFRs (Ziel/Ist/Status) und Runway-Elementen je Solution; Report als **NFR-/Compliance-Dashboard + Runway-Ampel**.
- **Warum:** Architektonische Schuld sichtbar & steuerbar machen (sonst „detoniert ungeplant"). Direkt aus dem A-ESA-/SAFe-NFR-Denken.
- **Aufwand:** M.
- **Ist-Stand:** `portfolio/nfr_config.py` (Schema v1: nfrs mit target/actual/status met|at_risk|violated, runway mit status in_place|building|gap + needed_by), Dashboard unter dem ROAM-Board (PDF: eigene Seite, beide Tabellen gestapelt), Verletzt/Lücken zuerst, Overdue-Hervorhebung (needed_by verstrichen ∧ nicht in place), Status von Menschen gepflegt (Werkzeug rechnet Ziel/Ist nicht), Portfolio aggregiert Member-Register mit Solution-Spalte; Szenario liefert je Solution ein Register mit (DoD erfüllt).

### B3 · ROAM-Risk-Board ✅ (umgesetzt 02.09.2026)
- **Was:** JSON mit Risiken (Resolved/Owned/Accepted/Mitigated + Owner/Impact); Report als **ROAM-Board**.
- **Warum:** Macht das Lagebild zur Governance-Basis statt bloßer Beobachtung (Ebene 3 – D „ROAM-Risk-Board").
- **Aufwand:** S–M.
- **Ist-Stand:** `portfolio/risks_config.py` (Schema v1: id/title/roam/owner/impact/status_since/notes), Board unter der Qualitätstabelle (PDF: eigene Seite), R-O-A-M-Gruppierung mit Farb-Zellen, Aging-Hervorhebung für Owned > 30 Tage, Portfolio aggregiert Member-Register mit Solution-Spalte; Owner = Teams; Szenario liefert je Solution ein Register mit (DoD erfüllt).

### B4 · Decision-/Assumption-Log ✅ (umgesetzt 02.09.2026)
- **Was:** JSON mit Architektur-/Solution-Entscheidungen + Annahmen (ADR-artig, leichtgewichtig); im Report verlinkt.
- **Warum:** Trade-off-Disziplin sichtbar; Annahmen prüfbar (Red-Team/Premortem-Anschluss).
- **Aufwand:** S.
- **Ist-Stand:** `portfolio/decision_config.py` (Schema v1: kind decision|assumption mit kind-abhängigem Status-Set proposed|accepted|superseded bzw. open|confirmed|invalidated; supersedes referenzvalidiert), Log-Tabelle unter der Dependency-Heatmap (PDF: eigene Seite), **offene Annahme mit überschrittenem review_by sortiert nach oben + rote „review due"-Zelle** (Red-Team-/Premortem-Anschluss), Portfolio aggregiert Member-Logs mit Solution-Spalte; Szenario liefert je Solution ein Log mit (DoD erfüllt). **Damit ist Phase B komplett umgesetzt (B1–B5); es folgen B6/B7 hinter D2.**

### B5 · Dependency-/Integration-Register ✅ (umgesetzt 02.09.2026)
- **Was:** JSON mit Abhängigkeiten/Integrationspunkten zwischen ARTs (Status, Fälligkeit); Report als **Dependency-/Integrations-Heatmap**.
- **Warum:** Cross-ART-Abhängigkeiten als Systemverhalten (Schutz vor lokaler Optimierung); Ebene 3 – D „Dependency-/Integrations-Heatmap".
- **Aufwand:** M.
- **Ist-Stand:** `portfolio/dependency_config.py` (Schema v1: from/to/status blocked|at_risk|on_track|done + due), Heatmap (offene Abhängigkeiten je from/to-Paar, Zellfarbe = dringlichster Status) + Detail-Tabelle unter dem NFR-Dashboard (PDF: eigene Seite), blocked zuerst, Overdue-Hervorhebung (due verstrichen ∧ nicht done); `to` bewusst nicht gegen Member validiert — Cross-Solution-/Extern-Ziele erlaubt und im Portfolio-Report sichtbar; Szenario liefert je Solution ein Register mit (DoD erfüllt).

### B6 · Flussproblem-Backlog & Konferenzmappe *(VSC-1; Workshop Wolfsburg 08/2026)* ✅ (umgesetzt 03.09.2026)
- **Was:** `flow_problems` als eigenes Input-Artefakt mit eigener `SCHEMA_VERSION` (Quelle, betroffene Value Streams/ARTs, Cross-VS-Flag, Alter, Status, Resolution-Commitment, Wiedervorlage-PI). Report-Profil **„Konferenzmappe"** bündelt die Inputs der Value-Stream-Konferenz zu einem Pre-Read. **Resolution-Tracking mit Aging** über PI-Grenzen: Impediments, die n Konferenzen überleben, eskalieren sichtbar (baut auf B3 und B5 auf).
- **Warum:** Die VSC ist das im Workshop definierte Ritual der Solution-Ebene; der Impediment-Backlog ist laut Workshop ihr wichtigster Input. Das dort benannte Muster „Risiken werden geloggt, nie mitigiert, tauchen nächstes PI wieder auf" wird damit messbar statt anekdotisch. Herleitung: `Quellen/bilder workshop/Analyse_Workshop-Notizen_Denkschriften+Software.md` (dort P1).
- **Aufwand:** M. **Voraussetzung:** B3/B5 (gemeinsame Datenobjekte).
- **Ist-Stand:** `portfolio/flow_problems_config.py` (Schema v1; Status open|committed|resolved|dropped; **Cross-VS abgeleitet**, nicht behauptet: > 1 value_stream; `conferences`-Zähler von Menschen gepflegt), **Survivor-Regel** ungelöst ∧ ≥ 3 Konferenzen → sortiert zuerst, roter Zähler; Report-Sektion (HTML+PDF, Portfolio-aggregiert) + **Konferenzmappe** via `--conference FILE [--conference-date]` (leichte druckbare Seite: Input 1 Daten/Qualität · Input 2 Impediments/ROAM/Dependencies · Input 3 Capabilities/SLOs; Roadmap-Input folgt mit B7); Szenario liefert flow_problems_alpha/beta.json mit (FP-A1/FP-B1 als Survivors, DoD erfüllt).

### B7 · Integrierte Roadmap-Sicht & Strategic Themes *(VSC-2; Workshop Wolfsburg 08/2026)* ✅ (umgesetzt 03.09.2026)
- **Was:** Roadmap-Aggregation über Trains mit Initiative-Swimlanes (Zeithorizont nah granular, fern grob: P1 · P2 · Y1 · Y2 · Y3). `strategic_themes` als Entität mit Epic-Verknüpfung und **Orphan-Detection in beide Richtungen** (Theme ohne Epics = deklariert und vergessen; Epic ohne Theme = Zombie-Initiative). Der Report-Diff (D2) auf die integrierte Sicht dokumentiert die „updated roadmaps" je Konferenz automatisch.
- **Warum:** Schließt die im Workshop konsolidierten SAFe-Lücken „no large-solution roadmap with initiative-level swim lanes" und „strategic themes haben kein strukturiertes Zuhause". Herleitung: Workshop-Analyse (dort P2).
- **Aufwand:** M–L. **Voraussetzung:** B6; profitiert von D2, braucht es aber nicht.
- **Ist-Stand:** `portfolio/themes_config.py` (Schema v1; Zombie = bewusst LEERES theme-Feld, Tippfehler-Referenz = Validierungsfehler), Orphanschaft portfolioweit beurteilt; Report mit Theme-Tabelle („declared & forgotten" rot), Roadmap-Matrix Trains × Horizonte (Zombies rot) und Zombie-Liste (HTML+PDF); Konferenzmappe um **Input 4** ergänzt; **D2-Anschluss umgesetzt**: Epics in Snapshots, Delta-Sektion „Roadmap epics (updated roadmaps)" mit Mehrfeld-Änderungen (Horizont/Status/Theme; Theme-Verlust → „zombie", worsened). Szenario liefert themes_alpha/beta.json mit (Orphan T-A2, Zombie EP-A9; Delta-Story EP-A9-Theme-Verlust + EP-B2 P2→P1 — DoD erfüllt). **Damit sind Phase B (B1–B7) und die VSC-Erweiterungen komplett.**

> *Einordnung B6/B7:* Am 31.08.2026 zunächst hinter Phase D gelegt, am 01.09.2026 in Phase B eingegliedert — wohin sie typologisch immer gehörten (lokale Input-Contracts im deterministischen Kern, keine KI-Abhängigkeit); Priorisierung nach dem D2-Piloten. Umsetzung beauftragt am 03.09.2026 (ursprünglich als PR #149 vorgeschlagen; dort wegen Roadmap-Konflikten geschlossen und hier aktuell eingepflegt).

---

## Phase C — externe Integration (S aus Fremdsystemen)

*Größter Aufwand, externe Abhängigkeiten; liefert das technische Gesundheitsbild neben dem Fluss.*

### C1 · SLO/SLI & Error-Budget ✅ (umgesetzt 03.09.2026)
- **Quelle:** Monitoring (Azure Monitor / Prometheus / Grafana). **Warum:** Zuverlässigkeit gemessen & budgetiert (*SRE with Azure*), technische Ergänzung zur ökonomischen Flow-Sicht. **Aufwand:** L.
- **Ist-Stand:** Über das neue steckbare `sources`-Framework (Vorgabe Robert: austauschbar, kombinierbar, neue Quelle = eine Datei): Referenz-Provider **prometheus** (De-facto-OSS-Standard, ~77 % Produktionsnutzung; Marktrecherche 03.09.) + universeller **file**-Provider (jedes System per JSON-Export, ohne API-Freigabe — Datadog/Dynatrace/Azure docken so an). Report-Sektion „Service Levels & Error Budgets" mit ZENTRALER Budget-/Status-Regel (verbraucht = (100−SLI)/(100−Ziel); at_risk < 25 % Rest) — jede Quelle wird gleich beurteilt. Config-Feld `slo`; Szenario liefert slo_alpha/beta.json mit.

### C2 · DORA + Qualitäts-/Fehlermetriken ✅ (umgesetzt 03.09.2026)
- **Quelle:** CI/CD + Git + SonarQube. **Was:** Deployment Frequency, Lead Time for Changes, Change Failure Rate, Time to Restore; Coupling/Cohesion → Fehlerneigung (*Fault Detection*). **Aufwand:** L.
- **Ist-Stand:** Referenz-Provider **github** (Wunsch Robert; keine native DORA-API — die vier Kennzahlen werden aus Deployments/PRs/Incident-Issues ABGELEITET, Näherungen dokumentiert und konfigurierbar), **gitlab** als zweite Referenz (einzige native DORA-API am Markt — Austauschbarkeits-Beweis) und **sonarqube** (Qualität: Coverage/Rating/kritische Verstöße). Report-Sektion „Delivery Performance (DORA) & Code Quality" mit Tier je Kennzahl an den veröffentlichten DORA-Schwellen (Unit-Tier = schwächste Kennzahl). Config-Feld `dora`; Szenario liefert dora_alpha/beta.json mit. **Offen:** Praxistest gegen echte Instanzen; Coupling/Cohesion-Fehlerneigung (Fault-Detection-Teil) später.

### C3 · `get_data`-Modul (Jira REST) fertigstellen ✅ (umgesetzt 03.09.2026)
- **Was:** direkter Jira-Abruf statt manuellem Export (bereits als Modul geplant). **Warum:** senkt Erhebungsaufwand → METRIKS-MINDSET „Metriken als automatisiertes Nebenprodukt". **Aufwand:** M–L.
- **Ist-Stand:** Umgesetzt mit **zwei gleichwertigen Erhebungswegen** (Vorgabe Robert 03.09.: API-Freigaben dauern in großen Organisationen lange — der manuelle Export bleibt vollwertig): CLI `fetch` (REST v3 Cursor-/v2 Offset-Paginierung, expand=changelog, Auth Cloud-Basic/Bearer-PAT, Token nur per ENV, nie geloggt) und `check` (Export-Prüfung: Pflichtfelder, Changelog, Duplikate, vergessene Folgeseiten); GUI mit Modus-Umschalter beider Wege; Launcher-Karte startet jetzt (Info-Knopf mit Export-Anleitung bleibt). Beide Wege münden im selben JSON-Envelope — Contract-Test gegen transform_data; Manual-Kapitel 2 in fünf Sprachen; Onepager.

---

## Phase D — KI-Assistenz (optional, hinter dem deterministischen Kern)

*Fachlicher Rahmen: `Quellen/KI-und-Lagebild_v1.0.md` (sieben Lagedienst-Muster M1–M7, sechs KI-Prinzipien). Architektur-Grundsatz: **Das LLM textet, es rechnet nicht** — Zahlen entstehen ausschließlich in Pipeline/Simulate; die KI-Schicht formuliert, übersetzt, erklärt. Jedes D-Feature ist optional (eigenes Modell/eigener Schlüssel, lokal oder API) und degradiert sauber: Ohne KI bleibt der Report vollständig nutzbar. Aggregat-Regel als harte Vorgabe: Teams/ARTs, keine Personen (KI-Prinzip 6).*

### D1 · LLM-Executive-Summary — **✅ (04.09.2026, Phase 4 auf dem llm-Framework)**
- **Was:** Kennzahlen aus `summary.py` als Eingabe, LLM erzeugt die Management-Formulierung (Zwei-Lesarten-tauglich); Zahlen werden aus dem Datenpfad übernommen, nie generiert.
- **Warum:** Rosetta-Stone-Arbeit (EA-Prinzip 3) wird bezahlbar; Muster M1/M6. **Aufwand:** S–M.
- **Ist-Stand:** `portfolio/exec_summary.py` — deterministischer **Summary-Contract** `summary_to_markdown(build_snapshot(config))` (Kennzahlen gepoolt + je Einheit, Quell-Konfidenz, Governance-Kopfzahlen als Statuszählungen; strukturell OHNE Owner/Personen — Aggregat-Grenze per Test erzwungen, Contract-Gleichheit per Spy-Test). Versionierter Prompt `exec_summary_system_prompt` (de/en) in llm/prompts; `llm.narrate` mit `system_prompt`-Weiche — Zahlen-Wächter, Art.-50-Banner und Audit (purpose `d1_exec_summary`) gelten unverändert. CLI: `--narrate` wirkt auf Report-Läufe mit HTML-`--output` — Abschnitt „Executive Summary (Entwurf)" DIREKT unter der Management-Summary-Tabelle (Fallback Seitenende) + separates `<output>.exec_summary.md`; GUI: dieselbe Checkbox gilt für „Report erzeugen …", KI-Fehler degradieren sauber (Report ohne Entwurf + Statusmeldung). PDF-Läufe: Hinweis statt Entwurf.

### D2 · Delta-Briefing  ⟵ *Phase-D-Pilot (Beschluss 13.08.2026)* — **Teil 1 ✅ (deterministischer Kern) · Teil 2 ✅ (KI-Narration, beide 03.09.2026)**
- **Was:** Deterministischer Diff zweier Report-Stände (neue/geschlossene Items, Kennzahl-Deltas, Ampelwechsel, Konfidenz-Änderungen) + LLM-Narration „Was hat sich geändert, was beschleunigt sich?".
- **Warum:** Hohpes „first derivative" als Produkt (Muster M2); geringstes Risiko, sofort spürbar, sauberer Beleg für den Architektur-Grundsatz. **Voraussetzung:** zwei Report-Stände. **Aufwand:** M.
- **Ist-Stand Teil 1:** `portfolio/snapshot.py` (Schema v1: Kennzahlen je Einheit + gepoolt, Quell-Konfidenz as-of-verankert, alle fünf Governance-Register; CLI `--snapshot`/`--as-of`) + `portfolio/delta.py` (CLI `--delta PREV NOW` ohne Config): Kennzahl-Deltas auf Anzeigegenauigkeit, Durchsatz im Zeitraum, Konfidenz-Übergänge, je Register added/removed/Statuswechsel (Verschlechterungen zuerst) + **frisch Überfälliges** (nur echte Kipp-Punkte gegen beide as-of-Daten); Ausgabe HTML/Markdown/stdout, „keine Änderungen" wird explizit gesagt. Szenario liefert snapshot_prev/now mit erzählter Zwei-Wochen-Story (DoD).
- **Ist-Stand Teil 2 (Entscheidungen Robert 03.09.2026: lokal mistral-nemo, extern claude-sonnet-5, Default Deutsch, Audit nur Hashes):** Steckbare KI-Schicht `llm/` nach dem sources-Muster (Provider = EINE Datei mit PROVIDER-Objekt, Auto-Discovery; `python -m llm providers|test`): **ollama** (lokal, Daten verlassen den Rechner nie), **claude** (Anthropic-API, Schlüssel NUR aus ANTHROPIC_API_KEY) und **mock** (zahlenfreie Attrappe — Demo/Tests ohne Modell). CLI `--narrate [PROVIDER] --llm-model --llm-lang`; ohne Flag exakt heutiges Verhalten, mit Flag Abschnitt „Narration (Entwurf)" + separates `<output>.narration.md` (Freigabe-Mechanik: Mensch redigiert den Entwurf). GUI-Checkbox + Provider-Auswahl; Testdaten-Generator-Demo mit wählbarem Provider (Default mock, umschaltbar auf ollama/claude). Drei Wächter unumgehbar in `llm/narrate.py` verdrahtet (Leitplanken a–c): **Zahlen-Wächter** (jede Zahl wörtlich im Briefing, sonst verworfen), **Art.-50-Kennzeichnung** (Banner mit Modell/Deployment-Klasse/Prompt-Version v1, behauptet nie Freigabe), **Betreiber-Nachweis** llm_audit.jsonl (nur SHA-256-Hashes). Eingabe-Contract = Delta-Markdown (per Pipeline-Test erzwungen — Teams, nie Personen, Leitplanke b). Ollama-Installationsanleitung Win11 als separate PDF (DE/EN) + Tutorial-Seite. **Offen: Leitplanke d** — Freigabe-Kalibrierung im Pilot-Betrieb (mitzählen, wie oft Entwürfe unverändert übernommen werden), sobald Ollama auf Roberts Rechner steht (Phase 0).

### D3 · Befragbares Lagebild
- **Was:** Q&A über Report-Daten (JSON/CSV) mit **Zitierpflicht**: jede Antwort referenziert den Datenpfad; „weiß ich nicht" ist zulässige Antwort. *Hygiene-Vorgabe (KI-Denkschrift v2.0, Prinzip 7):* konfigurierbar die **eigene Einschätzung des Fragenden vor der Antwort abfragen** und beide nebeneinanderstellen — Entscheidungshygiene nach Kahneman/Sibony/Sunstein („erst unabhängig urteilen, dann die KI fragen").
- **Warum:** Muster M3 — Shared Consciousness verbreitern, ohne das Urteil zu ersetzen. **Voraussetzung:** Provenienz-Modell über Report-Artefakte. **Aufwand:** M–L.

### D4 · Anomalie-Hinweise
- **Was:** Statistische Auffälligkeits-Erkennung im deterministischen Kern (stdlib), KI liefert nur den Erklärtext mit Kontext.
- **Warum:** Muster M4 (Entscheidungspunkt-Wecker), gegen Alarm-Müdigkeit: nur entscheidungsrelevante Schwellen (EVI). **Aufwand:** M.

### D5 · Red-Team-Assistent — **✅ (04.09.2026, Phase 4 — damit ist Phase 4 komplett: D1, D6, D5 auf dem llm-Framework)**
- **Was:** Premortem-/Annahmen-Angriffs-Fragen aus Decision-/Assumption-Log generieren (Rohmaterial für menschlich moderierte Sessions).
- **Warum:** Red-Team-Kapazität für jeden Stab (Rolle 3 der KI-Denkschrift). **Voraussetzung:** B4. **Aufwand:** S–M.
- **Ist-Stand:** `portfolio/red_team.py` — deterministischer Log-Contract (`decision_log_to_markdown` über `_collect_decisions`: IDs, Art, Status, Owner-Teams, Daten, supersedes), versionierter Prompt (`red_team_system_prompt` de/en: Premortem-Rahmung für Entscheidungen, direkter Annahmen-Angriff, 1–3 Fragen je Eintrag, gruppiert je ID). Die Denkschrift-Zuordnung „D5 → Urteil: NUR Rohmaterial, kein Empfehlungs-Button" ist MASCHINELL erzwungen: der **Fragen-Wächter** (`enforce_questions`) verwirft jede Ausgabe, deren „- "-Zeilen nicht als Frage enden — zusätzlich zu Zahlen-Wächter, Art.-50-Banner und Audit (purpose `d5_red_team`). CLI `--red-team FILE` an der Config (Provider via --narrate-Wert oder ollama); ohne referenziertes B4-Log klare Fehlermeldung. Mock liefert frage-förmige Attrappe (Demo/Tests ohne Modell).

### D6 · Mehrsprachige Report-Ausleitung — **✅ (04.09.2026, Phase 4)**
- **Was:** Report-Texte in weitere Sprachen ausleiten (Muster M5; gelebte Praxis der Manuals).
- **Warum:** adressatengerechte Zustellung in internationalen Solutions. **Aufwand:** S–M.
- **Ist-Stand:** `llm/translate.py` über den Wächter-Pfad (`llm.narrate`) — die Zahlen-Invariante ist für Übersetzungen die perfekte Wache (jede Zahl der Übersetzung muss wörtlich in der Vorlage stehen); versionierter Übersetzungs-Prompt je Haussprache (`translation_system_prompt`, Regeln: vollständig, Zahlen/IDs wörtlich, Eigennamen unübersetzt, Entwurf), **Art.-50-Banner jetzt in allen fünf Haussprachen** (`ai_banner_text` de/en/ro/pt/fr), Audit-Zweck `d6_translation`. Zwei Wege: `python -m llm translate DATEI --to LANG …` (der Redaktions-Workflow: der Mensch gibt den redigierten Text frei und leitet DANN aus — je Zielsprache `<datei>.<lang>.md`) und `--translate LANG …` an der portfolio-CLI (Delta: Entwurf → `.narration.<lang>.md`, ohne Narration das deterministische Briefing → `.<lang>.md`; Report: `.exec_summary.<lang>.md`). Provider wie überall (ollama lokal Default, claude, mock).

### D7 · Noise-Audit-Unterstützung *(neu, KI-Denkschrift v2.0)*
- **Was:** Dieselbe Frage n-fach in variierter Formulierung an die KI-Schicht stellen, Antworten protokollieren und die **Streuung ausweisen** (Konsistenz-Score, abweichende Aussagen markiert) — die KI misst ihre eigene Lautstärke. Optional Gegenüberstellung mit den unabhängigen Einschätzungen mehrerer Nutzer (Noise-Audit des Stabs, KI-Denkschrift D.3).
- **Warum:** Nicht-deterministische Modelle streuen selbst; blindes Vertrauen importiert diese Streuung als Scheinobjektivität (Risiko „Noise-Verstärkung"). Prinzip 7. **Voraussetzung:** D3. **Aufwand:** M.

**Zuordnung der D-Funktionen zu Entscheidungsbestandteilen** (Zerlegung nach Agrawal/Gans/Goldfarb, KI-Denkschrift C.6): D1/D2/D6 → *Aktion* (formulieren) · D3/D7 → *Vorhersage/Feedback* (erklären, konsistent halten) · D4 → *Ergebnis* · D5 → *Urteil* (nur Rohmaterial — **kein Empfehlungs-Button, der das Urteil automatisiert**).

**Rechtliche Leitplanken für Phase D** *(neu, KI-Denkschrift v2.1, Rechts-Prüfbox D.2 — KI-Verordnung (EU) 2024/1689, Stand 18.08.2026; bei Einführung juristisch prüfen)*:

- **(a) KI-Hinweise sind Teil des Produkts (Art. 50 KI-VO, gilt seit 02.08.2026).** D3 zeigt an, dass eine KI antwortet (Art. 50 Abs. 1). KI-formulierte Report-Texte (D1/D2/D6) tragen einen sichtbaren KI-Hinweis, bis ein Mensch sie geprüft und freigegeben hat — die Freigabe ist zugleich die Ausnahme von der Kennzeichnungspflicht (Art. 50 Abs. 4). Die Open-Source-Lizenz befreit nicht davon (Art. 2 Abs. 12 nimmt Art. 50 ausdrücklich aus).
- **(b) Aggregat-Grenze im deterministischen Kern (Anhang III Nr. 4).** Kein D-Feature erhält Personendaten; Prinzip 6 („Teams, keine Personen") wird im Kern erzwungen, nicht in der KI-Schicht — so bleibt das Lagebild außerhalb des Hochrisiko-Bereichs (Leistung/Verhalten von Beschäftigten). Das gehört als Test in die Pipeline, nicht als Hinweis in die Doku.
- **(c) Betreiber-Nachweis.** Modell, Version, Systemvorgaben und Datenklassifizierung je Deployment werden protokolliert (Grundlage für Kompetenz- und Transparenzpflicht, Art. 4/Art. 50); die Deployment-Entscheidung (on-prem / EU-Cloud / Zero-Retention) ist Teil der Konfiguration, nicht der Nutzerwahl.
- **(d) Erst der Pilot D2** liefert die Erfahrung, wie viel Freigabe-Aufwand die Hinweise erzeugen — die Freigabe-Schwelle (Stichprobe vs. volle Prüfung) wird dort kalibriert (KI-Denkschrift C.5 „Verifizieren können").

---

## Querschnitt (über alle Phasen)

- **Zwei-Lesarten-Layout:** Exec-Summary (Ampeln/Trends) ↔ technische Detailsicht — die „Rosetta-Stone"-Anforderung (Carducci): Report muss für Business *und* Engineering lesbar sein. Render-seitig in `export`/`summary`.
- **Konfidenz-Flag konsequent** auf allen gepoolten/aggregierten Kennzahlen (beginnt in A1, gilt für B/C mit).
- **Schema-Disziplin:** jedes neue Config-Artefakt mit eigener `SCHEMA_VERSION`; `solution_config` bleibt Single Source of Truth für die ART-/Solution-Referenzen.

---

## Priorisierung (Aufwand × Wert)

| Prio | Item | Phase | Aufwand | Wert |
|---|---|---|---|---|
| 1 | ✅ A1 Datenqualitäts-/Konfidenz-Flag | A | S–M | hoch (Vertrauen ins ganze Lagebild) |
| 2 | ✅ A2 Summary erweitern (E2E-Lead-Time, Abdeckung) | A | S | hoch |
| 3 | B3 ROAM-Board | B | S–M | hoch (Governance) |
| 4 | B2 NFR-/Runway-Register | B | M | hoch (Schuld sichtbar) |
| 5 | B1 Capability-Map | B | M | hoch (Strategie-Anbindung) |
| 6 | B5 Dependency-Heatmap | B | M | mittel–hoch |
| 7 | ✅ A3/A4 Comparison-Feinschliff / Stage-Map | A | S–M | mittel |
| 8 | B4 Decision-Log | B | S | mittel |
| 9 | C3 get_data (Jira REST) | C | M–L | hoch (Aufwand runter) |
| 10 | C1/C2 SLO + DORA/Qualität | C | L | hoch (technisches Gesundheitsbild) |
| 11 | **D2 Delta-Briefing (Phase-D-Pilot)** | D | M | hoch (sofort spürbar, geringstes KI-Risiko) |
| 12 | ✅ B6 Flussproblem-Backlog & Konferenzmappe (VSC-1) | B | M | hoch (füttert das VSC-Ritual; Aging macht Nicht-Mitigation messbar) |
| 13 | ✅ B7 Integrierte Roadmap & Strategic Themes (VSC-2) | B | M–L | hoch (SAFe-Lücken; Orphan-Detection; nutzt D2 für Konferenz-Nachberichte) |
| 14 | D1 Exec-Summary · D6 Sprachen | D | S–M | mittel–hoch |
| 15 | D4 Anomalie · D5 Red-Team · D3 Q&A (mit Hygiene-Vorgabe) | D | M–L | hoch (Lagedienst-Ausbau) |
| 16 | D7 Noise-Audit-Unterstützung | D | M | mittel–hoch (Vertrauen messbar machen) |

**Empfohlene Sequenz:** ✅ Phase A vollständig (umgesetzt 02.09.2026) → B3/B2/B1 (EA-Kern: Governance, Schuld, Strategie) → restliche B → C nach Bedarf/Reife. **Phase D** startet unabhängig davon mit dem Piloten D2, sobald zwei Report-Stände vorliegen (Beschluss vom 13.08.2026; fachliche Leitplanken in `Quellen/KI-und-Lagebild_v1.0.md`, Teil D).

---

## Platzierungs-Hinweis

Dieses Roadmap-Dokument liegt bewusst in **`docs/`** (getrackt, wandert mit dem Code). Die begleitende **Denkschrift** (fachlich-strategisch, kuratiert, versioniert nach `Quellen/Versionierung.md`) liegt in **`Quellen/`**. So bleibt Technik-Planung beim Code und die strategische Einordnung bei den kuratierten Quellen.
