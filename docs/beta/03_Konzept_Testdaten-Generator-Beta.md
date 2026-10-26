# Beta-Vorbereitung · Konzept Testdaten-Generator 3 (entschieden am 26.10.2026)

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
  structure.json · story.json         ← Struktur (E2a) und Geschichte (E2) als Daten
  portfolio.json · solution_<name>.json ×m · pi_config.json
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
  ai_drafts/ briefing_<stand>.md · ask_*.md   ← nur mit Schalter (F3, standardmäßig aus): Mock-Entwürfe mit Marker, nicht freigegeben
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

### 3.6 Struktur als Daten (Ergänzung Robert, 26.10.2026)
Der Generator darf nicht auf „1 Portfolio · 2 Solutions · je 3 ARTs" festgelegt sein. Die Struktur ist
eine eigene Datei `structure.json` (Baum: Portfolios → Solutions → ARTs) und wird in Schritt 1 bearbeitet:

```json
{"schema": 1, "portfolios": [
  {"id": "P1", "name": "Demo Portfolio", "solutions": [
    {"id": "S1", "name": "Alpha", "workflow": "classic", "arts": ["Alpha-1", "Alpha-2", "Alpha-3"]},
    {"id": "S2", "name": "Beta",  "workflow": "stage_map", "arts": ["Beta-1", "Beta-2", "Beta-3"]}]},
  {"id": "P2", "name": "Portfolio Nord", "solutions": [
    {"id": "S3", "name": "Gamma", "workflow": "classic", "arts": ["Gamma-1"]},
    {"id": "S4", "name": "Delta", "workflow": "classic", "arts": ["Delta-1", "Delta-2", "Delta-3", "Delta-4"]}]}
]}
```

- **Beliebige Kardinalität:** n Portfolios, je Portfolio m Solutions, je Solution k ≥ 1 ARTs
  (eine Solution mit einem ART ist zulässig — ihr Report ist dann ART-Tiefe ohne Vergleich).
  Strukturvorlagen: *Klein* (1·1·2), *Standard* (1·2·3), *Groß* (5 Portfolios, 3–4 Solutions, 1–6
  ARTs), *Eigene*. Namen werden vorgeschlagen (griechische Buchstaben, dann Nummern) und sind änderbar;
  eine Struktur lässt sich als Datei laden und speichern.
- **Vorlagen binden an Rollen, nicht an Namen:** Jedes Ereignis der Geschichte adressiert eine Rolle
  (`outlier_art`, `weak_source_art`, `blocked_dependency: {from, to}`, `slo_breach_service`,
  `alarm_art`, `recurring_seam`), und `story.json` ordnet Rollen auf die vorhandene Struktur zu —
  Standard: Ausreißer = letzter ART der ersten Solution, Datenlücke = letzter ART der zweiten Solution,
  Cross-Solution-Abhängigkeit zwischen Solution 1 und 2. Bei nur einer Solution entfallen
  Cross-Solution-Ereignisse mit Hinweis statt Fehler.
- **Mehrere Portfolios:** je Portfolio ein eigener Datenraum-Unterordner mit eigener `portfolio.json`
  und eigenen Ständen; Solutions bleiben Templates je Portfolio. Ein Portfolio-übergreifendes Lagebild
  (Enterprise-Ebene) ist heute kein Feature — der Datenraum legt die Daten dafür aber schon ab.
- **Umfang folgt der Struktur:** die Schätzung („Was entsteht") rechnet aus der Struktur: Jira-Exporte
  = Zahl der ARTs, Arbeitsmappen = 3 × ARTs, Register = 12 × Solutions, Stände × Portfolios.
- **Grenzen, die das Werkzeug nennt:** ab etwa 30 ARTs oder 5 Portfolios bei Umfang L warnt der
  Generator vor Dauer und Größe (Schätzung in Schritt 2), verweigert aber nichts.

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
| 1 Szenario | Vorlage wählen (Ruhig · **Standard-Lage** empfohlen · Eskalation · Erholung · Eigene), darunter die Ereignisse der Vorlage als Liste mit Zeitpunkt und Schalter; rechts der **Struktur-Editor** (Strukturvorlage, Portfolios mit Solutions, ART-Zähler je Solution, Workflow je Solution, Namen änderbar, + Solution / + Portfolio, Struktur laden/speichern, Summe) | `Main.dc.html` |
| 2 Umfang & Quellen | Stände (Schieber 2–12, Standard 6, Rhythmus 14 Tage; Schalter „Delta-Briefings für alle Folgepaare erzeugen"), Umfang s/m/l, Realismus 0–100, Seed, Sprache; Provider-Checkliste (Prometheus, GitHub, GitLab, SonarQube, CSV, Datei; Harmonisierung; Betreiber-Ebene) — alles an, Details einklappbar | `Umfang.dc.html` |
| 3 Erzeugen | Zielordner, Knopf „Datenraum erzeugen"; Fortschritt als Artefakt-Liste mit Häkchen und Zeit; Ergebniskarte: Zahlen (Vorgänge, Register, Stände, Provider), Geschichte in drei Sätzen, Aktionen „Report öffnen · Konferenzmappe · Delta 5→6 · Einseiter · Lagebild befragen · im Portfolio-Manager öffnen"; Vergleichswähler Stand a → b für jedes Paar | `Ergebnis.dc.html` |
| ART-Werkzeug | Eigener Reiter „Ein ART" mit dem heutigen Generator (Muster, Lernen, Fortschreiben) — für RTE und Analysten, nicht im Hauptweg | später |

## 4a. Framework-Frage (Nachtrag zu E6)

Das Windows-Release ist heute ein tragbares Bündel (eingebettetes Python 3.11 mit tkinter, openpyxl,
plotly, kaleido, pypdf, tkcalendar, vorgeladener Chrome für PDF); Linux/macOS installieren dieselben
Pakete in eine venv. „Ohne große Pakete" begrenzt also, was ins Bündel kommt, nicht, was der Nutzer tut.

| Option | Zusatzpaket | Läuft wo | Einschätzung |
|---|---|---|---|
| tkinter wie heute | keins | überall mit dem Bündel | grobe Gestaltung; jede Oberfläche doppelt (Prototyp + Nachbau) |
| **Lokaler Server (Standardbibliothek) + Browser des Nutzers** | keins | überall, wo ein Browser ist | Prototyp wird die Oberfläche; Reports und Bedienung in einem Medium |
| Eingebetteter Webview (pywebview) | ein kleines Paket, System-Webview | Windows sicher, Linux je Distribution | natives Fenster um HTML, weitere Abhängigkeit mit Plattformrisiko |
| Qt o. ä. | > 100 MB | überall | zu schwer |

Festlegungen für den Kandidaten, falls er gewählt wird: Server nur an die lokale Adresse, zufälliger
Port, Zufallsschlüssel in der Adresse; Ordnerwahl über Pfadfeld mit Verlauf, „Durchsuchen" über den
tkinter-Dialog, wo vorhanden (tkinter als Helfer, nicht als Oberfläche); Generator als Pilot, Launcher
und Portfolio-GUI folgen beim Suite-Umbau. **Risiko (Einschätzung, nicht gemessen):** Firmenrechner
können lokale Server über Proxy-Regeln oder Richtlinien blocken — früh mit einem Testnutzer auf einem
Firmenrechner prüfen.

## 5. Entscheidungen (Robert, 26.10.2026, einzeln durchgegangen)

| Nr. | Entscheidung | Festlegungen |
|---|---|---|
| E1 | **Datenraum als fester Baum** mit `README.md`-Geschichte (3.1). | Flacher Ordner verworfen. |
| E2 | **Geschichte als Datei `story.json`,** vier Vorlagen (Ruhig, Standard-Lage, Eskalation, Erholung), Ereignisse einzeln schaltbar, **an Rollen gebunden**. | Schnitt 1 trägt nur die heutige Geschichte als erste Vorlage; die drei weiteren in Schnitt 2. Unplausible Schalterkombinationen werden mit Hinweis durchgelassen. |
| E2a | **Struktur als Datei `structure.json`:** beliebig viele Portfolios, Solutions, ARTs (k ≥ 1); Vorlagen Klein 1·1·2, Standard 1·2·3, Groß (5 Portfolios), Eigene. | **Workflow je Solution,** nicht je ART. Namen vorgeschlagen und änderbar, Rollen hängen an Positionen. Je Portfolio ein Unterordner mit eigenen Ständen. Ab etwa 30 ARTs oder 5 Portfolios bei Umfang L Warnung, keine Verweigerung. |
| E3 | **Reihe von Ständen, Standard sechs × 14 Tage,** einstellbar 2–12; Delta-Briefings aller Folgepaare. | Beantwortet zugleich Frage 2. Vorlage Ruhig gibt drei Stände vor. |
| E4 | **Provider-Rohdaten in Systemformaten + `sources.json`.** | Prüfung eingebaut: Writer schreibt, echter Provider liest, Test vergleicht mit dem direkt erzeugten Register. |
| E5 | **Drei Schritte, ein Hauptknopf.** ART-Generator als eigener Reiter. | **Zweiter Reiter schrumpft** auf die Funktionen ohne Datenraum-Abdeckung (einzelner Export, Fortschreiben, Lernen) — nach eigenem Audit mit Belegen. |
| E6 | **Prototyp zuerst im Browser.** | **Framework für die Umsetzung offen:** tkinter ist nicht gesetzt, Robert: „nehmen, was uns am besten dient, losgelöst von Frameworks", Bedingung: lauffähig auf möglichst vielen Rechnern ohne große Pakete. Kandidat laut Abschnitt 4a: lokaler Server aus der Standardbibliothek + Browser des Nutzers. Entscheidung fällt mit Schnitt 3, im Blick auf den anschließenden Umbau der gesamten Suite. Regel für den Prototyp bis dahin: nichts zeigen, was ein Browser ohne Zusatzpaket nicht kann. |
| E7 | **Reihenfolge:** (1a) Struktur + Datenraum-Baum + Geschichte-Datei, (1b) Stände-Reihe + Deltas, (1c) Provider-Writer mit Prüfung — alle drei über die Kommandozeile, getestet; (2) drei weitere Geschichten; (3) Oberfläche nach freigegebenem Prototyp inkl. Framework-Entscheidung und Reiter-Audit; (4) Tutorial „Demo-Datenraum in einer Minute" mit PDF. | Jeder Schnitt ein PR auf den Beta-Branch, Texte vor Merge zur Freigabe. |
| F1 | **Name: „Datenraum"** bleibt der Begriff für den Ordner (Portfolio-Modul seit 0.25.0); der Generator erzeugt einen **Demo-Datenraum**. | Ein Satz in der Oberfläche erklärt: vollständiger Datenraum mit erfundenen Teams und einer Geschichte, der sich wie ein echter öffnen lässt. Kein Umbenennen im Portfolio-Modul. |
| F2 | Sechs Stände als Standard. | Siehe E3. |
| F3 | **KI-Entwürfe (Mock) als Schalter in Schritt 2, standardmäßig aus.** | Ablage in eigenem Unterordner `ai_drafts/` des Datenraums, damit Eingabe und Ergebnis getrennt bleiben; Entwürfe tragen den Marker und sind nicht freigegeben; darunter absichtlich falsche Zitate zum Üben von `llm check`. |

**Bewusst nicht:** keine Personen, keine Live-Systeme (Prometheus & Co. nur als Dateien), kein Generator
für die Denkschriften-Beispiele, keine Zufalls-„Realität" ohne Seed (alles reproduzierbar).

## 6. Umsetzungsstand

| Schnitt | Stand | Inhalt |
|---|---|---|
| 1a | **gebaut 26.10.2026** (PR auf `beta/ux-redesign`) | `structure.json` + `story.json` (`testdata_generator/structure.py`, `story.py`), `scenario.py` baut aus der Struktur mit rollengebundenen Ankern, mehrere Portfolios als Unterordner, CLI `--structure`/`--arts` mit Schätzung und Warnung, 67 Tests, Doku (CHANGELOG, mkdocs DE/EN, Handbuch 5 Sprachen). GUI noch unverändert. Archiv: `Ideen/Archiv/Datenraum-Struktur_1a_2026-10-26/`. |
| 1b | offen | Stände-Reihe (6 × 14 Tage), Delta-Briefings aller Folgepaare, `deltas/`. |
| 1c | offen | Provider-Rohdaten in Systemformaten, `sources.json`, Prüfung Writer gegen Reader. |
| 2 | offen | Vorlagen Ruhig/Eskalation/Erholung, Ereignis-Schalter. |
| 3 | offen | Oberfläche nach Prototyp (Stand 7), Framework-Entscheidung, Reiter-Audit. |
| 4 | offen | Tutorial „Demo-Datenraum in einer Minute". |

Onepager DE/EN: Vorschlag, einmal für den ganzen Generator nach Schnitt 1c statt je Schnitt
(Robert entscheidet).
