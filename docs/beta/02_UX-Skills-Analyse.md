# Beta-Vorbereitung · Analyse der „Laws of UX Agent Skills" und Vorschläge für SituationReport (23.10.2026)

Grundlage: der Ordner `C:\Users\rober\Downloads\laws-of-ux-agent-skills` (Pip Decks, Version 1.0.0,
Stand 07.10.2026; basiert auf *Laws of UX* von Jon Yablonski). Gelesen: README, AGENTS.md, die neun
`SKILL.md`, die Playbooks `dashboards-and-tables.md` und `states.md`, `RESULTS.md`, LICENSE.md.
Der Ordner wurde nur gelesen, nichts ausgeführt, nichts installiert.

## 1. Was das Paket ist

Neun Agent-Skills (reines Markdown, nichts zu bauen), die ein Coding-Agent lädt, wenn er eine
Oberfläche baut oder prüft. Kern ist die Karte: 54 „Gesetze" in vier Kategorien (29 UX-Theorie,
9 Psychologie, 7 Interaktionsprinzipien nach Norman, 9 Forschungsmethoden), je eine Datei mit
„Was es verlangt · Wann es gilt · Verstoß erkennen (Code / Screenshot) · Beispiel · Konflikte ·
Herkunft mit Quelle". Zahlen tragen ihre Quelle (WCAG, Apple HIG, Nielsen); unbelegte Zahlen sind als
Heuristik markiert — das passt zu unserer Wahrheitsregel.

| Skill | Was er tut | Nutzen für uns |
|---|---|---|
| `ux-preflight` | **Vor** jeder UI-Änderung ein „UX read": Nutzer und Ziel, primäre Aktion, drei bis sechs Gesetze als konkrete Vorgaben, Fehler, die nicht ausgeliefert werden, Zustände; danach „UX check" gegen den Code | **Hoch.** Genau die Disziplin, die wir für den Umbau brauchen: erst entscheiden, dann bauen, am Ende prüfen. Entspricht unserer Konzept-vor-Bau-Regel |
| `ux-audit` | Prüft Code, laufende Seite oder Screenshot in neun Linsen; Tabelle `# · Sev P0–P3 · Gesetz · Beleg · Schaden · Fix`, dazu „was funktioniert" und „nicht prüfbar". Ändert nichts | **Hoch.** Liefert den Beta-Backlog mit Belegen (`file:line`), statt Geschmacksurteilen |
| `ux-fix` | Setzt freigegebene Befunde um, kleinste Änderung zuerst, eine nach der anderen, prüft jede nach | **Hoch.** Passt zu „Freigabe zuletzt": Audit → Robert wählt → Fix |
| `ux-justify` | Begründung einer Entwurfsentscheidung (Decision · Why · Evidence · Trade-off · How we will know) mit Gesetz und Quelle | **Mittel.** Für CHANGELOG, PR-Texte, Testnutzer-Kommunikation und die Denkschriften |
| `ux-flows` | Sechs Playbooks: Formulare, Onboarding, Pricing/Checkout, Navigation, Dashboards/Tabellen, Zustände | **Hoch** für Dashboards/Tabellen, Navigation, Formulare, Zustände; Pricing/Checkout entfällt |
| `ux-methods` | Neun Forschungsmethoden als Plan → Vorlage → Auswertung (Usability-Test, Interview, Contextual Inquiry, Card Sorting, Survey, Affinity Map, Personas, Journey Map, Design Principles). Erfindet nie Ergebnisse | **Hoch.** Wir haben Testnutzer, die am Manual scheiterten — das Paket liefert Testplan und Leitfaden |
| `ux-figma-audit` | Audit eines Figma-Frames oder PNG | **Niedrig.** Kein Figma; die Screenshot-Route ist aber für tkinter-Fenster nützlich |
| `laws-of-ux` | Der Index der 54 Karten + „welches Gesetz gewinnt" | **Hoch** als Nachschlagewerk; wird von den anderen gelesen |
| `pip-library` | Pip-App-Anbindung | **Entfällt** (kein Pip-Konto nötig) |

Kosten laut README: etwa 1 400 Tokens für die neun Beschreibungen je Sitzung, 700–3 100 je geladenem
Skill, Kartendateien einzeln. Getestet vom Hersteller mit Claude Code, Sonnet 5.5 (`RESULTS.md`: Audits
fanden 17–19 von 19 gepflanzten Verstößen).

## 2. Lizenz — wichtig vor dem Einbau

`LICENSE.md` ist ein **proprietärer Einzelnutzer-Vertrag** (noch als „PLACEHOLDER, not yet legal
text" markiert): installieren auf eigenen Geräten und in eigenen Projekten ja, **in ein privates Repo
committen ja, in ein öffentliches Repo nie**, weitergeben nie, Credit-Zeile behalten. Folgen:

- Die Skills gehören **nicht** nach `.claude/skills/` im SituationReport-Repo (öffentlich).
- Richtig ist die **Nutzer-Ebene**: `~/.claude/skills/` oder der Plugin-Weg aus dem Downloads-Ordner
  (`claude plugin marketplace add <Ordner>` + `claude plugin install laws-of-ux@pip-decks`); der Ordner
  bleibt dann liegen. Beide Wege zugleich würden jeden Skill doppelt zeigen.
- Ins Repo darf ein **Verweis** (CLAUDE.md: „bei UI-Arbeit `ux-preflight`/`ux-audit` nutzen") und dürfen
  die **Ergebnisse** (Audits, Begründungen, Testpläne — „Those outputs are yours").
- Credit-Zeile dort, wo Ergebnisse veröffentlicht werden: „Based on Laws of UX by Jon Yablonski,
  lawsofux.com. Published by Pip Decks."

## 3. Wo die Gesetze bei uns greifen — erste Lesung ohne Audit

Keine Befunde (dafür ist `ux-audit` da), sondern die Stellen, an denen die Karten offensichtlich
anschlagen. Zahlen aus der Feature-Inventur.

| Gesetz | Wo bei uns | Was es verlangt |
|---|---|---|
| **Hick's Law**, Chunking | Portfolio-GUI mit 30 Knöpfen, Build-Reports mit 21, Datenquellen-Dialog mit 12 Registerfeldern | Gruppen nach Ritual (Daten → Lage → Konferenz → KI), eine empfohlene Aktion je Gruppe, Rest unter „Mehr" |
| **Von Restorff**, Selective Attention | Alle Knöpfe gleich gewichtet; der Einseiter hat bewusst keine Ampel | Eine primäre Aktion je Fenster; im Report Ausnahmen hervorheben und sonst Ruhe — unser „keine Ampel über alles" ist genau Campbell's Law |
| **Goal-Gradient**, Zeigarnik | Die Kette get_data → transform_data → build_reports → portfolio ist nur im Launcher-Layout angedeutet; Übergabe per Datei | Sichtbare Schritte, „du bist bei 2 von 4", Übergabe-Knopf (T2 existiert für einen Schritt) |
| **Feedback**, **Doherty Threshold** | Hintergrund-Threads mit Log-Fenster; KI-Aufrufe dauern Sekunden bis Minuten | Rückmeldung in 400 ms, Fortschritt und Abbruch bei langen Läufen, Ende mit nächstem Schritt |
| **Peak-End Rule** | „Report erzeugt: Pfad" als Ende | Ende mit Angebot: öffnen, Mappe bauen, Snapshot sichern |
| **Paradox of the Active User** | Manuals als PDF, Tutorials als PDF; Testnutzer lesen sie nicht | Hinweise an der Stelle statt Lektüre vorher; leere Zustände mit erstem Schritt („kein Register verbunden — Datenquellen öffnen") |
| **Jakob's Law**, Mental Model | tkinter ohne Menüleisten-Konventionen in allen Fenstern, Flaggen-Sprachwahl, eigene Dialoge | Standard-Muster: Menü Datei/Bearbeiten/Hilfe, bekannte Dateidialoge, gleiche Stelle für gleiche Dinge in allen acht Fenstern |
| **Fitts' Law** | „…"-Durchsuchen-Knöpfe mit `width=4`, Checkboxen | Mindestgrößen (24 CSS px WCAG AA; für Touch 44) |
| **Postel's Law**, Constraints | Pfade mit Leerzeichen, JSON-Register von Hand, Datumsformate | Annehmen, normalisieren, dann prüfen; Fehler neben dem Feld, Eingabe behalten |
| **Tesler's Law** | Zwölf Register sind echte Komplexität des Stabs, keine Oberflächenfrage | Komplexität nicht wegdesignen, sondern an die richtige Stelle legen (Datenraum einmal, nicht je Fenster) |
| **Pareto**, Short-Term Memory (Dashboards-Playbook) | Report mit ~20 Blöcken, Mappe mit vier Inputs, Einseiter 4×3 | Die zwei, drei Fragen des Rituals oben links; Vergleichswerte nebeneinander; Frische („Stand …") sichtbar |
| **Campbell's Law** | Jeder Report entscheidet, worauf der Stab achtet | Bewusst nicht gebaut: Ampel, Score über alles, Personen — die Karten bestätigen die Linie |

## 4. Vorschläge für die Beta-Arbeit

### V1 — Installation auf Nutzer-Ebene, Verweis im Repo
Plugin-Weg aus dem Downloads-Ordner (oder Kopie nach `~/.claude/skills/`), **nicht** ins Repo. In
CLAUDE.md eine Regel: „UI-Änderungen beginnen mit `ux-preflight` (UX read vor dem ersten Edit) und enden
mit dem UX check; Befunde kommen aus `ux-audit`, Umsetzung über `ux-fix` nur für freigegebene Befunde."
Das ist dieselbe Form wie unsere Konzept-Regel — nur je Bildschirm statt je Feature.

### V2 — Baseline: Audits der heutigen Oberflächen, bevor etwas umgebaut wird
Reihenfolge nach Gewicht: Launcher · Portfolio-GUI · Build-Reports-GUI · Datenquellen-Dialog ·
HTML-Report · Einseiter · Konferenzmappe · Delta-Briefing · die KI-Dialoge (Frage, Noise, Check).
Zwei Beleg-Arten: **Code** (tkinter-Dateien; die Code-Checks sind für HTML/CSS geschrieben, die neun
Linsen gelten trotzdem — Zählen von Knöpfen, Feldern, Schritten, Zuständen funktioniert überall) und
**Screenshot** (laufende Fenster über die eingebaute Browser-/Bildschirm-Route; HTML-Reports als Seite).
Ergebnis: eine Befundtabelle je Oberfläche in `docs/beta/audits/` mit P0–P3 — das ist der Beta-Backlog.
Du wählst, was gefixt wird (Grundsatz „Freigabe zuletzt").

### V3 — Informationsarchitektur nach dem Ritual, nicht nach der Baureihenfolge
Die Playbooks **Navigation** und **Dashboards/Tabellen** auf Launcher und Portfolio-Fenster anwenden:
Gruppen „Daten holen · Lage bauen · Konferenz vorbereiten · KI-Entwürfe · Freigabe"; je Gruppe eine
primäre Aktion; der Datenraum als ein Ort statt zwölf Felder in einem Dialog; die Kette der vier Module
als sichtbarer Pfad mit Übergabe. Vorher **Card Sorting** mit zwei, drei Testnutzern (`ux-methods`):
Wie gruppieren und benennen *sie* die 30 Funktionen? Das ist billig und entscheidet die Gruppen, statt
dass wir raten.

### V4 — Zustände und Rückmeldung in allen acht Fenstern
Das Playbook **States** als Checkliste je Fenster: leer (erster Start, kein Register), lädt
(Hintergrund-Thread, KI-Aufruf mit Fortschritt und Abbruch), Fehler (neben der Ursache, Eingabe bleibt),
Erfolg (mit nächstem Schritt), deaktiviert (warum). Ein gemeinsames Muster für alle Module — heute hat
jedes Fenster sein eigenes Log-Textfeld.

### V5 — Usability-Test mit den Testnutzern, vor und nach dem Umbau
`ux-methods` → Usability-Test: fünf Aufgaben entlang des Rituals (Daten holen, Report bauen, Lagebild
befragen, Mappe erzeugen, Entwurf freigeben), drei bis fünf Teilnehmer mit Codes P1–P5, Skript aus dem
Skill, Auswertung per Affinity Map. Einmal **vor** dem Umbau (Baseline, erklärt auch den Tutorial-Befund),
einmal **nach** dem ersten Schnitt. Ergänzend eine **Journey Map** des Rituals (Vorbereitung → Konferenz
→ Nachbereitung → nächster Stand), damit die Oberfläche dem Ablauf folgt. Das Paket erfindet keine
Ergebnisse — das passt zu unserer Wahrheitsregel; Entwürfe ohne Daten heißen „Draft from assumptions".

### V6 — Begründungen für die Entscheidungen, die wir bewusst gegen die Gewohnheit treffen
`ux-justify` für die drei, vier Linien, die Testnutzer irritieren könnten: keine Ampel über alles
(Campbell's Law), Teams statt Personen (Leitplanke b), Freigabe zuletzt mit sichtbarem Banner (Art. 50),
Spalte 3 des Einseiters ohne Empfehlung. Je eine Notiz nach dem Fünfer-Schema — für CHANGELOG, Tutorials
und als Absatz in der ToT-/KI-Denkschrift (nach dem Core-Group-Termin).

### V7 — Reports als Dashboards lesen
Das Dashboards-Playbook auf Report, Mappe und Einseiter: „Start from the questions" (die drei Fragen des
Einseiters sind genau das), „rank, do not tile", „say what the number means" (Label, Einheit, Zeitraum,
Vergleich — der Fakten-Index hat das schon), „show freshness" (Stand je Quelle), „link each number to its
detail" (vom Einseiter in den Report, vom Report in die Register). Die HTML-Seiten sind Web — hier gelten
die Code-Checks vollständig.

### Bewusst nicht
Pricing/Checkout-Playbook und Pip-Anbindung; keine Produkt-Tour (Paradox of the Active User — unsere
Tutorials bleiben, wandern aber als Hinweise an die Stelle); keine Skills ins öffentliche Repo; kein
Umbau ohne Baseline-Audit.

## 5. Grenzen des Pakets für uns

- Geschrieben für Web-Stacks; tkinter kennt weder CSS noch `data-`Attribute. Die **Linsen und Zähl-
  Checks** gelten, die **Pixel-Checks** nur über Screenshots (geschätzt, „est.").
- Fünf Sprachen: kein Gesetz des Decks behandelt Label-Längen und Umbruch — bleibt unsere Aufgabe.
- Die Karten sind Tendenzen, keine Beweise (sagt das Paket selbst). Entscheidungen fallen weiter bei dir,
  mit Testnutzern als Beleg.
- Lizenztext ist Entwurf; ob Mitarbeitende in einem privaten Repo mitgedeckt wären, lässt der Hersteller
  offen — für uns ohne Belang, solange die Skills auf deinem Rechner bleiben.

## 6. Vorgeschlagene Reihenfolge
1. V1 Installation (fünf Minuten, deine Entscheidung Plugin oder Kopie) + CLAUDE.md-Regel.
2. V2 Baseline-Audits, beginnend mit Launcher und Portfolio-GUI → `docs/beta/audits/`.
3. V5 Usability-Test-Plan und Card-Sorting-Vorlage (Testnutzer-Termin planen).
4. V3/V4 Umbau in Schnitten auf `beta/ux-redesign`, jeder Schnitt mit UX read und UX check.
5. V7 Reports, V6 Begründungen begleitend.

*Credit: Based on Laws of UX by Jon Yablonski, lawsofux.com. Published by Pip Decks.*
