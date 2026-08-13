# Roadmap: `portfolio`-Modul → EA-informiertes Solution-Lagebild

*Technisches, lebendes Dokument. Verortet im getrackten `docs/` (versioniert mit dem Code), nicht in `Quellen/`. Fachlicher Rahmen: die Denkschriften `Quellen/Enterprise-Architektur-und-Solution-Lagebild_v2.0.md` (EA-Dimensionen, Phasen A–C) und `Quellen/KI-und-Lagebild_v1.0.md` (Phase D) sowie `Quellen/Solution-Ebene_EA_Wissen-Skills-Lagebild.md`. Stand 2026-08-13.*

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

> Hinweis: Der Kommentar „Phase 1 supports only pooled" in `summary.py` ist **veraltet** — Comparison ist implementiert und in GUI/CLI wählbar. Beim nächsten Anfassen korrigieren.
>
> Und: Die vorhandene kanonische **Stage**-Map (Workflow-Status) ist **nicht** die EA-**Capability**-Map (Geschäftsfähigkeiten). Letztere kommt in Phase B — andere Dimension, andere Quelle.

---

## Phase A — aus vorhandenen Daten (S) · erweitert bestehenden Code

*Geringer Aufwand, sofort wertstiftend, keine neuen Eingaben. Berührt nur `aggregator.py` / `summary.py` / `gui.py`.*

### A1 · Datenqualitäts-/Konfidenz-Flag je Quelle  ⟵ *höchste Priorität*
- **Was:** Beim Poolen je Member erfassen: Datenstand/Alter, Record-Zahl, Anteil Issues ohne `first_date`/`closed_date`, fehlende CFD-Daten. Als **Ampel/Confidence je Quelle** in die Summary und (Comparison) je ART.
- **Warum (EA-Bezug):** Solution-Entscheidungen auf gepoolten Zahlen ohne Herkunfts-Vertrauen sind blind. Systemdenken verlangt: „wie belastbar ist diese Zahl?" (Kernpunkt der Denkschrift & Abschnitt 5 des Solution-Ebene-Papiers).
- **Wo:** `_load_member`/`build_pooled_report_data` liefern die Rohzahlen bereits; neue Felder in `Summary`, Spalte in `_summary_headers`/`_summary_cells`, farbige Zelle in `render_summary_html`.
- **Aufwand:** S–M.

### A2 · Management-Summary erweitern
- **Was:** End-to-End **Solution-Lead-Time** über alle ARTs (aus gepoolten Daten), **Member-Beitrag** (Anteil Items je ART), **Abdeckungsgrad** (wie viele geplante ARTs haben Daten geliefert).
- **Warum:** „Ein konsistenter Beitrag je ART, sauber zu einem Gesamtbild gepoolt" (Ebene 3 – A der Lagebild-Liste).
- **Wo:** `compute_summary`, `Summary`-Felder, Tabelle in `summary.py`.
- **Aufwand:** S.

### A3 · Comparison-Modus abrunden
- **Was:** Ausreißer-Hervorhebung (welcher ART reißt Median/P95?), Datenqualitäts-Flag je ART auch im Comparison-Report; veralteten `summary.py`-Kommentar entfernen.
- **Warum:** „Comparison-Modus: ARTs nebeneinander statt nur gepoolt" (Ebene 3 – D) ist da — hier nur schärfen.
- **Wo:** `render_comparison_html`, `load_comparison_units`.
- **Aufwand:** S.

### A4 · Kanonische Stage-Map konfigurierbar
- **Was:** Die feste 3-Gruppen-Map (To Do/In Progress/Done) optional feiner konfigurierbar machen (z. B. gemeinsame kanonische Stages je Solution), damit heterogene ART-Workflows differenzierter, aber konsistent poolen.
- **Warum:** „Stage-abhängige Metriken über eine gemeinsame, kanonische Stage-Map" (Ebene 3 – D).
- **Wo:** `build_reports.stage_groups` + Verweis in `solution_config` (neuer optionaler Block); Schema-Bump beachten.
- **Aufwand:** M.

---

## Phase B — neuer lokaler Input-Contract (G/B) · analog `solution_config`

*Jede Dimension = ein neues, versioniertes JSON-Artefakt (geschätzt/beobachtet im PI-Planning/Review erhoben), geladen & validiert wie die Solution-Config, in den Report gerendert. Mittlerer Aufwand. **Hier entsteht der eigentliche EA-Mehrwert.***

**Gemeinsames Muster je Item:** `portfolio/<name>_config.py` (Dataclass + `parse_*`/`load_*`, `SCHEMA_VERSION`) → Render-Funktion in `summary.py`/`aggregator.py` → GUI-Feld zum Verweisen auf die Datei.

### B1 · Capability-Map & -Health
- **Was:** JSON, das Solution-**Capabilities** (Geschäftsfähigkeiten) definiert und ARTs/Members auf Capabilities mappt; Report zeigt **Capability-Status/-Health** statt nur Ticket-Zahlen.
- **Warum:** Capabilities sind die *Sprache* der EA (alle vier EA-Bücher). Bindet Solution-Fortschritt an Strategie/Wert (Abschnitt 5 „Capability-Denken → Capability-Health").
- **Aufwand:** M.

### B2 · NFR-/Architecture-Runway-Register
- **Was:** JSON mit NFRs (Ziel/Ist/Status) und Runway-Elementen je Solution; Report als **NFR-/Compliance-Dashboard + Runway-Ampel**.
- **Warum:** Architektonische Schuld sichtbar & steuerbar machen (sonst „detoniert ungeplant"). Direkt aus dem A-ESA-/SAFe-NFR-Denken.
- **Aufwand:** M.

### B3 · ROAM-Risk-Board
- **Was:** JSON mit Risiken (Resolved/Owned/Accepted/Mitigated + Owner/Impact); Report als **ROAM-Board**.
- **Warum:** Macht das Lagebild zur Governance-Basis statt bloßer Beobachtung (Ebene 3 – D „ROAM-Risk-Board").
- **Aufwand:** S–M.

### B4 · Decision-/Assumption-Log
- **Was:** JSON mit Architektur-/Solution-Entscheidungen + Annahmen (ADR-artig, leichtgewichtig); im Report verlinkt.
- **Warum:** Trade-off-Disziplin sichtbar; Annahmen prüfbar (Red-Team/Premortem-Anschluss).
- **Aufwand:** S.

### B5 · Dependency-/Integration-Register
- **Was:** JSON mit Abhängigkeiten/Integrationspunkten zwischen ARTs (Status, Fälligkeit); Report als **Dependency-/Integrations-Heatmap**.
- **Warum:** Cross-ART-Abhängigkeiten als Systemverhalten (Schutz vor lokaler Optimierung); Ebene 3 – D „Dependency-/Integrations-Heatmap".
- **Aufwand:** M.

---

## Phase C — externe Integration (S aus Fremdsystemen)

*Größter Aufwand, externe Abhängigkeiten; liefert das technische Gesundheitsbild neben dem Fluss.*

### C1 · SLO/SLI & Error-Budget
- **Quelle:** Monitoring (Azure Monitor / Prometheus / Grafana). **Warum:** Zuverlässigkeit gemessen & budgetiert (*SRE with Azure*), technische Ergänzung zur ökonomischen Flow-Sicht. **Aufwand:** L.

### C2 · DORA + Qualitäts-/Fehlermetriken
- **Quelle:** CI/CD + Git + SonarQube. **Was:** Deployment Frequency, Lead Time for Changes, Change Failure Rate, Time to Restore; Coupling/Cohesion → Fehlerneigung (*Fault Detection*). **Aufwand:** L.

### C3 · `get_data`-Modul (Jira REST) fertigstellen
- **Was:** direkter Jira-Abruf statt manuellem Export (bereits als Modul geplant). **Warum:** senkt Erhebungsaufwand → METRIKS-MINDSET „Metriken als automatisiertes Nebenprodukt". **Aufwand:** M–L.

---

## Phase D — KI-Assistenz (optional, hinter dem deterministischen Kern)

*Fachlicher Rahmen: `Quellen/KI-und-Lagebild_v1.0.md` (sieben Lagedienst-Muster M1–M7, sechs KI-Prinzipien). Architektur-Grundsatz: **Das LLM textet, es rechnet nicht** — Zahlen entstehen ausschließlich in Pipeline/Simulate; die KI-Schicht formuliert, übersetzt, erklärt. Jedes D-Feature ist optional (eigenes Modell/eigener Schlüssel, lokal oder API) und degradiert sauber: Ohne KI bleibt der Report vollständig nutzbar. Aggregat-Regel als harte Vorgabe: Teams/ARTs, keine Personen (KI-Prinzip 6).*

### D1 · LLM-Executive-Summary
- **Was:** Kennzahlen aus `summary.py` als Eingabe, LLM erzeugt die Management-Formulierung (Zwei-Lesarten-tauglich); Zahlen werden aus dem Datenpfad übernommen, nie generiert.
- **Warum:** Rosetta-Stone-Arbeit (EA-Prinzip 3) wird bezahlbar; Muster M1/M6. **Aufwand:** S–M.

### D2 · Delta-Briefing  ⟵ *Phase-D-Pilot (Beschluss 13.08.2026)*
- **Was:** Deterministischer Diff zweier Report-Stände (neue/geschlossene Items, Kennzahl-Deltas, Ampelwechsel, Konfidenz-Änderungen) + LLM-Narration „Was hat sich geändert, was beschleunigt sich?".
- **Warum:** Hohpes „first derivative" als Produkt (Muster M2); geringstes Risiko, sofort spürbar, sauberer Beleg für den Architektur-Grundsatz. **Voraussetzung:** zwei Report-Stände. **Aufwand:** M.

### D3 · Befragbares Lagebild
- **Was:** Q&A über Report-Daten (JSON/CSV) mit **Zitierpflicht**: jede Antwort referenziert den Datenpfad; „weiß ich nicht" ist zulässige Antwort.
- **Warum:** Muster M3 — Shared Consciousness verbreitern. **Voraussetzung:** Provenienz-Modell über Report-Artefakte. **Aufwand:** M–L.

### D4 · Anomalie-Hinweise
- **Was:** Statistische Auffälligkeits-Erkennung im deterministischen Kern (stdlib), KI liefert nur den Erklärtext mit Kontext.
- **Warum:** Muster M4 (Entscheidungspunkt-Wecker), gegen Alarm-Müdigkeit: nur entscheidungsrelevante Schwellen (EVI). **Aufwand:** M.

### D5 · Red-Team-Assistent
- **Was:** Premortem-/Annahmen-Angriffs-Fragen aus Decision-/Assumption-Log generieren (Rohmaterial für menschlich moderierte Sessions).
- **Warum:** Red-Team-Kapazität für jeden Stab (Rolle 3 der KI-Denkschrift). **Voraussetzung:** B4. **Aufwand:** S–M.

### D6 · Mehrsprachige Report-Ausleitung
- **Was:** Report-Texte in weitere Sprachen ausleiten (Muster M5; gelebte Praxis der Manuals).
- **Warum:** adressatengerechte Zustellung in internationalen Solutions. **Aufwand:** S–M.

---

## Querschnitt (über alle Phasen)

- **Zwei-Lesarten-Layout:** Exec-Summary (Ampeln/Trends) ↔ technische Detailsicht — die „Rosetta-Stone"-Anforderung (Carducci): Report muss für Business *und* Engineering lesbar sein. Render-seitig in `export`/`summary`.
- **Konfidenz-Flag konsequent** auf allen gepoolten/aggregierten Kennzahlen (beginnt in A1, gilt für B/C mit).
- **Schema-Disziplin:** jedes neue Config-Artefakt mit eigener `SCHEMA_VERSION`; `solution_config` bleibt Single Source of Truth für die ART-/Solution-Referenzen.

---

## Priorisierung (Aufwand × Wert)

| Prio | Item | Phase | Aufwand | Wert |
|---|---|---|---|---|
| 1 | A1 Datenqualitäts-/Konfidenz-Flag | A | S–M | hoch (Vertrauen ins ganze Lagebild) |
| 2 | A2 Summary erweitern (E2E-Lead-Time, Abdeckung) | A | S | hoch |
| 3 | B3 ROAM-Board | B | S–M | hoch (Governance) |
| 4 | B2 NFR-/Runway-Register | B | M | hoch (Schuld sichtbar) |
| 5 | B1 Capability-Map | B | M | hoch (Strategie-Anbindung) |
| 6 | B5 Dependency-Heatmap | B | M | mittel–hoch |
| 7 | A3/A4 Comparison-Feinschliff / Stage-Map | A | S–M | mittel |
| 8 | B4 Decision-Log | B | S | mittel |
| 9 | C3 get_data (Jira REST) | C | M–L | hoch (Aufwand runter) |
| 10 | C1/C2 SLO + DORA/Qualität | C | L | hoch (technisches Gesundheitsbild) |
| 11 | **D2 Delta-Briefing (Phase-D-Pilot)** | D | M | hoch (sofort spürbar, geringstes KI-Risiko) |
| 12 | D1 Exec-Summary · D6 Sprachen | D | S–M | mittel–hoch |
| 13 | D4 Anomalie · D5 Red-Team · D3 Q&A | D | M–L | hoch (Lagedienst-Ausbau) |

**Empfohlene Sequenz:** Phase A vollständig (schnelles Vertrauen + Substanz) → B3/B2/B1 (EA-Kern: Governance, Schuld, Strategie) → restliche B → C nach Bedarf/Reife. **Phase D** startet unabhängig davon mit dem Piloten D2, sobald zwei Report-Stände vorliegen (Beschluss vom 13.08.2026; fachliche Leitplanken in `Quellen/KI-und-Lagebild_v1.0.md`, Teil D).

---

## Platzierungs-Hinweis

Dieses Roadmap-Dokument liegt bewusst in **`docs/`** (getrackt, wandert mit dem Code). Die begleitende **Denkschrift** (fachlich-strategisch, kuratiert, versioniert nach `Quellen/Versionierung.md`) liegt in **`Quellen/`**. So bleibt Technik-Planung beim Code und die strategische Einordnung bei den kuratierten Quellen.
