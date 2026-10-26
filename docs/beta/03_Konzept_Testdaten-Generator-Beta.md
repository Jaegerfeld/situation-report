# Beta-Vorbereitung · Konzept Testdaten-Generator 3 (Entwurf zur Entscheidung, 26.10.2026)

**Auftrag (Robert, 26.10.2026):** Ziel des Reworks ist eine ansprechende Lösung für Solution- und
Portfolio-Management, zugleich eine Toolsuite für RTE, Flow-Manager und Analysten. Zum Schulen,
Präsentieren und Testen braucht es umfängliche, realitätsnahe Testdaten auf Knopfdruck. Schwerpunkt:
ein Portfolio mit zwei Solutions und je drei ARTs, **mit den Daten aller Provider**, nicht nur Jira.
UI-Konzept zuerst, Prototyp im Browser: https://claude.ai/artifact/WECbEUw6Z91mLkYGy6jxfJ

## 1. Befund — was der Generator heute kann

| Baustein | Stand (v0.54.0) |
|---|---|
| ART-Generator | Jira-JSON je ART mit Workflow, Zykluszeit-Verteilung, vier Anti-Pattern-Formen, Realismus 0–100 (echte Statuswege), Fortschreibung (`--continue`), Lernen aus echten Transitionen |
| Portfolio-Szenario (`--scenario portfolio`) | **2 Solutions × 3 ARTs** (Alpha-1..3, Beta-1..3), alle Jira-Rohdaten, XLSX, Configs, **zwölf Register** je Solution (Risiken, NFR/Runway, Capabilities, Abhängigkeiten, Decision-Log, Flussprobleme, Themes/Epics, SLO, DORA, Solution Areas, Wecker), Snapshot-Paar prev/now, PI-Config, README mit den eingebauten Geschichten (Alpha-3 Ausreißer, Beta-3 schwache Daten, Alpha-1→Alpha-3 blockiert, SLO-Bruch Order Sync API …); Umfang s/m/l; Szenario-Fortschreibung mit Snapshot-Rotation |
| Oberfläche | Ein Fenster, 15 Knöpfe, zwei Welten gemischt: oben der ART-Generator mit ~15 Parametern, unten „Demo-Portfolio" mit Erzeugen/Fortschreiben und vier Öffnen-Knöpfen |

**Was fehlt für „alle Provider":**
- Die SLO-/DORA-Register werden **direkt als Register-JSON** geschrieben. Die Provider des Moduls
  `sources` (Prometheus, GitHub DORA, GitLab DORA, SonarQube, CSV-SLO, Datei) bekommen **keine
  Eingaben** — der Weg „Quelle → `sources fetch` → Register" lässt sich mit Demo-Daten nicht zeigen.
- Kein Harmonisierungs-Arbeitsbereich (P3 hat `--example`, aber nicht im Datenraum), kein
  KI-Kompetenz-Log (R4), kein Betreiber-Nachweis, keine Prompt-Bündel.
- Nur **zwei Stände** (prev/now). Die Auffälligkeits-Hinweise (D4) brauchen ≥ 4, ein Schulungs-
  Durchlauf „sechs Konferenzen" braucht sechs — heute nur über wiederholtes Fortschreiben per Hand.
- Die Geschichte ist fest verdrahtet (eine Story, ein Seed-Verhalten). Für Schulung und Präsentation
  braucht es **wählbare Ereignisse** („im PI 2 bricht die SLO", „Scope wächst ab Woche 8") und ein
  ruhiges Gegenstück ohne Ereignisse.

## 2. Zielbild in einem Satz

Ein Knopf erzeugt einen **vollständigen Datenraum** — Portfolio mit zwei Solutions und je drei ARTs,
alle Jira-Rohdaten, alle Register, **Rohdaten jedes Providers**, eine **Reihe von Ständen** über
mehrere Konferenzen und eine wählbare **Geschichte** mit Ereignissen —, den Report, Mappe, Delta,
Einseiter, Befragung, Wecker und Harmonisierung sofort lesen; der ART-Generator für RTE und
Analysten bleibt als eigener Weg erhalten.

## 3. Datenmodell des Datenraums

### 3.1 Struktur (fest, benannt, sprechend)
```
<Datenraum>/
  portfolio.json · solution_alpha.json · solution_beta.json · pi_config.json
  README.md                         ← die Geschichte dieses Datenraums, Ereignisse, Seed, Zahlen
  raw/   <ART>_jira.json ×6         ← Jira-Export (Allowlist, Personen anonymisiert wie R1)
  xlsx/  <ART>_IssueTimes/CFD/Transitions ×6
  registers/ <register>_<solution>.json ×12 je Solution
  sources/                          ← NEU: Rohdaten je Provider, so wie das System sie liefert
    prometheus/<service>_slo.json   (Query-Antwort-Format)
    github/<art>_deployments.json   (Deployments/Workflow-Runs)
    gitlab/<art>_pipelines.json
    sonarqube/<art>_measures.json
    csv/<service>_slo.csv
    file/<art>_records.json         (normiertes Record-Schema, der „Weg 1")
    sources.json                    ← Config, die `python -m sources fetch` auf diese Dateien zeigt
  harmonisation/                    ← NEU: Katalog, 2–3 Bewertungen je E2E-Prozess, Board-Entscheidungen, Vorstand
  snapshots/ snapshot_<datum>.json ×N  ← NEU: Reihe (Standard 6 Stände = 6 Konferenzen), prev/now als Aliasse
  deltas/    delta_<n>-<n+1>.html/.md ×(N−1)  ← NEU: Delta-Briefings aller Folgepaare, fertig gerendert
  operator/ ai_literacy.json · llm_audit.jsonl · prompt_<zweck>_*.md   ← NEU: Betreiber-Ebene (R3/R4, Export-Weg)
```

### 3.2 Die Geschichte als Daten (`story.json`, wählbar in der Oberfläche)
Ereignisse mit Zeitpunkt (PI/Woche), Ziel (ART, Register, Service) und Wirkung; der Generator
übersetzt sie in Jira-Transitionen, Registereinträge und Stände. Vorlagen:

| Vorlage | Ereignisse | Für |
|---|---|---|
| **Ruhig** | keine; alle Teams im Rahmen | erste Schulung, Baseline, Noise-Audit |
| **Standard-Lage** (heutige Story) | Alpha-3 Ausreißer, Beta-3 Datenlücke, Alpha-1→Alpha-3 blockiert, SLO-Bruch Order Sync, Wecker DP-A1 ausgelöst, Naht Alpha-1×Alpha-3 wiederkehrend | Präsentation, Tutorials |
| **Eskalation** | Standard + Scope-Wachstum ab PI 2, zweite Abhängigkeit blockiert, Runway-Lücke überfällig, Konferenz ohne Beschluss (Flussproblem überlebt 4×) | Übung Value-Stream-Konferenz, Red Team |
| **Erholung** | Standard bis Stand 3, danach Maßnahmen greifen (Zykluszeit sinkt, SLO zurück, Wecker unterschwellig) | Delta-Briefing, „was hat sich geändert" |
| **Eigene** | Ereignisse an/aus, Zeitpunkt verschiebbar | Trainer |

Jedes Ereignis ist auch in `README.md` als Satz erzählt — die Lösung zur Übungsaufgabe.

### 3.3 Reihe der Stände
Stand 1 … N im Konferenzrhythmus (Standard 14 Tage, 6 Stände). Jeder Stand = eingefrorener
Snapshot + Fortschreibung der Rohdaten (heutige `scenario_continue`-Mechanik, N-fach). Damit laufen
D2 (Delta zwischen beliebigen Ständen), D4 Schritt 2 (Hinweise ab 4 Ständen), die Wecker-Historie
und der Lernpfad „sechs Konferenzen" ohne Handarbeit.

**Delta-Stände (Ergänzung Robert, 26.10.2026):** Der Datenraum bringt die Delta-Briefings **aller
Folgepaare** (1 → 2 … N−1 → N) fertig gerendert mit (`deltas/`, HTML + Markdown), und die Ergebniskarte
hat einen Vergleichswähler für **beliebige** Stände (z. B. 1 → 6 über das ganze Quartal). Die Ereignisse
der Geschichte sind so gelegt, dass jedes Folgepaar etwas zeigt — Verschlechterung, Verbesserung,
Neuzugang, Überfälliges —, in der README je Paar ein Satz, was zu sehen ist. Wecker-Historie und
Auffälligkeits-Hinweise lesen dieselbe Reihe.

### 3.4 Provider-Rohdaten (die Lücke)
Je Provider ein Writer, der **das Format des Systems** erzeugt (nicht unser Register), so dass die
vorhandenen Reader `sources/providers/*.py` sie unverändert lesen: Prometheus (`result[].values`),
GitHub (Deployments + Workflow-Runs → DORA), GitLab (Pipelines/Deployments), SonarQube
(`component.measures[]`), CSV-SLO, Datei (normiertes Record-Schema). `sources.json` verdrahtet sie.
Die Zahlen sind dieselben wie in den Registern — **eine Wahrheit, zwei Wege** (Register direkt oder
über `sources fetch`), und die Schulung kann beide zeigen.

### 3.5 Personen
Keine. Teams/ARTs als Owner, anonymisierte Autoren im Changelog (wie R1), Teilnehmerzahlen im
Kompetenz-Log. Der Datenraum ist damit ohne Datenschutz-Frage weitergebbar.

## 4. Oberfläche — drei Schritte, ein Knopf

**Nutzer und Ziel (UX read):** Trainer, Vorführender oder Testnutzer will in unter einer Minute einen
Datenraum haben, der eine erzählbare Lage zeigt — und wissen, was er dann öffnen kann. **Primäre
Aktion:** „Datenraum erzeugen". **Gesetze:** Goal-Gradient (drei benannte Schritte, Stand sichtbar),
Hick's/Pareto (vier Vorlagen, eine empfohlen, Details zugeklappt), Tesler (Komplexität in Vorlagen und
Standardwerten, nicht in Feldern), Feedback/Doherty (Fortschritt je Artefakt, Abbruch), Peak-End
(Ergebnis mit den nächsten Aktionen), Jakob (gleiche Fenster-Konventionen wie die übrigen Module).
**Nicht ausgeliefert:** Wand aus 15 Feldern, gleichgewichtige Knöpfe, Erfolg ohne nächsten Schritt.
**Zustände:** leer (kein Zielordner), erzeugt (Fortschritt je Artefakt), fertig (Ergebniskarte), Fehler
(neben dem Artefakt, Rest bleibt), Ordner nicht leer (Rückfrage).

| Schritt | Inhalt | Prototyp |
|---|---|---|
| 1 Szenario | Vorlage wählen (Ruhig · **Standard-Lage** empfohlen · Eskalation · Erholung · Eigene), darunter die Ereignisse der Vorlage als Liste mit Zeitpunkt und Schalter; rechts die Struktur (Portfolio → 2 Solutions → 6 ARTs) mit Namen, änderbar | `Main.dc.html` |
| 2 Umfang & Quellen | Stände (Schieber 2–12, Standard 6, Rhythmus 14 Tage; Schalter „Delta-Briefings für alle Folgepaare erzeugen"), Umfang s/m/l, Realismus 0–100, Seed, Sprache; Provider-Checkliste (Prometheus, GitHub, GitLab, SonarQube, CSV, Datei; Harmonisierung; Betreiber-Ebene) — alles an, Details einklappbar | `Umfang.dc.html` |
| 3 Erzeugen | Zielordner, Knopf „Datenraum erzeugen"; Fortschritt als Artefakt-Liste mit Häkchen und Zeit; Ergebniskarte: Zahlen (Vorgänge, Register, Stände, Provider), Geschichte in drei Sätzen, Aktionen „Report öffnen · Konferenzmappe · Delta 5→6 · Einseiter · Lagebild befragen · im Portfolio-Manager öffnen"; Vergleichswähler Stand a → b für jedes Paar | `Ergebnis.dc.html` |
| ART-Werkzeug | Eigener Reiter „Ein ART" mit dem heutigen Generator (Muster, Lernen, Fortschreiben) — für RTE und Analysten, nicht im Hauptweg | später |

## 5. Entscheidungen (meine Empfehlung jeweils zuerst)

- **E1 Datenraum als feste Struktur mit `README.md`-Geschichte** (3.1). *Alternative:* flacher Ordner wie heute.
- **E2 Geschichte als Daten (`story.json`) mit vier Vorlagen und Ereignis-Schaltern.** *Alternative:* nur die heutige feste Story.
- **E3 Reihe von Ständen, Standard 6 × 14 Tage.** *Alternative:* prev/now bleiben, Reihe nur per Fortschreiben.
- **E4 Provider-Rohdaten in Systemformaten + `sources.json`,** damit `sources fetch` im Demo-Datenraum läuft. *Alternative:* Register direkt wie heute (die Provider bleiben ohne Demo).
- **E5 Drei-Schritte-Oberfläche mit einem Hauptknopf; ART-Generator als eigener Reiter.** *Alternative:* heutiges Fenster erweitern.
- **E6 Prototyp zuerst im Browser** (Design-Artifact, gemeinsam iterieren), dann tkinter. *Alternative:* direkt bauen.
- **E7 Reihenfolge der Umsetzung:** (1) Datenmodell + Provider-Writer + Stände-Reihe (CLI, Tests), (2) Story-Vorlagen, (3) Oberfläche nach freigegebenem Prototyp, (4) Tutorial „Datenraum in einer Minute". Jeder Schnitt ein PR auf den Beta-Branch.
- **Bewusst nicht:** keine Personen, keine Live-Systeme (Prometheus & Co. nur als Dateien), kein Generator für die Denkschriften-Beispiele, keine Zufalls-„Realität" ohne Seed (alles reproduzierbar).

## 6. Offene Fragen an Robert
1. Namen: „Datenraum" (Portfolio-Begriff seit 0.25.0) als Produktwort für das Ergebnis — oder „Demo-Welt"/„Übungslage"?
2. Sechs Stände als Standard — oder drei (ein PI)?
3. Soll der Datenraum auch die KI-Entwürfe (Markdown-Dateien mit Marker) enthalten, erzeugt mit dem Mock-Provider, damit Freigabe (`llm approve`) und `llm check` geübt werden können?
