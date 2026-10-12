# harmonisation

Harmonisierungs-Score je End-to-End-Prozess: ein strukturiertes Assessment in drei
Dimensionen (**Business Value · Transparenz · IT und Betrieb**), versioniert abgelegt,
je Dimension ein Score mit Konfidenz, gerendert als **Entscheider-Matrix** fürs Board.
Herkunft: Roadmap, Priorität P3.

!!! info "Befund, kein Urteil"
    Das Modul empfiehlt nichts — weder *was* harmonisiert wird noch *in welcher Tiefe*.
    Es rechnet den Befund und hält fest, was das Board entschieden hat. Die Urteilszeile
    bleibt beim Menschen, dieselbe Nicht-Funktion wie der fehlende Empfehlungs-Button in
    der KI-Schicht.

## Start

```bash
python -m harmonisation
```

Öffnet die Oberfläche: Arbeitsbereich wählen oder **Beispiel anlegen**, Prozesse pflegen,
Bewertung erfassen, Entscheidung eintragen, Matrix erzeugen.

```bash
python -m harmonisation <ordner> --lang de --browser
python -m harmonisation <ordner> --example      # Beispiel-Arbeitsbereich anlegen und rendern
```

| Option | Bedeutung |
|---|---|
| `--output FILE` | HTML-Datei (Standard: `<ordner>/matrix.<lang>.html`) |
| `--lang de\|en\|ro\|pt\|fr` | Sprache der Matrix (Standard: de) |
| `--example` | schreibt den Beispiel-Arbeitsbereich in den Ordner |
| `--browser` | öffnet die Matrix im Browser |
| `--since JJJJ-MM-TT` | statt der Matrix die **Veränderung** seit diesem Stichtag (`<ordner>/delta.<lang>.html`) |
| `--delta ORDNER` | Veränderung gegenüber einem zweiten Arbeitsbereich (früherer Stand) |
| `--narrate [PROVIDER]` | **KI-Lesart (Entwurf)** unter Matrix oder Veränderung; Standard `ollama`, auch `claude`, `mock` |
| `--llm-model`, `--llm-base-url` | Modell bzw. Adresse für `--narrate` (sonst Provider-Standard) |

## Arbeitsbereich

Ein Ordner mit vier Dingen, alles JSON mit `schema_version`:

```
<ordner>/
├── catalogue.json      Fragenkatalog: Dimensionen → Fragen (Text je Sprache)
├── processes.json      End-to-End-Prozesse (id, name, owner, brands)
├── decisions.json      Entscheidung des Boards je Prozess (optional)
└── assessments/        eine Datei je Bewertung: Prozess, Befragte(r), Datum, Antworten
```

**Der Katalog ist Daten, nicht Code.** Der mitgelieferte Beispielkatalog mit 3 × 8 Fragen
ist eine Illustration der Struktur; die eigenen Fragen kommen in dieselbe Datei.
Jede Frage ist so formuliert, dass hohe Zustimmung *für* eine Harmonisierung spricht —
nur so sind die Werte einer Dimension addierbar.

## Antworten und Rechnung

- **Skala je Frage:** 0 „trifft nicht zu" … 4 „trifft voll zu" — und **„unbekannt" als
  zulässige Antwort**. Ein Lagebild, das Unwissen nicht ausweisen kann, täuscht Sicherheit vor.
- **Beleggrad je Antwort:** belegt (Dokument, Messung) · geschätzt · Hörensagen.
- **Score je Dimension:** Mittel der beantworteten Fragen, 0–100; dazu „n von 8 beantwortet".
- **Konfidenz:** Anteil belegter Antworten an *allen* Fragen der Dimension — hoch ab ⅔,
  mittel ab ⅓, sonst niedrig. „Unbekannt" senkt die Konfidenz, nicht den Score.
- **Mehrere Bewertungen desselben Prozesses:** **Median** als Score, **Spanne** (max − min)
  daneben. Zwei Befragte, die denselben Prozess völlig verschieden sehen, sind ein Befund,
  kein Rauschen, das man wegmittelt.
- **Kein Gesamtscore** über die Dimensionen: drei Zahlen nebeneinander sind ehrlicher als
  eine, die drei verschiedene Dinge verrechnet.

## Die Matrix

Zeilen = Prozesse, Spalten = Dimensionen; je Zelle Score (blau abgestuft — ein Befund,
keine Ampel), Zahl der Bewertungen, beantwortete Fragen, Spanne und die Konfidenz als
Ampel-Badge. Rechts die Spalten, die **das Board ausfüllt**: Entscheidung (standardisieren ·
markenspezifisch · offen) und Tiefe im Wortlaut des Boards. Farbschlüssel und Legende stehen
vor der ersten Tabelle. Darunter die zweite Lesart: jede Bewertung mit jeder Antwort und
ihrem Beleggrad.

## Veränderung zweier Stände (Schritt 2)

„Was hat sich seit der letzten Bewertung geändert?" — nach dem Muster des Delta-Briefings.
Bewertungen sind datiert, darum rechnet `--since 2026-09-20` den Stand von damals aus den
heutigen Dateien zurück; `--delta <ordner>` vergleicht mit einem zweiten Arbeitsbereich.
Verglichen werden je Prozess und Dimension **Score, Konfidenz, Spanne und Zahl der
Bewertungen** (alt → neu), dazu neue Bewertungen (nur das Datum, keine Namen), die
Entscheidungen des Boards, hinzugekommene oder entfallene Prozesse. Ein geänderter
Fragenkatalog wird als Warnung ausgewiesen — die Scores sind dann nicht vergleichbar.

- „Keine Änderungen" wird ausdrücklich gesagt.
- **Ein gesunkener Score ist keine Verschlechterung**, sondern ein anderer Befund. Die
  Tabelle ordnet nach Prozess, nicht nach gut und schlecht.
- Entscheidungen ohne Datum gelten in beiden Ständen als vorhanden; die Seite zählt sie.

```bash
python -m harmonisation <ordner> --since 2026-09-20 --lang de --browser
```

## KI-Lesart (Entwurf)

`--narrate` (oder der Haken in der Oberfläche) hängt an Matrix oder Veränderung eine
Lesart an — nach demselben Muster wie die Executive Summary der Portfolio-Reports:

- Das Modell sieht **nur einen Contract** mit allen Zahlen der Matrix bzw. der Veränderung:
  Prozesse, Dimensionen, Marken, Entscheidungen des Boards — **nie Personen** (Owner und
  Befragte fehlen im Contract strukturell).
- Jede Zahl im Entwurf muss im Contract stehen, sonst wird er verworfen (einmal wiederholt).
- Der versionierte Prompt untersagt zusätzlich **jede Empfehlung**, was harmonisiert wird
  oder in welcher Tiefe — der Score ist ein Befund, das Urteil liegt beim Board.
- Der Entwurf steht gekennzeichnet (Art.-50-Banner) direkt unter der Tabelle und
  zusätzlich in `<ausgabe>.reading.md` zum Redigieren; der Betreiber-Nachweis landet in
  `llm_audit.jsonl` neben der Ausgabe (Zweck `p3_reading`).
- Scheitert die KI, bleibt die deterministische Seite stehen; die Kommandozeile meldet es
  mit Rückgabewert 3, die Oberfläche in der Statuszeile.

```bash
python -m harmonisation <ordner> --narrate            # lokal über Ollama
python -m harmonisation <ordner> --since 2026-09-20 --narrate mock   # Attrappe ohne Modell
```

## In der Konferenzmappe

Im Portfolio-Modul trägt eine Solution das optionale Feld `"harmonisation"` mit dem
**Ordner** des Arbeitsbereichs (Datenquellen-Dialog, zehntes Feld mit Ordner-Auswahl;
„Aus Datenraum übernehmen" erkennt `registers/harmonisation/` am Katalog). Die
Konferenzmappe zeigt die Matrix dann als **Anhang nach Input 4** — eine Board-Sicht,
bewusst kein fünfter Konferenz-Input. Ein fehlender oder inkonsistenter Arbeitsbereich
wird mit Warnung übersprungen; die Mappe steht trotzdem.

## Was bewusst fehlt

- Kein Harmonisierungs-Vorschlag, keine Rangliste, keine empfohlene Tiefe — auch nicht
  in der KI-Lesart.
- Keine KI im Kern: Die Rechnung ist deterministisch und nur Standardbibliothek. Die
  optionale KI-Lesart formuliert nur, gekennzeichnet als Entwurf, und rechnet nichts.
- Kein Gesamtscore.
- Kein Diff auf Antwort-Ebene: Die zweite Lesart der Matrix zeigt jede Antwort; ein Diff
  darauf wäre ein Diff auf Aussagen einzelner Personen.

## Tests

```bash
python -m pytest tests/harmonisation/
```
