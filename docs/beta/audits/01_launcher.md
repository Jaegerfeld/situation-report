# UX audit: Launcher (`python -m launcher`)

**Scope:** `launcher/gui.py` (787 Zeilen, vollständig gelesen) · Windows-Desktop, Zeiger, Fenster 748 × 681 px auf 3440 × 1440 (gemessen) · statischer Code + laufendes Fenster (Screenshot `launcher_2026-10-23.png`, Sprache DE, Maße der Widgets aus der laufenden Instanz)
**User goal assumed:** Ein Stabsmitglied oder Agile Coach startet SituationReport zum ersten oder zum zehnten Mal und will das richtige Werkzeug für den nächsten Schritt öffnen — Daten holen, Report bauen oder das Lagebild für die Konferenz aufmachen.
**Verdict:** Needs work · **Score:** 20/32 (63 %) · **Findings:** 0 P0, 2 P1, 5 P2, 4 P3

Verfahren: `ux-audit` (Laws of UX Agent Skills 1.0.0, Pip Decks, nach Jon Yablonski), neun Linsen, Code-Checks; Maße gemessen, nicht geschätzt. Keine Änderung am Code.

## Findings

| # | Sev | Law | Evidence | Why it hurts the user | Fix |
|---|-----|-----|----------|------------------------|-----|
| 1 | P1 | Feedback (+ Doherty Threshold) | `launcher/gui.py:783` `subprocess.Popen([sys.executable, "-m", module_id])` kehrt sofort zurück; der Knopf bleibt unverändert, kein Status, kein Cursor-Wechsel. Build Reports und Portfolio importieren Plotly — das Fenster erscheint erst nach Sekunden | Nach „Starten" passiert sichtbar nichts; Menschen klicken erneut (zweites Fenster) oder halten das Programm für kaputt | Beim Klick den Knopf der Karte auf „Startet …" setzen und deaktivieren, `cursor="watch"`; nach `proc.poll()`-Prüfung (z. B. 3 s) zurücksetzen. Rückmeldung in < 400 ms |
| 2 | P1 | Feedback (+ Constraints) | `launcher/gui.py:777-783` `_launch` ohne `try/except`; `Popen`-Fehler landet als Tk-Callback-Ausnahme auf stderr. Ein Modul, das beim Start abbricht (fehlendes Paket im portablen Bundle, Importfehler), hinterlässt nichts im Launcher | Der Hauptzweck des Fensters schlägt still fehl; die Person sieht weder Grund noch Ausweg | `Popen` mit `stderr=PIPE`; nach 2–3 s `poll()`: Rückgabewert ≠ 0 → Dialog „<Modul> konnte nicht starten" mit den letzten stderr-Zeilen und Hinweis aufs Manual |
| 3 | P2 | Pareto Principle (+ Hick's Law, Von Restorff Effect) | `launcher/gui.py:364-373` acht Karten, alle `available=True`, alle mit derselben `ttk.Button`-Vorlage „Starten" (`:512-515`); Screenshot: acht gleich große Karten, acht gleiche Knöpfe | Nichts sagt, womit man anfängt; der häufigste Weg (Stab: Solutions & Portfolios; Pipeline: Get Data) hat dasselbe Gewicht wie Helper und Testdaten-Generator | Je Hälfte einen empfohlenen Einstieg hervorheben (eine primäre Variante, Text „Hier starten"), Werkzeuge für Entwickler (Testdata Generator, Helper) kleiner oder unter „Werkzeuge" gruppieren |
| 4 | P2 | Goal-Gradient Effect (+ Mental Model) | `launcher/gui.py:366-371` Reihenfolge rechts: Transform Data, Build Reports, Get Data, Simulate, Testdata Generator, Helper — die Kette ist aber Get Data → Transform Data → Build Reports (Übergabe existiert nur in Transform, `transform_data`-Doku T2); Screenshot: Get Data in Zeile 2 | Wer die Reihenfolge nicht kennt, startet in der Mitte und muss zurück; der Fortschritt im Dreischritt ist unsichtbar | Karten in Pipeline-Reihenfolge anordnen und nummerieren („1 Daten holen · 2 Aufbereiten · 3 Report"), Simulate/Testdaten/Helper danach; später: Status „zuletzt: Transform erledigt" |
| 5 | P2 | Conceptual Model (+ Jakob's Law) | `launcher/gui.py:118-146` und je Sprache: Kartennamen „Transform Data", „Build Reports", „Get Data", „Helper", „Harmonisation" sind in allen fünf Sprachen englische Modulnamen; nur die Beschreibung darunter nennt die Aufgabe („Jira-Daten aufbereiten") | Die Person muss Modulnamen in Aufgaben übersetzen; „Helper" sagt nichts, „Harmonisation" nur Eingeweihten etwas | Aufgabe als Titel in der jeweiligen Sprache („Jira-Daten aufbereiten"), Modulname als kleine Unterzeile; Reihenfolge der Begriffe in Manuals und Karten gleich halten |
| 6 | P2 | Signifiers (+ Jakob's Law, Discoverability) | `launcher/gui.py:428-448` Flaggen-Knopf und „?" ohne Text; die Übersetzungsschlüssel `tip_language`/`tip_manual` (`:115-116` je Sprache) werden nirgends an ein Tooltip gebunden; Sprache wechselt nur durch Durchklicken von fünf Flaggen (`_toggle_language :420-424`) | Nicht erkennbar, was der Knopf tut; wer Französisch will, klickt viermal; eine Flagge steht nicht für eine Sprache (GB-Flagge für Englisch) | Menüknopf „Sprache ▾" mit Liste der fünf Sprachen in ihrer Eigenschreibung; „?" → Knopf „Handbuch" mit Text; die vorhandenen Tooltip-Texte binden |
| 7 | P2 | Fitts' Law | gemessen in der laufenden Instanz: „?" 19 × 28 px, Flagge 34 × 22 px — je eine Achse unter dem WCAG-2.2-AA-Minimum von 24 × 24 CSS-px (SC 2.5.8); „Starten" 76 × 25 px (erfüllt AA) | Die beiden Kopfzeilen-Knöpfe sind die kleinsten Ziele im Fenster und liegen am Rand | `padx`/`pady` so setzen, dass beide ≥ 24 × 24 px erreichen (Ziel 32 × 32); zwischen Flagge und „?" 8 px Abstand |
| 8 | P3 | Stroop Effect (+ Von Restorff Effect) | `launcher/gui.py:502` Badge ALPHA in `#e74c3c` (Rot, Fehlerfarbe), BETA in Orange; Screenshot: fünf rote Badges | Rot signalisiert Fehler oder Gefahr; „Alpha" ist ein Reifegrad, kein Fehler — die Karten wirken kaputt | Reifegrad in neutraler Farbe (Grau/Blau) mit Text; Rot für Fehler reservieren |
| 9 | P3 | Occam's Razor (+ Conceptual Model) | `launcher/gui.py:512-521` `has_info` wird nur geprüft, wenn `available` falsch ist; Get Data ist `available=True, has_info=True` (`:368`) → `_show_workaround_info` (`:718-770`) und die Texte „Get Data ist noch nicht verfügbar" (`:152-170` und je Sprache) sind unerreichbar und seit 0.21.0 falsch | Toter Pfad und veraltete Texte in fünf Sprachen; wer sie beim Übersetzen pflegt, pflegt Unwahres | Dialog und Schlüssel `dlg_get_data_*`, `btn_launch_helper`, `btn_open_manual` entfernen — oder als echten „Erster Schritt"-Hinweis neu nutzen (siehe #4) |
| 10 | P3 | Cognitive Dissonance | `launcher/gui.py:709-710` „?" öffnet per `webbrowser.open` ein Online-PDF; kein Hinweis, dass der Browser aufgeht und Internet nötig ist (portables Paket läuft auch offline) | Klick auf ein Hilfe-Symbol im Programm führt unerwartet nach außen; offline passiert nichts Sichtbares | Beschriftung „Handbuch (PDF, online)"; offline-Fall: Dialog mit Pfad zur mitgelieferten PDF, falls vorhanden |
| 11 | P3 | Feedback | `launcher/gui.py:783` kein Halten des `Popen`-Handles; keine Anzeige, welche Module schon laufen; zweiter Klick öffnet eine zweite Instanz | Mehrere gleiche Fenster, ohne dass die Person es merkt | Prozesse je Modul merken; Karte zeigt „läuft" und bringt das Fenster nach vorn oder fragt „zweites Fenster öffnen?" |

Note on #3 und #4: beide betreffen die Kartenordnung, aber verschieden — #3 die Gewichtung (was ist wichtig), #4 die Reihenfolge (was kommt wann). Eine Umordnung löst #4, nicht #3.

## Scorecard

| Lens | Score | Decided by |
|------|-------|------------|
| 1 Focus | 2 | #3 P2 (Pareto Principle) |
| 2 Choice and load | 3 | #9 P3 (Occam's Razor) |
| 3 Visual structure | 4 | keine Befunde: Karten gleich gebaut, Gruppen durch Überschrift und Trenner, Abstände innen (8) kleiner als zwischen den Hälften (12) |
| 4 Targets and movement | 2 | #7 P2 (Fitts' Law) |
| 5 Signals and feedback | 1 | #1, #2 P1 (Feedback) |
| 6 Expectations | 2 | #5 P2 (Conceptual Model) |
| 7 Input and recovery | n/a | kein Eingabefeld im Fenster |
| 8 Progress and endings | 2 | #4 P2 (Goal-Gradient Effect) |
| 9 Honesty | 4 | keine Befunde: Reifegrade und Version stehen ehrlich am Produkt, Update-Hinweis ohne Druck |

Summe 20 von 32 (8 Linsen bewertet) = 63 % → **Needs work** (zwei P1).

## What works

- **Zwei Hälften nach Zielgruppe** („Large Solutions & Portfolien" / „ARTs & Team-Verbünde", `:462-477`): die Aufteilung folgt der Frage „für wen", nicht der Modulreihenfolge — Mental Model. Beim Umbau erhalten.
- **Badges tragen Text, nicht nur Farbe** (`:500-507`): ALPHA/BETA bleiben auch ohne Farbe lesbar — WCAG 1.4.1, Von Restorff. Nur die Farbwahl (#8) ändern.
- **Update-Hinweis an Ort und Stelle** (`:663-696`): gelbe Leiste oben mit Text und Knopf, erscheint nur, wenn es etwas gibt, drängt nicht — Feedback ohne Lärm.
- **Fenster passt sich dem Bildschirm an** (`_fit_to_screen :699-706`) und merkt sich die Sprache (`_save_lang_pref`): zwei Dinge, die in jedem Modul gleich sein sollten — Jakob's Law innerhalb des Produkts.

## Not checked

- **Echte Startzeiten** der Module (Plotly-Import, Antivirus im portablen Paket): nur aus Code und Erfahrung abgeleitet; eine Messung je Modul würde #1 beziffern.
- **Verhalten von Menschen**: ob Testnutzer den Einstieg finden oder in der Mitte beginnen — Usability-Test mit der Aufgabe „Erzeuge den ersten Report aus einem Jira-Export" (`ux-methods`, Usability Test).
- **Die vier anderen Sprachen** im Screenshot (nur DE geprüft): Umbruch der Beschreibungen bei `wraplength=155` in FR/PT, Kartenhöhen je Sprache.
- **Tastaturbedienung und Fokus-Ring** der `tk.Button`-Kopfzeile (Standard-Tk, nicht gemessen) und **High-DPI-Skalierung** (gemessen bei 100 %).
- **Hinweis zur Prüfbarkeit:** die Code-Checks des Pakets sind für HTML/CSS geschrieben; tkinter kennt keine Stile — Linsen und Zählungen gelten, Pixelwerte stammen aus `winfo_width/height` der laufenden Instanz.

## Next step

Nichts wurde geändert. Wähle die Befunde, die umgesetzt werden sollen (`fix all`, `fix 1, 2` oder `fix P1`); die Umsetzung folgt dem `ux-fix`-Verfahren: kleinste Änderung zuerst, eine nach der anderen, jede nachgeprüft. Vorschlag: #1, #2 (P1) zuerst, dann #4 und #6 — #3 und #5 betreffen die Informationsarchitektur und gehören in den Schnitt „Launcher nach dem Ritual" (V3 der UX-Skills-Analyse), zusammen mit dem Card Sorting.

*Based on Laws of UX by Jon Yablonski, lawsofux.com. Published by Pip Decks.*
